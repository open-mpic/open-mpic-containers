from fastapi import FastAPI

from open_mpic_core.common_domain.check_request import DcvCheckRequest
from open_mpic_core.mpic_dcv_checker.mpic_dcv_checker import MpicDcvChecker

import os
from dotenv import load_dotenv

load_dotenv("config/app.conf")


class MpicDcvCheckerService:
    def __init__(self):
        self.perspective_code = os.environ['code']
        self.dcv_checker = MpicDcvChecker(self.perspective_code)

    def check_dcv(self, dcv_request: DcvCheckRequest):
        return self.dcv_checker.check_dcv(dcv_request)
        # status_code = 200
        # if dcv_response.errors is not None and len(dcv_response.errors) > 0:
        #     if dcv_response.errors[0].error_type == '404':
        #         status_code = 404
        #     else:
        #         status_code = 500
        # result = {
        #     'statusCode': status_code,
        #     'headers': {'Content-Type': 'application/json'},
        #     'body': dcv_response.model_dump_json()
        # }
        # return result


# Global instance for Service
_service = None


def get_service() -> MpicDcvCheckerService:
    """
    Singleton pattern to avoid recreating the service on every call
    """
    global _service
    if _service is None:
        _service = MpicDcvCheckerService()
    return _service


app = FastAPI()


@app.post("/dcv")
def perform_mpic(request: DcvCheckRequest):
    return get_service().check_dcv(request)
