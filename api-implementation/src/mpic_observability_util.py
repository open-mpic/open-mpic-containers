import importlib.metadata
import logging
import os

from opentelemetry import metrics, trace
from opentelemetry._logs import get_logger_provider, set_logger_provider
from opentelemetry.exporter.otlp.proto.http._log_exporter import OTLPLogExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk._logs import LoggerProvider, LoggingHandler
from opentelemetry.sdk._logs.export import BatchLogRecordProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

_otel_logging_handler: LoggingHandler | None = None


def env_bool(name: str, default: bool = False) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.lower() == "true"


def otel_any_signal_enabled() -> bool:
    return (
        env_bool("OTEL_TRACES_ENABLED", False)
        or env_bool("OTEL_METRICS_ENABLED", False)
        or env_bool("OTEL_LOGS_ENABLED", False)
    )


def otel_tracing_enabled() -> bool:
    return env_bool("OTEL_TRACES_ENABLED", False)


def setup_telemetry(service_name: str) -> None:
    """Initialize OpenTelemetry SDK providers for metrics, traces, and logs."""
    traces_enabled = env_bool("OTEL_TRACES_ENABLED", False)
    metrics_enabled = env_bool("OTEL_METRICS_ENABLED", False)
    logs_enabled = env_bool("OTEL_LOGS_ENABLED", False)

    if not (traces_enabled or metrics_enabled or logs_enabled):
        return

    try:
        api_version = importlib.metadata.version("open-mpic-restapi-server")
    except importlib.metadata.PackageNotFoundError:
        api_version = "unknown"

    try:
        core_version = importlib.metadata.version("open-mpic-core")
    except importlib.metadata.PackageNotFoundError:
        core_version = "unknown"

    resource = Resource.create(
        {
            SERVICE_NAME: os.environ.get("OTEL_SERVICE_NAME", service_name),
            SERVICE_VERSION: api_version,
            "open_mpic_core.version": core_version,
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
        global _otel_logging_handler
        logger_provider = LoggerProvider(resource=resource)
        logger_provider.add_log_record_processor(BatchLogRecordProcessor(OTLPLogExporter()))
        set_logger_provider(logger_provider)
        if _otel_logging_handler is None:
            _otel_logging_handler = LoggingHandler(level=logging.INFO, logger_provider=logger_provider)
            logging.getLogger().addHandler(_otel_logging_handler)


def shutdown_telemetry() -> None:
    """Flush buffered telemetry and shut down SDK providers."""
    global _otel_logging_handler
    if _otel_logging_handler is not None:
        logging.getLogger().removeHandler(_otel_logging_handler)
        _otel_logging_handler.close()
        _otel_logging_handler = None

    for provider in (trace.get_tracer_provider(), metrics.get_meter_provider(), get_logger_provider()):
        if hasattr(provider, "shutdown"):
            provider.shutdown()
