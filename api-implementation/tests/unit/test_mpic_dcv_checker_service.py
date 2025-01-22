import time
import pytest

from unittest.mock import AsyncMock
from fastapi import status
from fastapi.testclient import TestClient

from open_mpic_core.common_domain.check_response import DcvCheckResponse
from open_mpic_core.common_domain.check_response_details import DcvHttpCheckResponseDetails
from open_mpic_core.common_domain.enum.dcv_validation_method import DcvValidationMethod
from open_mpic_core.common_domain.validation_error import MpicValidationError
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator

from mpic_dcv_checker_service.main import MpicDcvCheckerService, app


# noinspection PyMethodMayBeStatic
class TestMpicDcvCheckerService:
    @staticmethod
    @pytest.fixture(scope='class')
    def set_env_variables():
        envvars = {
            'AWS_REGION': 'us-east-1',
        }
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            for k, v in envvars.items():
                class_scoped_monkeypatch.setenv(k, v)
            yield class_scoped_monkeypatch  # restore the environment afterward

    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicDcvCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        # note: this test is semi-invalidated by other tests that check this value because it's a global load
        assert service.perspective_code == 'PERSPECTIVE_NAME_CODE_STRING'

    # noinspection PyMethodMayBeStatic
    def service__should_do_dcv_check_using_configured_dcv_checker(self, set_env_variables, mocker):
        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()
        mock_dcv_response = TestMpicDcvCheckerService.create_dcv_check_response()
        awaitable_mock_response = AsyncMock(return_value=mock_dcv_response)
        mocker.patch('open_mpic_core.mpic_dcv_checker.mpic_dcv_checker.MpicDcvChecker.check_dcv', new=awaitable_mock_response)

        with TestClient(app) as client:
            response = client.post('/dcv', json=dcv_check_request.model_dump())

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_dcv_response.model_dump()

    @pytest.mark.parametrize('error_type, error_message, expected_status_code', [
        ('404', 'Not Found', status.HTTP_404_NOT_FOUND),
        ('No Answer', 'The DNS response does not contain an answer to the question', status.HTTP_500_INTERNAL_SERVER_ERROR)
    ])
    def service__should_return_appropriate_status_code_given_dcv_related_errors_in_response(
            self, error_type: str, error_message: str, expected_status_code: int, set_env_variables, mocker):
        mock_dcv_response = TestMpicDcvCheckerService.create_dcv_check_response()
        mock_dcv_response.check_passed = False
        mock_dcv_response.errors = [(MpicValidationError(error_type=error_type, error_message=error_message))]

        awaitable_mock_response = AsyncMock(return_value=mock_dcv_response)
        mocker.patch('open_mpic_core.mpic_dcv_checker.mpic_dcv_checker.MpicDcvChecker.check_dcv', new=awaitable_mock_response)

        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()

        with TestClient(app) as client:
            response = client.post('/dcv', json=dcv_check_request.model_dump())
            
        assert response.status_code == expected_status_code
        assert response.json() == mock_dcv_response.model_dump()

    def service__should_return_healthy_status_given_health_check_request(self):
        with TestClient(app) as client:
            response = client.get('/healthz')

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {'status': 'healthy'}

    def service__should_set_log_level_of_dcv_checker(self, set_env_variables, trace_logging_output, mocker):
        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()
        mocker.patch('open_mpic_core.mpic_dcv_checker.mpic_dcv_checker.MpicDcvChecker.perform_http_based_validation',
                     return_value=TestMpicDcvCheckerService.create_dcv_check_response())
        with TestClient(app) as client:
            response = client.post('/dcv', json=dcv_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        log_contents = trace_logging_output.getvalue()
        print(log_contents)
        assert all(text in log_contents for text in ['mpic_dcv_checker', 'TRACE'])  # Verify the log level was set

    # test that the service is using opentelemetry tracing properly
    def service__should_trace_timing_of_dcv_check(self, set_env_variables, tracer_in_memory_exporter, mocker):
        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()
        mock_dcv_response = TestMpicDcvCheckerService.create_dcv_check_response()
        awaitable_mock_response = AsyncMock(return_value=mock_dcv_response)
        mocker.patch('open_mpic_core.mpic_dcv_checker.mpic_dcv_checker.MpicDcvChecker.check_dcv', new=awaitable_mock_response)

        with TestClient(app) as client:
            client.post('/dcv', json=dcv_check_request.model_dump())
        from opentelemetry.sdk.trace import ReadableSpan
        spans: list[ReadableSpan] = tracer_in_memory_exporter.get_finished_spans()
        for span in spans:
            print(span.to_json())
        assert len(spans) == 1
        assert '/dcv' in spans[0].name

    @staticmethod
    def create_dcv_check_response():
        return DcvCheckResponse(perspective_code='us-east-1', check_passed=True,
                                details=DcvHttpCheckResponseDetails(
                                    validation_method=DcvValidationMethod.WEBSITE_CHANGE_V2
                                ), timestamp_ns=time.time_ns())


if __name__ == '__main__':
    pytest.main()
