import time
import datetime
import random

from pathlib import Path
from pydantic import TypeAdapter
from locust import HttpUser, task, events, tag, FastHttpUser, run_single_user, between, constant
# from locust.runners import MasterRunner

from open_mpic_core import (
    MpicResponse,
    MpicCaaRequest,
    MpicRequestOrchestrationParameters,
    CaaCheckParameters,
    CertificateType,
    MpicCaaResponse,
)

test_domain_list: list[str] = []
mpic_response_adapter = TypeAdapter(MpicResponse)


def timestring() -> str:
    now = datetime.datetime.now()
    return datetime.datetime.strftime(now, "%m:%S.%f")[:-5]


class LocalDockerComposeUser(HttpUser):
    wait_time = constant(0)  # between(1, 2)  # wait between 1 and 2 seconds after each task, for now
    host = "http://localhost:8000/mpic-coordinator"
    network_timeout = 10

    @tag("caa")
    @task
    def do_one_mpic_caa_request(self):
        # select random domain from test_domain_list (it's been read in, has X length)
        target_domain = random.choice(test_domain_list)
        headers = {"Content-Type": "application/json"}
        print(f"CAA for domain: {target_domain}")

        request = MpicCaaRequest(
            trace_identifier=f"test_trace_id_{time.time()}",  # unique trace id for each request
            domain_or_ip_target=target_domain,
            orchestration_parameters=MpicRequestOrchestrationParameters(perspective_count=2, quorum_count=2),
            caa_check_parameters=CaaCheckParameters(
                certificate_type=CertificateType.TLS_SERVER, caa_domains=["mozilla.com"]
            ),
        )

        data = request.model_dump_json()

        print(f"request: {data}")

        with self.client.post("/mpic", headers=headers, data=data, catch_response=True) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected response code: {response.status_code}")
            else:
                mpic_response: MpicCaaResponse = mpic_response_adapter.validate_json(response.text)
                print(f"{timestring()} response: {response.text}")
                if mpic_response.mpic_completed is False:
                    response.failure("MPIC did not complete successfully")
                else:
                    response.success()


@events.test_start.add_listener
def on_locust_init(environment, **_kwargs):
    print("Initializing locust environment...")
    # if isinstance(environment.runner, MasterRunner):
    global test_domain_list
    # read in the test domain list file that's in the same directory as this file, each line is a domain
    resource_path = Path(__file__).parent.parent / "resources" / "target_domains.txt"
    with resource_path.open() as file:
        test_domain_list = [line.strip() for line in file]


# if launched directly, e.g. "python3 debugging.py", not "locust -f debugging.py"
if __name__ == "__main__":
    run_single_user(LocalDockerComposeUser)
