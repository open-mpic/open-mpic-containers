import pytest
import logging

from io import StringIO
from opentelemetry import trace
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from open_mpic_core.common_util.trace_level_logger import TRACE_LEVEL


@pytest.fixture(autouse=False)
def trace_logging_output():
    # Clear existing handlers
    root = logging.getLogger()
    for handler in root.handlers[:]:
        root.removeHandler(handler)

    log_output = StringIO()  # to be able to inspect what gets logged
    handler = logging.StreamHandler(log_output)
    handler.setFormatter(logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))

    # Configure fresh logging
    logging.basicConfig(
        handlers=[handler],
        level=TRACE_LEVEL,
    )

    yield log_output


@pytest.fixture(autouse=False, scope='function')
def tracer_console_exporter():  # use for DEBUGGING OpenTelemetry related tests (to see what gets logged)
    provider = trace.get_tracer_provider()
    if not hasattr(provider, 'add_span_processor'):
        pytest.fail(f"TracerProvider {provider} does not have add_span_processor method")
    exporter = ConsoleSpanExporter()
    processor = SimpleSpanProcessor(exporter)
    # noinspection PyUnresolvedReferences
    provider.add_span_processor(processor)
    yield
    processor.shutdown()


@pytest.fixture(autouse=False, scope='function')
def tracer_in_memory_exporter():  # use for assertions in OpenTelemetry tests
    provider = trace.get_tracer_provider()
    if not hasattr(provider, 'add_span_processor'):
        pytest.fail(f"TracerProvider {provider} does not have add_span_processor method")
    exporter = InMemorySpanExporter()
    processor = SimpleSpanProcessor(exporter)  # Using Simple instead of Batch for immediate processing
    # noinspection PyUnresolvedReferences
    provider.add_span_processor(processor)
    yield exporter
    exporter.clear()
    processor.shutdown()
