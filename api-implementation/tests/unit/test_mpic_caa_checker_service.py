import time
from unittest.mock import AsyncMock

import pytest

from fastapi import status
from fastapi.testclient import TestClient

from open_mpic_core.common_domain.check_response import CaaCheckResponse
from open_mpic_core.common_domain.check_response_details import CaaCheckResponseDetails
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator

from mpic_caa_checker_service.main import MpicCaaCheckerService, app


# noinspection PyMethodMayBeStatic
class TestMpicCaaCheckerService:
    @staticmethod
    @pytest.fixture(scope='class')
    def set_env_variables():
        envvars = {
            'AWS_REGION': 'us-east-1',
            'default_caa_domains': 'ca1.com|ca2.org|ca3.net'
        }
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            for k, v in envvars.items():
                class_scoped_monkeypatch.setenv(k, v)
            yield class_scoped_monkeypatch  # restore the environment afterward

    # noinspection PyMethodMayBeStatic
    def service__should_do_caa_check_using_configured_caa_checker(self, set_env_variables, mocker):
        mock_caa_result = TestMpicCaaCheckerService.create_caa_check_response()

        # Use AsyncMock for async function
        mock = AsyncMock(return_value=mock_caa_result)
        mocker.patch('open_mpic_core.mpic_caa_checker.mpic_caa_checker.MpicCaaChecker.check_caa', new=mock)

        caa_check_request = ValidCheckCreator.create_valid_caa_check_request()

        with TestClient(app) as client:
            response = client.post('/caa', json=caa_check_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == mock_caa_result.model_dump()

    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicCaaCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        assert service.perspective_code == 'PERSPECTIVE_NAME_CODE_STRING'

    @staticmethod
    def create_caa_check_response():
        return CaaCheckResponse(perspective_code='us-east-1', check_passed=True,
                                details=CaaCheckResponseDetails(caa_record_present=True,
                                                                found_at='example.com'),
                                timestamp_ns=time.time_ns())


if __name__ == '__main__':
    pytest.main()
