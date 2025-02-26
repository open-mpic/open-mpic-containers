import dns
import time
import pytest
import re

from fastapi import status
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock
from open_mpic_core import CaaCheckResponse, CaaCheckResponseDetails
from open_mpic_core_test.test_util.mock_dns_object_creator import MockDnsObjectCreator
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator

from mpic_caa_checker_service.main import MpicCaaCheckerService, app


# noinspection PyMethodMayBeStatic
class TestMpicCaaCheckerService:
    @staticmethod
    @pytest.fixture(scope="function")
    def set_env_variables():
        envvars = {"default_caa_domains": "example.com|example.net"}
        with pytest.MonkeyPatch.context() as function_scoped_monkeypatch:
            for k, v in envvars.items():
                function_scoped_monkeypatch.setenv(k, v)
            yield function_scoped_monkeypatch  # restore the environment afterward

    # noinspection PyMethodMayBeStatic
    def service__should_do_caa_check_using_configured_caa_checker(self, set_env_variables, mocker):
        mock_caa_response = TestMpicCaaCheckerService.create_caa_check_response()

        # Use AsyncMock for async function
        awaitable_mock_response = AsyncMock(return_value=mock_caa_response)
        mocker.patch("open_mpic_core.MpicCaaChecker.check_caa", new=awaitable_mock_response)

        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()

        with TestClient(app) as client:
            response = client.post("/caa", json=caa_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_caa_response.model_dump()

    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicCaaCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        assert service.default_caa_domain_list == ["DEFAULT_CAA_DOMAINS_LIST"]

    def service__should_return_healthy_status_given_health_check_request(self):
        with TestClient(app) as client:
            response = client.get("/healthz")

        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "healthy"}

    def service__should_set_log_level_of_caa_checker(self, setup_logging, mocker):  # TODO add logger_setup fixture
        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()

        records = [MockDnsObjectCreator.create_caa_record(0, "issue", "ca1.org")]
        mock_rrset = MockDnsObjectCreator.create_rrset(dns.rdatatype.CAA, *records)
        mock_domain = dns.name.from_text(caa_check_request.domain_or_ip_target)
        mock_return = (mock_rrset, mock_domain)
        mocker.patch("open_mpic_core.MpicCaaChecker.find_caa_records_and_domain", return_value=mock_return)

        with TestClient(app) as client:
            response = client.post("/caa", json=caa_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        log_contents = setup_logging.getvalue()
        print(log_contents)
        assert all(text in log_contents for text in ["MpicCaaChecker", "TRACE"])  # Verify the log level was set

    def service__should_return_app_config_diagnostics_give_diagnostics_request(self, set_env_variables):
        with TestClient(app) as client:
            response = client.get("/configz")
        assert response.status_code == status.HTTP_200_OK
        config = response.json()
        assert all(
            re.match(r"^\d+\.\d+\.\d+", config[key])
            for key in ["app_version", "open_mpic_api_spec_version", "mpic_core_version"]
        )
        assert config["default_caa_domains"] == "example.com|example.net"

    @staticmethod
    def create_caa_check_response():
        return CaaCheckResponse(
            check_passed=True,
            details=CaaCheckResponseDetails(caa_record_present=True, found_at="example.com"),
            timestamp_ns=time.time_ns(),
        )


if __name__ == "__main__":
    pytest.main()
