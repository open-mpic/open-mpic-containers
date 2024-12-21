from fastapi import FastAPI  # type: ignore

from open_mpic_core.common_domain.check_request import CaaCheckRequest
from open_mpic_core.mpic_caa_checker.mpic_caa_checker import MpicCaaChecker

import os
from dotenv import load_dotenv

load_dotenv("config/app.conf")


class MpicCaaCheckerService:
    def __init__(self):
        self.perspective_code = os.environ['code']
        self.default_caa_domain_list = os.environ['default_caa_domains'].split("|")
        self.caa_checker = MpicCaaChecker(self.default_caa_domain_list, self.perspective_code)

    def check_caa(self, caa_request: CaaCheckRequest):
        return self.caa_checker.check_caa(caa_request)
        # result = {
        #     'statusCode': 200,  # note: must be snakeCase
        #     'headers': {'Content-Type': 'application/json'},
        #     'body': caa_response.model_dump_json()
        # }
        # return result


# Global instance for Lambda runtime
_service = None


def get_service() -> MpicCaaCheckerService:
    """
    Singleton pattern to avoid recreating the handler on every Lambda invocation
    """
    global _service
    if _service is None:
        _service = MpicCaaCheckerService()
    return _service


app = FastAPI()


@app.post("/caa")
def perform_mpic(request: CaaCheckRequest):
    return get_service().check_caa(request)
