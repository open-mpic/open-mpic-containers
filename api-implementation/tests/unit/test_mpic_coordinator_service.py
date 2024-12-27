import json
import yaml
import pytest

from importlib import resources
from io import BytesIO
from unittest.mock import patch
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import TypeAdapter
from requests import Response

from open_mpic_core.common_domain.check_request import DcvCheckRequest
from open_mpic_core.common_domain.check_response import DcvCheckResponse
from open_mpic_core.common_domain.check_response_details import DcvDnsCheckResponseDetails
from open_mpic_core.common_domain.enum.check_type import CheckType
from open_mpic_core.common_domain.enum.dcv_validation_method import DcvValidationMethod
from open_mpic_core.mpic_coordinator.domain.mpic_orchestration_parameters import MpicEffectiveOrchestrationParameters
from open_mpic_core.mpic_coordinator.domain.mpic_response import MpicCaaResponse
from open_mpic_core.mpic_coordinator.domain.remote_perspective import RemotePerspective

from mpic_coordinator_service.main import MpicCoordinatorService, PerspectiveEndpoints, PerspectiveEndpointInfo, app
from open_mpic_core_test.test_util.valid_mpic_request_creator import ValidMpicRequestCreator
from open_mpic_core_test.test_util.valid_check_creator import ValidCheckCreator


client = TestClient(app)


