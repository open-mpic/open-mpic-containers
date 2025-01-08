from fastapi import FastAPI  # type: ignore
from pathlib import Path

from open_mpic_core.common_domain.check_request import CaaCheckRequest
from open_mpic_core.mpic_caa_checker.mpic_caa_checker import MpicCaaChecker

import os
from dotenv import load_dotenv


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / 'config' / 'app.conf'
load_dotenv(config_path)


class MpicCaaCheckerService:
    def __init__(self):
        self.perspective_code = os.environ['code']
        self.default_caa_domain_list = os.environ['default_caa_domains'].split("|")
        self.caa_checker = MpicCaaChecker(self.default_caa_domain_list, self.perspective_code)

    async def check_caa(self, caa_request: CaaCheckRequest):
        return await self.caa_checker.check_caa(caa_request)


# Global instance for Service
_service = None


def get_service() -> MpicCaaCheckerService:
    """
    Singleton pattern to avoid recreating the service on every API all
    """
    global _service
    if _service is None:
        _service = MpicCaaCheckerService()
    return _service


app = FastAPI()


@app.post("/caa")
async def handle_caa_check(request: CaaCheckRequest):
    return await get_service().check_caa(request)
