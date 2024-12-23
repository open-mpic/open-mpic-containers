from mpic_dcv_checker_service.main import MpicDcvCheckerService


# noinspection PyMethodMayBeStatic
class TestMpicDcvCheckerServiceLambda:
    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicDcvCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        # note: this test is semi-invalidated by other tests that check this value because it's a global load
        assert service.perspective_code == 'PERSPECTIVE_NAME_CODE_STRING'
