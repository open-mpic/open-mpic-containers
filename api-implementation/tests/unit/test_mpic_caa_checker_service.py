import dns
import time
import pytest

from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from opentelemetry import trace

from open_mpic_core.common_domain.check_response import CaaCheckResponse
from open_mpic_core_test.test_util.mock_dns_object_creator import MockDnsObjectCreator
from open_mpic_core.common_domain.check_response_details import CaaCheckResponseDetails
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator

from mpic_caa_checker_service.main import MpicCaaCheckerService, app


# noinspection PyMethodMayBeStatic
class TestMpicCaaCheckerService:
    @staticmethod
    @pytest.fixture(scope='class', autouse=True)
    def set_env_variables():
        # note: opentelemetry env vars are set in the pyproject.toml file using pytest-env due to timing constraints
        envvars = {
            'AWS_REGION': 'us-east-1',
            'default_caa_domains': 'ca1.com|ca2.org|ca3.net',
        }
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            for k, v in envvars.items():
                class_scoped_monkeypatch.setenv(k, v)
            yield class_scoped_monkeypatch  # restore the environment afterward

    # noinspection PyUnresolvedReferences
    @classmethod
    def teardown_class(cls):
        provider = trace.get_tracer_provider()
        # if provider has force_flush method, call it to ensure all spans are sent
        if hasattr(provider, 'force_flush'):
            trace.get_tracer_provider().force_flush()
        if hasattr(provider, 'shutdown'):
            trace.get_tracer_provider().shutdown()

    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicCaaCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        assert service.perspective_code == 'PERSPECTIVE_NAME_CODE_STRING'

    def service__should_return_healthy_status_given_health_check_request(self):
        with TestClient(app) as client:
            response = client.get('/healthz')

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'status': 'healthy'}

    # noinspection PyMethodMayBeStatic
    def service__should_do_caa_check_using_configured_caa_checker(self, set_env_variables, mocker):
        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()
        mock_caa_response = TestMpicCaaCheckerService.create_caa_check_response()
        awaitable_mock_response = AsyncMock(return_value=mock_caa_response)
        mocker.patch('open_mpic_core.mpic_caa_checker.mpic_caa_checker.MpicCaaChecker.check_caa',
                     new=awaitable_mock_response)

        with TestClient(app) as client:
            response = client.post('/caa', json=caa_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_caa_response.model_dump()

    # TODO verify instead that the log is being piped to opentelemetry or something
    def service__should_set_log_level_of_caa_checker(self, trace_logging_output, mocker):
        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()

        records = [MockDnsObjectCreator.create_caa_record(0, 'issue', 'ca1.org')]
        mock_rrset = MockDnsObjectCreator.create_rrset(dns.rdatatype.CAA, *records)
        mock_domain = dns.name.from_text(caa_check_request.domain_or_ip_target)
        mock_return = (mock_rrset, mock_domain)
        mocker.patch('open_mpic_core.mpic_caa_checker.mpic_caa_checker.MpicCaaChecker.find_caa_records_and_domain',
                     return_value=mock_return)

        with TestClient(app) as client:
            response = client.post('/caa', json=caa_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        log_contents = trace_logging_output.getvalue()
        print(log_contents)
        assert all(text in log_contents for text in ['mpic_caa_checker', 'TRACE'])

    # test that the service is using opentelemetry tracing properly
    def service__should_trace_timing_of_caa_check(self, set_env_variables, tracer_in_memory_exporter, mocker):
        mock_caa_response = TestMpicCaaCheckerService.create_caa_check_response()
        awaitable_mock_response = AsyncMock(return_value=mock_caa_response)
        mocker.patch('open_mpic_core.mpic_caa_checker.mpic_caa_checker.MpicCaaChecker.check_caa',
                     new=awaitable_mock_response)
        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()
        with TestClient(app) as client:
            client.post('/caa', json=caa_check_request.model_dump())
        from opentelemetry.sdk.trace import ReadableSpan
        print(f"Current tracer provider: {trace.get_tracer_provider()}")
        spans: list[ReadableSpan] = tracer_in_memory_exporter.get_finished_spans()
        for span in spans:
            print(span.to_json())
        assert len(spans) == 1  # only one span should be created with current FastAPIInstrumentor arguments
        assert '/caa' in spans[0].name

    @staticmethod
    def create_caa_check_response():
        return CaaCheckResponse(perspective_code='us-east-1', check_passed=True,
                                details=CaaCheckResponseDetails(caa_record_present=True,
                                                                found_at='example.com'),
                                timestamp_ns=time.time_ns())


if __name__ == '__main__':
    pytest.main()
