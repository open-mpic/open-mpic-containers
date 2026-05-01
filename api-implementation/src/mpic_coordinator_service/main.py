import importlib.metadata
import json
import logging
import os
import tomllib
import traceback

import aiohttp
import yaml

from contextlib import asynccontextmanager
from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from opentelemetry import trace, metrics
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.propagate import inject
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from pydantic import TypeAdapter, BaseModel, Field
from open_mpic_core import MpicRequest, MpicResponse
from open_mpic_core import MpicRequestValidationException as MpicRequestValidationError, MpicRequestValidationMessages
from open_mpic_core import CheckType
from open_mpic_core import CheckRequest, CheckResponse
from open_mpic_core import MpicCoordinator, MpicCoordinatorConfiguration
from open_mpic_core import RemotePerspective
from open_mpic_core import get_logger


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() == "true"


def _otel_tracing_enabled() -> bool:
    return _env_bool("OTEL_TRACES_ENABLED", False)


def _setup_telemetry(service_name: str) -> None:
    """Initialize OpenTelemetry SDK providers for metrics, traces, and logs.

    Reads the following environment variables (all optional):
      OTEL_TRACES_ENABLED         - Set 'true' to export traces (default: false)
      OTEL_METRICS_ENABLED        - Set 'true' to export metrics (default: false)
      OTEL_LOGS_ENABLED           - Set 'true' to export logs (default: false)
      OTEL_SERVICE_NAME           - Service name reported to backends (overrides service_name arg)
      OTEL_EXPORTER_OTLP_ENDPOINT - Base URL for OTLP HTTP export
                                    (default: http://otel-collector:4318; read by exporters automatically)
      OTEL_RESOURCE_ATTRIBUTES    - Extra resource labels, e.g. deployment.environment=dev
    """
    traces_enabled = _env_bool("OTEL_TRACES_ENABLED", False)
    metrics_enabled = _env_bool("OTEL_METRICS_ENABLED", False)
    logs_enabled = _env_bool("OTEL_LOGS_ENABLED", False)

    if not (traces_enabled or metrics_enabled or logs_enabled):
        return

    try:
        core_version = importlib.metadata.version("open-mpic-core")
    except importlib.metadata.PackageNotFoundError:
        core_version = "unknown"

    resource = Resource.create(
        {
            SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", service_name),
            SERVICE_VERSION: core_version,
        }
    )

    if traces_enabled:
        tracer_provider = TracerProvider(resource=resource)
        tracer_provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
        trace.set_tracer_provider(tracer_provider)

    if metrics_enabled:
        reader = PeriodicExportingMetricReader(OTLPMetricExporter())
        meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
        metrics.set_meter_provider(meter_provider)

    if logs_enabled:
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(logger_provider)
        logging.getLogger().addHandler(LoggingHandler(level=logging.INFO, logger_provider=logger_provider))


def _shutdown_telemetry() -> None:
    """Flush buffered telemetry and shut down SDK providers."""
    for provider in (trace.get_tracer_provider(), metrics.get_meter_provider(), get_logger_provider()):
        if hasattr(provider, "shutdown"):
            provider.shutdown()


def _otel_propagation_headers() -> dict[str, str]:
    """Return W3C trace-context headers for the current active span (empty dict when no SDK)."""
    headers: dict[str, str] = {}
    inject(headers)
    return headers


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
load_dotenv(config_path)
logger = get_logger(__name__)


class PerspectiveEndpointInfo(BaseModel):
    url: str
    headers: dict[str, str] | None = Field(default_factory=dict)


class PerspectiveEndpoints(BaseModel):
    dcv_endpoint_info: PerspectiveEndpointInfo
    caa_endpoint_info: PerspectiveEndpointInfo


