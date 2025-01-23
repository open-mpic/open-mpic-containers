import os
from contextlib import asynccontextmanager

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse

from open_mpic_core.common_domain.check_request import DcvCheckRequest
from open_mpic_core.mpic_dcv_checker.mpic_dcv_checker import MpicDcvChecker
from open_mpic_core.common_util.trace_level_logger import get_logger


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / 'config' / 'app.conf'
load_dotenv(config_path)
logger = get_logger(__name__)


class MpicDcvCheckerService:
    def __init__(self):
        self.perspective_code = os.environ['code']
        self.verify_ssl = 'verify_ssl' not in os.environ or os.environ['verify_ssl'] == 'True'
        self.dcv_checker = MpicDcvChecker(
            perspective_code=self.perspective_code, reuse_http_client=True, verify_ssl=self.verify_ssl
        )

    async def shutdown(self):
        await self.dcv_checker.shutdown()

    async def check_dcv(self, dcv_request: DcvCheckRequest):
        result = await self.dcv_checker.check_dcv(dcv_request)
        if result.errors is not None and len(result.errors) > 0:
            if result.errors[0].error_type == '404':
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            result = JSONResponse(
                status_code=status_code,  # If you want to use 400 instead of 422
                content=result.model_dump()
            )
        return result


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


# noinspection PyUnusedLocal
@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Initialize services
    service = get_service()
    yield
    await service.shutdown()


app = FastAPI(lifespan=lifespan)


@app.post("/dcv")
async def perform_mpic(request: DcvCheckRequest):
    # noinspection PyUnresolvedReferences
    async with logger.trace_timing('Remote DCV check processing'):
        return await get_service().check_dcv(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