# noinspection PyMethodMayBeStatic
class TestMpicCoordinatorService:
    @pytest.fixture(autouse=True)
    def mock_yaml_load(self):
        with resources.files('resources').joinpath('available_test_perspectives.yaml').open('r') as file:
            perspectives_yaml = yaml.safe_load(file)

        with patch('mpic_coordinator_service.main.yaml.safe_load') as mock:
            mock.return_value = perspectives_yaml
            yield mock

    @staticmethod
    @pytest.fixture(scope='function')
    def set_env_variables():
        perspectives_as_dict = TestMpicCoordinatorService.create_perspectives_config_dict()
        envvars = {
            'perspectives': json.dumps({k: v.model_dump() for k, v in perspectives_as_dict.items()}),
            'default_perspective_count': '2',
            'absolute_max_attempts': '2',
            'hash_secret': 'test_secret'
        }
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            for k, v in envvars.items():
                class_scoped_monkeypatch.setenv(k, v)
            yield class_scoped_monkeypatch  # restore the environment afterward

    @staticmethod
    @pytest.fixture(scope='function')
    def set_some_env_variables():
        # set the env variables whose placeholder values are not strings (to avoid runtime errors),
        # expecting the remaining placeholder values to be read from the config file
        perspectives_as_dict = TestMpicCoordinatorService.create_perspectives_config_dict()
        envvars = {
            'perspectives': json.dumps({k: v.model_dump() for k, v in perspectives_as_dict.items()}),
            'default_perspective_count': '2',
            'absolute_max_attempts': '2',
        }
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            for k, v in envvars.items():
                class_scoped_monkeypatch.setenv(k, v)
            yield class_scoped_monkeypatch

    def constructor__should_initialize_mpic_coordinator_and_set_target_perspectives(self, set_env_variables):
        mpic_coordinator_service = MpicCoordinatorService()
        all_possible_perspectives = TestMpicCoordinatorService.get_perspectives_by_code_dict_from_file()
        for target_perspective in mpic_coordinator_service.target_perspectives:
            assert target_perspective in all_possible_perspectives.values()
        mpic_coordinator = mpic_coordinator_service.mpic_coordinator
        assert len(mpic_coordinator.target_perspectives) == 6
        assert mpic_coordinator_service.hash_secret == 'test_secret'
        assert mpic_coordinator_service.default_perspective_count == 2
        assert mpic_coordinator_service.global_max_attempts == 2

    def load_available_perspectives_config__should_return_dict_of_perspectives_with_proximity_info_by_region_code(self):
        perspectives = MpicCoordinatorService.load_available_perspectives_config()
        expected_perspectives = TestMpicCoordinatorService.get_perspectives_by_code_dict_from_file()
        assert len(perspectives) == len(expected_perspectives)
        assert 'test-1' in perspectives
        assert 'test-7' in perspectives['test-8'].too_close_codes

    def call_remote_perspective__should_call_remote_perspective_with_provided_arguments_and_return_check_response(self, set_env_variables, mocker):
        mocker.patch('requests.post', side_effect=self.create_successful_api_call_response_for_dcv_check)
        dcv_check_request = ValidCheckCreator.create_valid_dns_check_request()
        service = MpicCoordinatorService()
        check_response = service.call_remote_perspective(
            RemotePerspective(code='test-1', rir='rir1'), CheckType.DCV, dcv_check_request
        )
        assert check_response.check_passed is True
        # hijacking the value of 'perspective_code' to verify that the right arguments got passed to the call
        assert check_response.perspective_code == dcv_check_request.domain_or_ip_target

    def service__should_read_in_environment_configuration_through_config_file(self, set_some_env_variables):
        mpic_coordinator_service = MpicCoordinatorService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        assert mpic_coordinator_service.hash_secret == 'HASH_SECRET_STRING'

    def service__should_return_400_error_and_details_given_invalid_request_body(self, set_env_variables):
        request = ValidMpicRequestCreator.create_valid_dcv_mpic_request()
        # noinspection PyTypeChecker
        request.domain_or_ip_target = None
        response = client.post('/mpic', json=request.model_dump())
        assert response.status_code == 400
        result_body = json.loads(response.text)
        assert result_body['validation_issues'][0]['type'] == 'string_type'

    def service__should_return_400_error_and_details_given_invalid_check_type(self, set_env_variables):
        request = ValidMpicRequestCreator.create_valid_dcv_mpic_request()
        request.check_type = 'invalid_check_type'
        response = client.post('/mpic', json=request.model_dump())
        assert response.status_code == 400
        result_body = json.loads(response.text)
        assert result_body['validation_issues'][0]['type'] == 'literal_error'

    def service__should_return_400_error_given_logically_invalid_request(self, set_env_variables):
        request = ValidMpicRequestCreator.create_valid_dcv_mpic_request()
        request.orchestration_parameters.perspective_count = 1
        response = client.post('/mpic', json=request.model_dump())
        assert response.status_code == 400
        result_body = json.loads(response.text)
        assert result_body['validation_issues'][0]['issue_type'] == 'invalid-perspective-count'

    def service__should_return_500_error_given_other_unexpected_errors(self, set_env_variables, mocker):
        request = ValidMpicRequestCreator.create_valid_dcv_mpic_request()
        mocker.patch('open_mpic_core.mpic_coordinator.mpic_coordinator.MpicCoordinator.coordinate_mpic',
                     side_effect=Exception('Something went wrong'))
        response = client.post('/mpic', json=request.model_dump())
        assert response.status_code == 500

    def service__should_coordinate_mpic_using_configured_mpic_coordinator(self, set_env_variables, mocker):
        mpic_request = ValidMpicRequestCreator.create_valid_mpic_request(CheckType.CAA)
        mock_return_value = TestMpicCoordinatorService.create_caa_mpic_response()
        mocker.patch('open_mpic_core.mpic_coordinator.mpic_coordinator.MpicCoordinator.coordinate_mpic',
                     return_value=mock_return_value)
        response = client.post('/mpic', json=mpic_request.model_dump())
        assert response.status_code == status.HTTP_200_OK
        result_body = json.loads(response.text)
        assert result_body['is_valid'] is True

    @staticmethod
    def get_perspectives_by_code_dict_from_file() -> dict[str, RemotePerspective]:
        with resources.files('resources').joinpath('available_test_perspectives.yaml').open('r') as file:
            perspectives_yaml = yaml.safe_load(file)
            perspective_type_adapter = TypeAdapter(list[RemotePerspective])
            perspectives = perspective_type_adapter.validate_python(perspectives_yaml['available_regions'])
            return {perspective.code: perspective for perspective in perspectives}

    @staticmethod
    def create_perspectives_config_dict() -> dict[str, PerspectiveEndpoints]:
        # configure 6 target perspectives
        perspectives_as_dict = {
            f"test-{i}": PerspectiveEndpoints(caa_endpoint_info=PerspectiveEndpointInfo(url=f"http://caa{i}.example.com/caa"),
                                              dcv_endpoint_info=PerspectiveEndpointInfo(url=f"http://dcv{i}.example.com/dcv"))
            for i in range(1, 7)  # 1-6
        }
        return perspectives_as_dict

    # noinspection PyUnusedLocal,PyShadowingNames
    def create_successful_api_call_response_for_dcv_check(self, url, timeout, headers, json):
        # json arg in requests.post() is a "json serializable object" (dict) rather than an actual json string
        check_request = DcvCheckRequest.model_validate(json)
        # hijacking the value of 'perspective_code' to verify that the right arguments got passed to the call
        expected_response_body = DcvCheckResponse(
            perspective_code=check_request.domain_or_ip_target,
            check_passed=True, details=DcvDnsCheckResponseDetails(
                validation_method=DcvValidationMethod.ACME_DNS_01
            )
        )
        expected_response = TestMpicCoordinatorService.create_mock_response(
            200, expected_response_body.model_dump_json()
        )
        return expected_response

    @staticmethod
    def create_mock_response(status_code: int, content: str, kwargs: dict = None):
        response = Response()
        response.status_code = status_code
        response.raw = BytesIO(content.encode('utf-8'))  # code under test reads from response.text
        if kwargs is not None:
            for k, v in kwargs.items():
                setattr(response, k, v)
        return response

    @staticmethod
    def create_caa_mpic_response():
        caa_request = ValidMpicRequestCreator.create_valid_caa_mpic_request()
        return MpicCaaResponse(
            request_orchestration_parameters=caa_request.orchestration_parameters,
            actual_orchestration_parameters=MpicEffectiveOrchestrationParameters(
                perspective_count=3, quorum_count=2, attempt_count=1
            ),
            is_valid=True,
            perspectives=[],
            caa_check_parameters=caa_request.caa_check_parameters
        )


if __name__ == '__main__':
    pytest.main()
