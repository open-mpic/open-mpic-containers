import importlib.metadata
import logging
import pytest
from unittest.mock import MagicMock, patch, call

import mpic_observability_util

# TEMP: trigger CI workflow run for tests.yml path filters.

class TestEnvBool:
    """Test env_bool helper function with various env states."""

    def env_bool__should_return_false_by_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_ENV_VAR", raising=False)
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is False

    def env_bool__should_return_custom_default_when_unset(self, monkeypatch):
        monkeypatch.delenv("TEST_ENV_VAR", raising=False)
        assert mpic_observability_util.env_bool("TEST_ENV_VAR", default=True) is True

    def env_bool__should_return_true_when_set_to_true(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_VAR", "true")
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is True

    def env_bool__should_return_true_when_set_to_true_case_insensitive(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_VAR", "True")
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is True
        monkeypatch.setenv("TEST_ENV_VAR", "TRUE")
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is True

    def env_bool__should_return_false_when_set_to_false(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_VAR", "false")
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is False

    def env_bool__should_return_false_when_set_to_arbitrary_value(self, monkeypatch):
        monkeypatch.setenv("TEST_ENV_VAR", "anything_else")
        assert mpic_observability_util.env_bool("TEST_ENV_VAR") is False


class TestOtelSignalHelpers:
    """Test otel signal detection functions."""

    def otel_any_signal_enabled__should_return_false_when_all_disabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")
        assert mpic_observability_util.otel_any_signal_enabled() is False

    def otel_any_signal_enabled__should_return_true_when_traces_enabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")
        assert mpic_observability_util.otel_any_signal_enabled() is True

    def otel_any_signal_enabled__should_return_true_when_metrics_enabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "true")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")
        assert mpic_observability_util.otel_any_signal_enabled() is True

    def otel_any_signal_enabled__should_return_true_when_logs_enabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "true")
        assert mpic_observability_util.otel_any_signal_enabled() is True

    def otel_tracing_enabled__should_return_false_by_default(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        assert mpic_observability_util.otel_tracing_enabled() is False

    def otel_tracing_enabled__should_return_true_when_enabled(self, monkeypatch):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
        assert mpic_observability_util.otel_tracing_enabled() is True


class TestSetupTelemetry:
    """Test setup_telemetry with various signal combinations."""

    @staticmethod
    def setup_logging_for_telemetry():
        """Ensure logging handler state is clean for telemetry tests."""
        root = logging.getLogger()
        for handler in root.handlers[:]:
            root.removeHandler(handler)
        yield
        # Reset state after test
        mpic_observability_util._otel_logging_handler = None

    def setup_telemetry__should_return_early_when_all_signals_disabled(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")

        mock_resource = mocker.patch("mpic_observability_util.Resource.create")

        mpic_observability_util.setup_telemetry("test-service")

        mock_resource.assert_not_called()

    def setup_telemetry__should_use_unknown_version_when_api_package_not_found(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")

        # Patch version lookups
        def version_side_effect(package_name):
            if "open-mpic-restapi-server" in package_name:
                raise importlib.metadata.PackageNotFoundError(package_name)
            return "1.0.0"

        mocker.patch(
            "importlib.metadata.version",
            side_effect=version_side_effect,
        )

        mock_resource = mocker.patch("mpic_observability_util.Resource.create")
        mocker.patch("mpic_observability_util.TracerProvider")
        mocker.patch("mpic_observability_util.BatchSpanProcessor")
        mocker.patch("mpic_observability_util.trace")

        mpic_observability_util.setup_telemetry("test-service")

        # Assert Resource.create was called with unknown api version
        mock_resource.assert_called_once()
        call_kwargs = mock_resource.call_args[0][0]
        assert call_kwargs["service.version"] == "unknown"

    def setup_telemetry__should_use_unknown_version_when_core_package_not_found(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")

        # Patch version lookups
        def version_side_effect(package_name):
            if "open-mpic-core" in package_name:
                raise importlib.metadata.PackageNotFoundError(package_name)
            return "1.0.0"

        mocker.patch(
            "importlib.metadata.version",
            side_effect=version_side_effect,
        )

        mock_resource = mocker.patch("mpic_observability_util.Resource.create")
        mocker.patch("mpic_observability_util.TracerProvider")
        mocker.patch("mpic_observability_util.BatchSpanProcessor")
        mocker.patch("mpic_observability_util.trace")

        mpic_observability_util.setup_telemetry("test-service")

        # Assert Resource.create was called with unknown core version
        mock_resource.assert_called_once()
        call_kwargs = mock_resource.call_args[0][0]
        assert call_kwargs["open_mpic_core.version"] == "unknown"

    def setup_telemetry__should_setup_tracer_provider_when_traces_enabled(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "true")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")

        mocker.patch("importlib.metadata.version", return_value="1.0.0")
        mock_resource = mocker.patch("mpic_observability_util.Resource.create")
        mock_tracer_provider = mocker.patch("mpic_observability_util.TracerProvider")
        mock_span_processor = mocker.patch("mpic_observability_util.BatchSpanProcessor")
        mock_exporter = mocker.patch("mpic_observability_util.OTLPSpanExporter")
        mock_trace = mocker.patch("mpic_observability_util.trace")

        mpic_observability_util.setup_telemetry("test-service")

        mock_tracer_provider.assert_called_once()
        mock_exporter.assert_called_once()
        mock_span_processor.assert_called_once()
        mock_trace.set_tracer_provider.assert_called_once()

    def setup_telemetry__should_setup_meter_provider_when_metrics_enabled(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "true")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "false")

        mocker.patch("importlib.metadata.version", return_value="1.0.0")
        mocker.patch("mpic_observability_util.Resource.create")
        mock_metric_reader = mocker.patch("mpic_observability_util.PeriodicExportingMetricReader")
        mock_metric_exporter = mocker.patch("mpic_observability_util.OTLPMetricExporter")
        mock_meter_provider = mocker.patch("mpic_observability_util.MeterProvider")
        mock_metrics = mocker.patch("mpic_observability_util.metrics")

        mpic_observability_util.setup_telemetry("test-service")

        mock_metric_exporter.assert_called_once()
        mock_metric_reader.assert_called_once()
        mock_meter_provider.assert_called_once()
        mock_metrics.set_meter_provider.assert_called_once()

    def setup_telemetry__should_setup_logger_provider_when_logs_enabled(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "true")

        mocker.patch("importlib.metadata.version", return_value="1.0.0")
        mocker.patch("mpic_observability_util.Resource.create")
        mock_logger_provider = mocker.patch("mpic_observability_util.LoggerProvider")
        mock_log_exporter = mocker.patch("mpic_observability_util.OTLPLogExporter")
        mock_log_processor = mocker.patch("mpic_observability_util.BatchLogRecordProcessor")
        mock_logging_handler = mocker.patch("mpic_observability_util.LoggingHandler")
        mock_set_logger_provider = mocker.patch("mpic_observability_util.set_logger_provider")

        mpic_observability_util.setup_telemetry("test-service")

        mock_log_exporter.assert_called_once()
        mock_log_processor.assert_called_once()
        mock_logger_provider.assert_called_once()
        mock_set_logger_provider.assert_called_once()
        mock_logging_handler.assert_called_once()

    def setup_telemetry__should_not_duplicate_logging_handler_on_second_call(self, monkeypatch, mocker):
        monkeypatch.setenv("OTEL_LOGS_ENABLED", "true")
        monkeypatch.setenv("OTEL_TRACES_ENABLED", "false")
        monkeypatch.setenv("OTEL_METRICS_ENABLED", "false")

        mocker.patch("importlib.metadata.version", return_value="1.0.0")
        mocker.patch("mpic_observability_util.Resource.create")
        mocker.patch("mpic_observability_util.LoggerProvider")
        mocker.patch("mpic_observability_util.OTLPLogExporter")
        mocker.patch("mpic_observability_util.BatchLogRecordProcessor")
        mock_logging_handler = mocker.patch("mpic_observability_util.LoggingHandler")
        mocker.patch("mpic_observability_util.set_logger_provider")
        mocker.patch("logging.getLogger")

        # Reset handler state before test
        mpic_observability_util._otel_logging_handler = None

        # First call should create handler
        mpic_observability_util.setup_telemetry("test-service-1")
        assert mock_logging_handler.call_count == 1

        # Second call should not create another handler (it already exists)
        mpic_observability_util.setup_telemetry("test-service-2")
        assert mock_logging_handler.call_count == 1

        # Reset for other tests
        mpic_observability_util._otel_logging_handler = None


# class TestShutdownTelemetry:
#     """Test shutdown_telemetry cleanup behavior."""

#     def shutdown_telemetry__should_remove_logging_handler_when_present(self, mocker):
#         # Set up a mock handler
#         mock_handler = MagicMock()
#         mpic_observability_util._otel_logging_handler = mock_handler

#         mock_root_logger = mocker.patch("logging.getLogger")

#         mpic_observability_util.shutdown_telemetry()

#         mock_root_logger.return_value.removeHandler.assert_called_once_with(mock_handler)
#         mock_handler.close.assert_called_once()
#         assert mpic_observability_util._otel_logging_handler is None

#     def shutdown_telemetry__should_not_error_when_no_logging_handler(self, mocker):
#         mpic_observability_util._otel_logging_handler = None

#         mocker.patch("logging.getLogger")

#         # Should not raise
#         mpic_observability_util.shutdown_telemetry()

#     def shutdown_telemetry__should_shutdown_providers_when_shutdown_method_exists(self, mocker):
#         mpic_observability_util._otel_logging_handler = None

#         # Create mock providers with shutdown method
#         mock_tracer_provider = MagicMock()
#         mock_meter_provider = MagicMock()
#         mock_logger_provider = MagicMock()

#         mocker.patch("logging.getLogger")
#         mocker.patch("mpic_observability_util.trace.get_tracer_provider", return_value=mock_tracer_provider)
#         mocker.patch("mpic_observability_util.metrics.get_meter_provider", return_value=mock_meter_provider)
#         mocker.patch(
#             "mpic_observability_util.get_logger_provider",
#             return_value=mock_logger_provider,
#         )

#         mpic_observability_util.shutdown_telemetry()

#         mock_tracer_provider.shutdown.assert_called_once()
#         mock_meter_provider.shutdown.assert_called_once()
#         mock_logger_provider.shutdown.assert_called_once()

#     def shutdown_telemetry__should_skip_shutdown_when_method_does_not_exist(self, mocker):
#         mpic_observability_util._otel_logging_handler = None

#         # Create mock providers without shutdown method
#         mock_tracer_provider = MagicMock(spec=[])  # Empty spec means no shutdown
#         mock_meter_provider = MagicMock()
#         mock_logger_provider = MagicMock()

#         mocker.patch("logging.getLogger")
#         mocker.patch("mpic_observability_util.trace.get_tracer_provider", return_value=mock_tracer_provider)
#         mocker.patch("mpic_observability_util.metrics.get_meter_provider", return_value=mock_meter_provider)
#         mocker.patch(
#             "mpic_observability_util.get_logger_provider",
#             return_value=mock_logger_provider,
#         )

#         mpic_observability_util.shutdown_telemetry()

#         # Tracer provider has no shutdown, so it shouldn't be called
#         # (MagicMock would still have it as attribute, but hasattr would fail with empty spec)
#         assert not hasattr(mock_tracer_provider, "shutdown") or mock_tracer_provider.shutdown.call_count == 0
#         mock_meter_provider.shutdown.assert_called_once()
#         mock_logger_provider.shutdown.assert_called_once()
