from multiprocessing.util import get_logger

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.trace import NoOpTracerProvider

from open_mpic_core.common_util.trace_level_logger import get_logger

import os
from enum import Enum

logger = get_logger(__name__)


class ExporterType(str, Enum):
    CONSOLE = 'console'
    OTLP = 'otlp'
    NONE = 'none'  # Explicit no-op exporter


# noinspection PyUnresolvedReferences
def initialize_tracing_configuration():
    logger.debug("Initializing tracing configuration")
    """Initialize tracing configuration."""
    disabled = os.getenv('OTEL_SDK_DISABLED', 'True').lower() == 'true'

    # Get exporter type; using 'MPIC_' to not interfere with actual OpenTelemetry environment variables
    exporter_type = ExporterType(os.getenv("MPIC_OTEL_TRACES_EXPORTER", ExporterType.NONE))

    logger.debug(f"Is OTEL disabled? {disabled}")
    # if exporter type is console, set that up
    if disabled or exporter_type == ExporterType.NONE:
        logger.debug("Making a NoOpTracerProvider...")
        tracer_provider = NoOpTracerProvider()
    else:
        exporter = None
        if exporter_type == ExporterType.CONSOLE:
            logger.debug("Making a ConsoleSpanExporter...")
            exporter = ConsoleSpanExporter()
        elif exporter_type == ExporterType.OTLP:
            logger.debug("Making an OTLPSpanExporter...")
            exporter = OTLPSpanExporter()  # reads env configuration for OTLP endpoint

        service_name = os.getenv('OTEL_SERVICE_NAME', 'mpic_service')
        resource = Resource.create(
            attributes={
                "service.name": service_name,
            }
        )
        tracer_provider = TracerProvider(resource=resource)
        processor = BatchSpanProcessor(exporter)
        # processor = SimpleSpanProcessor(exporter)
        tracer_provider.add_span_processor(processor)

    trace.set_tracer_provider(tracer_provider)


def instrument_fastapi(self, app):
    """Instrument FastAPI if tracing is enabled"""
    if self.enabled:
        FastAPIInstrumentor.instrument_app(app)
        AioHttpClientInstrumentor().instrument()
