import json
from importlib import resources

import pytest
import yaml
from open_mpic_core.mpic_coordinator.domain.remote_perspective import RemotePerspective
from pydantic import TypeAdapter

from mpic_coordinator_service.app.main import MpicCoordinatorService, PerspectiveEndpoints, PerspectiveEndpointInfo


# noinspection PyMethodMayBeStatic
class TestMpicCoordinatorLambda:
    @staticmethod
    @pytest.fixture(scope='class')
    def set_env_variables():
        perspectives_as_dict = {
            "test-1": PerspectiveEndpoints(caa_endpoint_info=PerspectiveEndpointInfo(url="http://caa1.example.com/caa"),
                                           dcv_endpoint_info=PerspectiveEndpointInfo(url="http://dcv1.example.com/dcv")),
            "test-2": PerspectiveEndpoints(caa_endpoint_info=PerspectiveEndpointInfo(url="http://caa2.example.com/caa"),
                                           dcv_endpoint_info=PerspectiveEndpointInfo(url="http://dcv2.example.com/dcv"))
        }
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

    def constructor__should_initialize_mpic_coordinator_and_set_target_perspectives(self, set_env_variables):
        mpic_coordinator_service = MpicCoordinatorService()
        all_possible_perspectives = TestMpicCoordinatorLambda.get_perspectives_by_code_dict_from_file()
        for target_perspective in mpic_coordinator_service.target_perspectives:
            assert target_perspective in all_possible_perspectives.values()
        mpic_coordinator = mpic_coordinator_service.mpic_coordinator
        assert len(mpic_coordinator.target_perspectives) == 2
        assert mpic_coordinator_service.hash_secret == 'test_secret'
        assert mpic_coordinator_service.default_perspective_count == 2
        assert mpic_coordinator_service.global_max_attempts == 2

    @staticmethod
    def get_perspectives_by_code_dict_from_file() -> dict[str, RemotePerspective]:
        with resources.files('mpic_coordinator_service.resources').joinpath('available_perspectives.yaml').open('r') as file:
            perspectives_yaml = yaml.safe_load(file)
            perspective_type_adapter = TypeAdapter(list[RemotePerspective])
            perspectives = perspective_type_adapter.validate_python(perspectives_yaml['available_regions'])
            return {perspective.code: perspective for perspective in perspectives}
