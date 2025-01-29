import os

from fastapi import FastAPI  # type: ignore
from pathlib import Path
from dotenv import load_dotenv

from open_mpic_core import CaaCheckRequest, MpicCaaChecker, get_logger

# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
load_dotenv(config_path)
logger = get_logger(__name__)


class MpicCaaCheckerService:
    def __init__(self):
        self.perspective_code = os.environ["code"]
        self.default_caa_domain_list = os.environ["default_caa_domains"].split("|")

        # FIXME fail on perspective_code None or empty -- necessary for interpreting check results
        # FIXME warn on default_caa_domain_list None or empty

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
    # noinspection PyUnresolvedReferences
    async with logger.trace_timing("Remote CAA check processing"):
        return await get_service().check_caa(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
