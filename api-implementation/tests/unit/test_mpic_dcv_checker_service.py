import pytest

from mpic_dcv_checker_service.main import MpicDcvCheckerService


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
