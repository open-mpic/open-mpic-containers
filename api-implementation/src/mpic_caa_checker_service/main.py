import importlib.metadata
import logging
import os
import tomllib
import importlib.metadata

from contextlib import asynccontextmanager
from fastapi import FastAPI  # type: ignore
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry import trace, metrics
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
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

from open_mpic_core import CaaCheckRequest
from open_mpic_core import MpicCaaChecker
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


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
load_dotenv(config_path)
logger = get_logger(__name__)


class MpicCaaCheckerService:
    def __init__(self):
        # FIXME warn on default_caa_domain_list None or empty
        self.default_caa_domain_list = os.environ["default_caa_domains"].split("|")
        self.dns_timeout_seconds = (
            float(os.environ["dns_timeout_seconds"]) if "dns_timeout_seconds" in os.environ else None
        )
        self.dns_resolution_lifetime_seconds = (
            float(os.environ["dns_resolution_lifetime_seconds"])
            if "dns_resolution_lifetime_seconds" in os.environ
            else None
        )
        self.caa_checker = MpicCaaChecker(
            self.default_caa_domain_list,
            dns_timeout=self.dns_timeout_seconds,
            dns_resolution_lifetime=self.dns_resolution_lifetime_seconds,
        )

    async def check_caa(self, caa_request: CaaCheckRequest):
        return await self.caa_checker.check_caa(caa_request)


# Global instance for Service
_service = None


def get_service() -> MpicCaaCheckerService:
    """
    Singleton pattern to avoid recreating the service on every API all
    """
    global _service
    if _service is None:
        _service = MpicCaaCheckerService()
    return _service


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    _setup_telemetry("mpic-caa-checker")
    get_service()  # initialize service after telemetry is configured
    yield
    _shutdown_telemetry()


app = FastAPI(lifespan=lifespan)
if _otel_tracing_enabled():
    FastAPIInstrumentor.instrument_app(app)


# noinspection PyUnresolvedReferences
@app.post("/caa")
async def handle_caa_check(request: CaaCheckRequest):
    async with logger.trace_timing("Remote CAA check processing"):
        result = await get_service().check_caa(request)
        logger.trace(f"CAA check result: {result}")
        return result


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/configz")
async def get_config():
    current = Path(__file__).parent
    for _ in range(3):  # Try up to 3 levels up (Docker flattens the file structure a fair bit)
        path_to_project_config = current / "pyproject.toml"
        if path_to_project_config.exists():
            with path_to_project_config.open(mode="rb") as file:
                pyproject = tomllib.load(file)
                uvicorn_server_timeout_keep_alive = (
                    int(os.environ["uvicorn_server_timeout_keep_alive"])
                    if "uvicorn_server_timeout_keep_alive" in os.environ
                    else None
                )
                return {
                    "open_mpic_api_spec_version": pyproject["tool"]["api"]["spec_version"],
                    "app_version": pyproject["project"]["version"],
                    "mpic_core_version": importlib.metadata.version("open-mpic-core"),
                    "default_caa_domains": get_service().default_caa_domain_list,
                    "log_level": logger.getEffectiveLevel(),
                    "uvicorn_server_timeout_keep_alive": uvicorn_server_timeout_keep_alive,
                    "dns_timeout_seconds": get_service().dns_timeout_seconds,
                    "dns_resolution_lifetime_seconds": get_service().dns_resolution_lifetime_seconds,
                }
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
