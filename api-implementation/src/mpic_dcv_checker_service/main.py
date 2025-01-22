import os
from contextlib import asynccontextmanager

from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from open_mpic_core.common_domain.check_request import DcvCheckRequest
from open_mpic_core.mpic_dcv_checker.mpic_dcv_checker import MpicDcvChecker

from common_configuration.opentelemetry_configuration import initialize_tracing_configuration

# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / 'config' / 'app.conf'
load_dotenv(config_path)


class MpicDcvCheckerService:
    def __init__(self):
        self.perspective_code = os.environ.get('code')
        self.verify_ssl = bool(os.environ.get('verify_ssl', False).lower()) is True
        self.dcv_checker = MpicDcvChecker(self.perspective_code, self.verify_ssl)

    async def initialize(self):
        await self.dcv_checker.initialize()

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
    await service.initialize()

    yield

    # Cleanup
    await service.shutdown()


app = FastAPI(lifespan=lifespan)
initialize_tracing_configuration()
FastAPIInstrumentor.instrument_app(app, excluded_urls='healthz', exclude_spans=['send', 'receive'])


@app.post("/dcv")
async def perform_mpic(request: DcvCheckRequest):
    # noinspection PyUnresolvedReferences
    return await get_service().check_dcv(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
