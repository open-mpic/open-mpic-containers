from mpic_caa_checker_service import MpicCaaCheckerService


# noinspection PyMethodMayBeStatic
class TestMpicCaaCheckerServiceLambda:
    def service__should_read_in_environment_configuration_through_config_file(self):
        service = MpicCaaCheckerService()
        # it'll read in the placeholder values in the config files -- that's acceptable for this particular test
        assert service.perspective_code == 'PERSPECTIVE_NAME_CODE_STRING'
