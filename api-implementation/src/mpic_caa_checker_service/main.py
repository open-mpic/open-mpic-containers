import os

from fastapi import FastAPI  # type: ignore
from pathlib import Path
from dotenv import load_dotenv
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

from open_mpic_core.common_domain.check_request import CaaCheckRequest
from open_mpic_core.mpic_caa_checker.mpic_caa_checker import MpicCaaChecker
from common_configuration.opentelemetry_configuration import initialize_tracing_configuration

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


def get_service() -> MpicCaaCheckerService:
    """
    Singleton pattern to avoid recreating the service on every API all
    """
    global _service
    if _service is None:
        _service = MpicCaaCheckerService()
    return _service


_service = None  # Global instance for Service
app = FastAPI()
initialize_tracing_configuration()
FastAPIInstrumentor.instrument_app(app, excluded_urls='healthz', exclude_spans=['send', 'receive'])


@app.post("/caa")
async def handle_caa_check(request: CaaCheckRequest):
    # noinspection PyUnresolvedReferences
    # with tracer.start_as_current_span("Remote CAA check processing"):
    return await get_service().check_caa(request)


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}
