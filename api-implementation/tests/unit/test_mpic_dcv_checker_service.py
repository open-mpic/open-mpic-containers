import time
import re
import pytest

from unittest.mock import AsyncMock

from fastapi import status
from fastapi.testclient import TestClient
from open_mpic_core import DcvCheckResponse
from open_mpic_core import DcvHttpCheckResponseDetails
from open_mpic_core import DcvValidationMethod
from open_mpic_core import MpicValidationError
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator

from mpic_dcv_checker_service.main import app


# noinspection PyMethodMayBeStatic
class TestMpicDcvCheckerService:
    @staticmethod
    @pytest.fixture(scope="function")
    def set_env_variables():
        envvars = {
            "uvicorn_server_timeout_keep_alive": "25",
        }
        with pytest.MonkeyPatch.context() as function_scoped_monkeypatch:
            for k, v in envvars.items():
                function_scoped_monkeypatch.setenv(k, v)
            yield function_scoped_monkeypatch  # restore the environment afterward

    # noinspection PyMethodMayBeStatic
    def service__should_do_dcv_check_using_configured_dcv_checker(self, mocker):
        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()
        mock_dcv_response = TestMpicDcvCheckerService.create_dcv_check_response()

        # Use AsyncMock for async function
        awaitable_mock_response = AsyncMock(return_value=mock_dcv_response)
        mocker.patch("open_mpic_core.MpicDcvChecker.check_dcv", new=awaitable_mock_response)

        with TestClient(app) as client:
            response = client.post("/dcv", json=dcv_check_request.model_dump())

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_dcv_response.model_dump()

    # fmt: off
    @pytest.mark.parametrize("error_type, error_message, expected_status_code", [
            ("404", "Not Found", status.HTTP_404_NOT_FOUND),
            (
                "No Answer",
                "The DNS response does not contain an answer to the question",
                status.HTTP_500_INTERNAL_SERVER_ERROR,
            ),
    ])
    # fmt: on
    def service__should_return_appropriate_status_code_given_dcv_related_errors_in_response(
        self, error_type: str, error_message: str, expected_status_code: int, mocker
    ):
        mock_dcv_response = TestMpicDcvCheckerService.create_dcv_check_response()
        mock_dcv_response.check_passed = False
        mock_dcv_response.errors = [(MpicValidationError(error_type=error_type, error_message=error_message))]

        awaitable_mock_response = AsyncMock(return_value=mock_dcv_response)
        mocker.patch("open_mpic_core.MpicDcvChecker.check_dcv", new=awaitable_mock_response)

        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()

        with TestClient(app) as client:
            response = client.post("/dcv", json=dcv_check_request.model_dump())

        assert response.status_code == expected_status_code
        assert response.json() == mock_dcv_response.model_dump()

    def service__should_return_healthy_status_given_health_check_request(self):
        with TestClient(app) as client:
            response = client.get("/healthz")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    def service__should_set_log_level_of_dcv_checker(self, mocker, setup_logging):
        dcv_check_request = ValidCheckCreator.create_valid_http_check_request()
        check_response = TestMpicDcvCheckerService.create_dcv_check_response()
        mocker.patch("open_mpic_core.MpicDcvChecker.perform_http_based_validation", return_value=check_response)
        with TestClient(app) as client:
            response = client.post("/dcv", json=dcv_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        log_contents = setup_logging.getvalue()
        print(log_contents)
        assert all(text in log_contents for text in ["MpicDcvChecker", "TRACE"])  # Verify the log level was set

    def service__should_return_app_config_diagnostics_give_diagnostics_request(self, set_env_variables):
        with TestClient(app) as client:
            response = client.get("/configz")
        assert response.status_code == status.HTTP_200_OK
        config = response.json()
        assert all(
            re.match(r"^\d+\.\d+\.\d+", config[key])
            for key in ["app_version", "open_mpic_api_spec_version", "mpic_core_version"]
        )
        assert config["http_client_timeout_seconds"] == 35  # default in app.conf file
        assert config["verify_ssl"] is True
        assert config["log_level"] == 5
        assert config["uvicorn_server_timeout_keep_alive"] == 25

    @staticmethod
    def create_dcv_check_response():
        return DcvCheckResponse(
            check_passed=True,
            details=DcvHttpCheckResponseDetails(validation_method=DcvValidationMethod.WEBSITE_CHANGE),
            timestamp_ns=time.time_ns(),
        )


if __name__ == "__main__":
    pytest.main()
