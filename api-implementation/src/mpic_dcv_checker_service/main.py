import os
import tomllib
import importlib.metadata

from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from open_mpic_core import DcvCheckRequest
from open_mpic_core import MpicDcvChecker
from open_mpic_core import get_logger

# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
logger = get_logger(__name__)


class MpicDcvCheckerService:
    def __init__(self):
        load_dotenv(config_path)
        self.verify_ssl = "verify_ssl" not in os.environ or os.environ["verify_ssl"] == "True"
        self.http_client_timeout_seconds = (
            float(os.environ["http_client_timeout_seconds"])
            if "http_client_timeout_seconds" in os.environ
            else 30
        )
        self.dcv_checker = MpicDcvChecker(
            http_client_timeout=self.http_client_timeout_seconds, reuse_http_client=True, verify_ssl=self.verify_ssl
        )

    async def shutdown(self):
        await self.dcv_checker.shutdown()

    async def check_dcv(self, dcv_request: DcvCheckRequest):
        result = await self.dcv_checker.check_dcv(dcv_request)
        if result.errors is not None and len(result.errors) > 0:
            if result.errors[0].error_type == "404":
                status_code = status.HTTP_404_NOT_FOUND
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            result = JSONResponse(
                status_code=status_code, content=result.model_dump()  # If you want to use 400 instead of 422
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
    async with logger.trace_timing("Remote DCV check processing"):
        return await get_service().check_dcv(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/configz")
async def get_config():
    current = Path(__file__).parent
    for _ in range(3):  # Try up to 3 levels up (Docker flattens the file structure a fair bit)
        test_path = current / "pyproject.toml"
        if test_path.exists():
            with test_path.open(mode="rb") as file:
                pyproject = tomllib.load(file)
                return {
                    "open_mpic_api_spec_version": pyproject["tool"]["api"]["spec_version"],
                    "app_version": pyproject["project"]["version"],
                    "mpic_core_version": importlib.metadata.version("open-mpic-core"),
                    "verify_ssl": get_service().verify_ssl,
                    "http_client_timeout_seconds": get_service().http_client_timeout_seconds,
                }
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
