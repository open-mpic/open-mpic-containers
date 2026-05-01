import logging
import os
from contextlib import asynccontextmanager

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
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
from open_mpic_core import DcvCheckRequest
from open_mpic_core import MpicDcvChecker
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

    import importlib.metadata

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
        logging.getLogger().addHandler(LoggingHandler(level=logging.NOTSET, logger_provider=logger_provider))


def _shutdown_telemetry() -> None:
    """Flush buffered telemetry and shut down SDK providers."""
    for provider in (trace.get_tracer_provider(), metrics.get_meter_provider(), get_logger_provider()):
        if hasattr(provider, "shutdown"):
            provider.shutdown()


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
load_dotenv(config_path)
logger = get_logger(__name__)


class MpicDcvCheckerService:
    def __init__(self):
        self.verify_ssl = "verify_ssl" not in os.environ or os.environ["verify_ssl"] == "True"
        try:
            self.dcv_checker = MpicDcvChecker(reuse_http_client=True, verify_ssl=self.verify_ssl)
        except TypeError:
            self.dcv_checker = MpicDcvChecker(verify_ssl=self.verify_ssl)

    async def shutdown(self):
        await self.dcv_checker.shutdown()

    async def check_dcv(self, dcv_request: DcvCheckRequest):
        result = await self.dcv_checker.check_dcv(dcv_request)
        if result.errors is not None and len(result.errors) > 0:
            if result.errors[0].error_type == "404":
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            result = JSONResponse(
                status_code=status_code, content=result.model_dump()  # If you want to use 400 instead of 422
            )
        return result


# Global instance for Service
_service = None


def get_service() -> MpicDcvCheckerService:
    """
    Singleton pattern to avoid recreating the service on every call
    """
    global _service
    if _service is None:
        _service = MpicDcvCheckerService()
    return _service


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Initialize telemetry before service so instruments are created against real providers
    _setup_telemetry("mpic-dcv-checker")

    # Initialize services
    service = get_service()
    yield
    await service.shutdown()
    _shutdown_telemetry()


app = FastAPI(lifespan=lifespan)
if _otel_tracing_enabled():
    FastAPIInstrumentor.instrument_app(app)


@app.post("/dcv")
async def perform_mpic(request: DcvCheckRequest):
    # noinspection PyUnresolvedReferences
    async with logger.trace_timing("Remote DCV check processing"):
        return await get_service().check_dcv(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