class MpicCoordinatorService:
    def __init__(self):
        # load environment variables
        perspectives_json = os.environ["perspectives"]
        perspectives = {
            code: PerspectiveEndpoints.model_validate(endpoints)
            for code, endpoints in json.loads(perspectives_json).items()
        }
        self.all_target_perspective_codes = list(perspectives.keys())
        self.default_perspective_count = int(os.environ["default_perspective_count"])
        self.global_max_attempts = (
            int(os.environ["absolute_max_attempts"]) if "absolute_max_attempts" in os.environ else None
        )
        self.hash_secret = os.environ["hash_secret"]
        self.timeout_seconds = float(os.environ["timeout_seconds"]) if "timeout_seconds" in os.environ else 5

        self.remotes_per_perspective_per_check_type = {
            CheckType.DCV: {
                perspective_code: perspective_config.dcv_endpoint_info
                for perspective_code, perspective_config in perspectives.items()
            },
            CheckType.CAA: {
                perspective_code: perspective_config.caa_endpoint_info
                for perspective_code, perspective_config in perspectives.items()
            },
        }

        all_possible_perspectives_by_code = MpicCoordinatorService.load_available_perspectives_config()
        self.target_perspectives = MpicCoordinatorService.convert_codes_to_remote_perspectives(
            self.all_target_perspective_codes, all_possible_perspectives_by_code
        )

        self.mpic_coordinator_configuration = MpicCoordinatorConfiguration(
            self.target_perspectives, self.default_perspective_count, self.global_max_attempts, self.hash_secret
        )

        self._async_http_client = None

        self.mpic_coordinator = MpicCoordinator(
            call_remote_perspective_function=self.call_remote_perspective,
            mpic_coordinator_configuration=self.mpic_coordinator_configuration,
        )

        # for correct deserialization of responses based on discriminator field (check type)
        self.mpic_request_adapter = TypeAdapter(MpicRequest)
        self.check_response_adapter = TypeAdapter(CheckResponse)

    async def initialize(self):
        if self._async_http_client is None:
            session_timeout = aiohttp.ClientTimeout(
                total=None, sock_connect=self.timeout_seconds, sock_read=self.timeout_seconds
            )

            self._async_http_client = aiohttp.ClientSession(timeout=session_timeout, trust_env=True)

    async def shutdown(self):
        if self._async_http_client:
            await self._async_http_client.close()
            self._async_http_client = None

    @staticmethod
    def load_available_perspectives_config() -> dict[str, RemotePerspective]:
        """
        Reads in the available perspectives from a configuration yaml and returns them as a dict (map).
        Expects the yaml to be in the resources folder, next to the app folder containing this file.
        :return: dict of available perspectives with region code as key
        """
        resource_path = Path(__file__).parent / "resources" / "available_perspectives.yaml"

        with resource_path.open() as file:
            region_config_yaml = yaml.safe_load(file)
            region_type_adapter = TypeAdapter(list[RemotePerspective])
            regions_list = region_type_adapter.validate_python(region_config_yaml["available_regions"])
            regions_dict = {region.code: region for region in regions_list}
            return regions_dict

    @staticmethod
    def convert_codes_to_remote_perspectives(
        perspective_codes: list[str], all_possible_perspectives_by_code: dict[str, RemotePerspective]
    ) -> list[RemotePerspective]:
        remote_perspectives = []

        for perspective_code in perspective_codes:
            if perspective_code not in all_possible_perspectives_by_code.keys():
                continue  # TODO throw an error? check this case in the validator?
            else:
                fully_defined_perspective = all_possible_perspectives_by_code[perspective_code]
                remote_perspectives.append(fully_defined_perspective)

        return remote_perspectives

    # This function MUST validate its response and return a proper open_mpic_core object type.
    async def call_remote_perspective(
        self, perspective: RemotePerspective, check_type: CheckType, check_request: CheckRequest
    ) -> CheckResponse:
        if self._async_http_client is None:
            raise RuntimeError("Service not initialized - call initialize() first")

        # Get the remote info from the data structure.
        endpoint_info: PerspectiveEndpointInfo = self.remotes_per_perspective_per_check_type[check_type][
            perspective.code
        ]

        async with self._async_http_client.post(
            url=endpoint_info.url,
            headers={**dict(endpoint_info.headers or {}), **_otel_propagation_headers()},
            json=check_request.model_dump(),
        ) as response:
            text = await response.text()
            return self.check_response_adapter.validate_json(text)

    async def perform_mpic(self, mpic_request: MpicRequest) -> MpicResponse:
        return await self.mpic_coordinator.coordinate_mpic(mpic_request)


# Global instance for Service
_service = None


def get_service() -> MpicCoordinatorService:
    """
    Singleton pattern to avoid recreating the service on every call
    """
    global _service
    if _service is None:
        _service = MpicCoordinatorService()
    return _service


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Initialize telemetry before service so instruments are created against real providers
    _setup_telemetry("mpic-coordinator")

    # Initialize services
    service = get_service()
    await service.initialize()

    yield

    # Cleanup
    await service.shutdown()
    _shutdown_telemetry()


app = FastAPI(lifespan=lifespan)
if _otel_tracing_enabled():
    FastAPIInstrumentor.instrument_app(app)


# noinspection PyUnusedLocal
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,  # If you want to use 400 instead of 422
        content={"error": MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key, "validation_issues": e.errors()},
    )


# noinspection PyUnusedLocal
@app.exception_handler(MpicRequestValidationError)
async def mpic_validation_exception_handler(request: Request, e: MpicRequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,  # If you want to use 400 instead of 422
        content={
            "error": MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key,
            "validation_issues": json.loads(e.__notes__[0]),
        },
    )


@app.middleware("http")  # This is a middleware that catches general exceptions and returns a 500 response
async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        logger.error(traceback.format_exc())
        return JSONResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, content={"error": str(e)})


@app.post("/mpic")
async def handle_mpic(request: MpicRequest):
    # noinspection PyUnresolvedReferences
    async with logger.trace_timing("MPIC request processing"):
        return await get_service().perform_mpic(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/configz")
async def get_config():
    current = Path(__file__).parent
    for _ in range(3):  # Try up to 3 levels up (Docker flattens the file structure a fair bit)
        test_path = current / "pyproject.toml"
        if test_path.exists():
            with test_path.open(mode="rb") as file:
                pyproject = tomllib.load(file)
                return {
                    "open_mpic_api_spec_version": pyproject["tool"]["api"]["spec_version"],
                    "app_version": pyproject["project"]["version"],
                    "mpic_core_version": importlib.metadata.version("open-mpic-core"),
                }
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
