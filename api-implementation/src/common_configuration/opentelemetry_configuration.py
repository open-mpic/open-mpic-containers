from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.trace import NoOpTracerProvider

import os
from enum import Enum


class ExporterType(str, Enum):
    CONSOLE = 'console'
    OTLP = 'otlp'
    NONE = 'none'  # Explicit no-op exporter


def initialize_tracing_configuration():
    print("Initializing tracing configuration")
    """Initialize tracing configuration."""
    disabled = os.getenv('OTEL_SDK_DISABLED', 'True').lower() == 'true'

    # Get exporter type; using 'MPIC_' to not interfere with actual OpenTelemetry environment variables
    exporter_type = ExporterType(os.getenv("MPIC_OTEL_TRACES_EXPORTER", ExporterType.NONE))

    print(f"OTEL is disabled? {disabled}")
    # if exporter type is console, set that up
    if disabled or exporter_type == ExporterType.NONE:
        print("Making a NoOpTracerProvider...")
        tracer_provider = NoOpTracerProvider()
    else:
        exporter = None
        if exporter_type == ExporterType.CONSOLE:
            print("Making a ConsoleSpanExporter...")
            exporter = ConsoleSpanExporter()
        elif exporter_type == ExporterType.OTLP:
            print("Making an OTLPSpanExporter...")
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
