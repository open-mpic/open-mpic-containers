import json
import sys
import pytest
import time

from open_mpic_core.common_domain.check_parameters import DcvDnsPersistentValidationParameters
from open_mpic_core.mpic_coordinator.domain.mpic_response import MpicDcvResponse
from pydantic import TypeAdapter

from open_mpic_core import CaaCheckParameters, DcvWebsiteChangeValidationParameters, PerspectiveResponse
from open_mpic_core import CertificateType
from open_mpic_core import CheckType
from open_mpic_core import MpicCaaRequest, MpicDcvRequest, MpicCaaResponse
from open_mpic_core import MpicRequestOrchestrationParameters
from open_mpic_core import MpicResponse, MpicRequestValidationMessages

import testing_api_client

MPIC_REQUEST_PATH = "mpic"


# noinspection PyMethodMayBeStatic
@pytest.mark.integration
class TestDeployedMpicApi:
    @classmethod
    def setup_class(cls):
        cls.mpic_response_adapter = TypeAdapter(MpicResponse)

    @pytest.fixture(scope="class")
    def api_client(self):
        with pytest.MonkeyPatch.context() as class_scoped_monkeypatch:
            # blank out argv except first param; arg parser doesn't expect pytest args
            class_scoped_monkeypatch.setattr(sys, "argv", sys.argv[:1])
            api_client = testing_api_client.TestingApiClient()
            yield api_client
            api_client.close()

    def api_should_return_200_and_passed_corroboration_given_successful_caa_check(self, api_client):
        request = MpicCaaRequest(
            trace_identifier=f"test_trace_id_{time.time()}",  # unique trace id for each request
            domain_or_ip_target="example.com",
            orchestration_parameters=MpicRequestOrchestrationParameters(perspective_count=2, quorum_count=2),
            caa_check_parameters=CaaCheckParameters(
                certificate_type=CertificateType.TLS_SERVER, caa_domains=["mozilla.com"]
            ),
        )

        print("\nRequest:\n", json.dumps(request.model_dump(), indent=4))  # pretty print request body
        response = api_client.post(MPIC_REQUEST_PATH, json.dumps(request.model_dump()))
        # assert response body has a list of perspectives with length 2, and each element has response code 200
        print("\nResponse:\n", json.dumps(json.loads(response.text), indent=4))  # pretty print response body
        assert response.status_code == 200
        mpic_response: MpicCaaResponse = self.mpic_response_adapter.validate_json(response.text)
        perspectives: list[PerspectiveResponse] = mpic_response.perspectives
        assert mpic_response.is_valid is True
        assert mpic_response.domain_or_ip_target == request.domain_or_ip_target
        assert len(perspectives) == request.orchestration_parameters.perspective_count
        assert (
            len(list(filter(lambda perspective: perspective.check_response.check_type == CheckType.CAA, perspectives)))
            == request.orchestration_parameters.perspective_count
        )

    def api_should_support_persistent_dns_validation_method(self, api_client):
        request = MpicDcvRequest(
            trace_identifier=f"test_trace_id_{time.time()}",
            domain_or_ip_target="dns-persist.integration-testing.open-mpic.org",
            orchestration_parameters=MpicRequestOrchestrationParameters(perspective_count=2, quorum_count=2),
            dcv_check_parameters=DcvDnsPersistentValidationParameters(
                issuer_domain_names=["example-ca.example.com"],
                expected_account_uri="https://example-ca.example.com/acct/123",
            ),
        )
        print("\nRequest:\n", json.dumps(request.model_dump(), indent=4))  # pretty print request body
        response = api_client.post(MPIC_REQUEST_PATH, json.dumps(request.model_dump()))
        print("\nResponse:\n", json.dumps(json.loads(response.text), indent=4))  # pretty print response body
        assert response.status_code == 200
        mpic_response: MpicDcvResponse = self.mpic_response_adapter.validate_json(response.text)
        assert mpic_response.is_valid is True

    @pytest.mark.skip(reason="working on getting the first test to pass")
    def api_should_return_200_and_failed_corroboration_given_failed_dcv_check(self, api_client):
        request = MpicDcvRequest(
            domain_or_ip_target="ifconfig.me",
            dcv_check_parameters=DcvWebsiteChangeValidationParameters(http_token_path="/", challenge_value="test"),
        )

        print("\nRequest:\n", json.dumps(request.model_dump(), indent=4))  # pretty print request body
        response = api_client.post(MPIC_REQUEST_PATH, json.dumps(request.model_dump()))
        assert response.status_code == 200
        response_body = json.loads(response.text)
        print("\nResponse:\n", json.dumps(response_body, indent=4))  # pretty print response body

    @pytest.mark.skip(reason="working on getting the first test to pass")
    def api_should_return_400_given_invalid_orchestration_parameters_in_request(self, api_client):
        request = MpicCaaRequest(
            domain_or_ip_target="example.com",
            orchestration_parameters=MpicRequestOrchestrationParameters(
                perspective_count=3, quorum_count=5
            ),  # invalid quorum count
            caa_check_parameters=CaaCheckParameters(
                certificate_type=CertificateType.TLS_SERVER, caa_domains=["mozilla.com"]
            ),
        )

        print("\nRequest:\n", json.dumps(request.model_dump(), indent=4))  # pretty print request body
        response = api_client.post(MPIC_REQUEST_PATH, json.dumps(request.model_dump()))
        assert response.status_code == 400
        response_body = json.loads(response.text)
        print("\nResponse:\n", json.dumps(response_body, indent=4))  # pretty print response body
        assert response_body["error"] == MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key
        assert any(
            issue["issue_type"] == MpicRequestValidationMessages.INVALID_QUORUM_COUNT.key
            for issue in response_body["validation_issues"]
        )

    @pytest.mark.skip(reason="working on getting the first test to pass")
    def api_should_return_400_given_invalid_check_type_in_request(self, api_client):
        request = MpicCaaRequest(
            domain_or_ip_target="example.com",
            orchestration_parameters=MpicRequestOrchestrationParameters(perspective_count=3, quorum_count=2),
            caa_check_parameters=CaaCheckParameters(
                certificate_type=CertificateType.TLS_SERVER, caa_domains=["mozilla.com"]
            ),
        )
        request.check_type = "invalid_check_type"

        print("\nRequest:\n", json.dumps(request.model_dump(), indent=4))  # pretty print request body
        response = api_client.post(MPIC_REQUEST_PATH, json.dumps(request.model_dump()))
        assert response.status_code == 400
        response_body = json.loads(response.text)
        print("\nResponse:\n", json.dumps(response_body, indent=4))
        assert response_body["error"] == MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key
