import os
import tomllib
import importlib.metadata

from fastapi import FastAPI  # type: ignore
from pathlib import Path
from dotenv import load_dotenv

from open_mpic_core import CaaCheckRequest
from open_mpic_core import MpicCaaChecker
from open_mpic_core import get_logger


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / "config" / "app.conf"
logger = get_logger(__name__)


class MpicCaaCheckerService:
    def __init__(self):
        load_dotenv(config_path)
        # FIXME warn on default_caa_domain_list None or empty
        self.default_caa_domain_list = os.environ["default_caa_domains"].split("|")
        self.caa_checker = MpicCaaChecker(self.default_caa_domain_list)

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


# noinspection PyUnresolvedReferences
@app.post("/caa")
async def handle_caa_check(request: CaaCheckRequest):
    async with logger.trace_timing("Remote CAA check processing"):
        result = await get_service().check_caa(request)
        logger.trace(f"CAA check result: {result}")
        return result


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
                    "default_caa_domains": get_service().default_caa_domain_list,
                    "log_level": logger.getEffectiveLevel(),
                }
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
