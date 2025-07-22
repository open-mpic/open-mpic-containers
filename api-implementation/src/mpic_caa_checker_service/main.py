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
        self.dns_timeout_seconds = (
            float(os.environ["dns_timeout_seconds"]) if "dns_timeout_seconds" in os.environ else None
        )
        self.dns_resolution_lifetime_seconds = (
            float(os.environ["dns_resolution_lifetime_seconds"])
            if "dns_resolution_lifetime_seconds" in os.environ
            else None
        )
        self.caa_checker = MpicCaaChecker(
            self.default_caa_domain_list,
            dns_timeout=self.dns_timeout_seconds,
            dns_resolution_lifetime=self.dns_resolution_lifetime_seconds,
        )

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
        logger.trace("CAA check result: %s", result)
        return result


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/configz")
async def get_config():
    current = Path(__file__).parent
    for _ in range(3):  # Try up to 3 levels up (Docker flattens the file structure a fair bit)
        path_to_project_config = current / "pyproject.toml"
        if path_to_project_config.exists():
            with path_to_project_config.open(mode="rb") as file:
                pyproject = tomllib.load(file)
                uvicorn_server_timeout_keep_alive = (
                    int(os.environ["uvicorn_server_timeout_keep_alive"])
                    if "uvicorn_server_timeout_keep_alive" in os.environ
                    else None
                )
                return {
                    "open_mpic_api_spec_version": pyproject["tool"]["api"]["spec_version"],
                    "app_version": pyproject["project"]["version"],
                    "mpic_core_version": importlib.metadata.version("open-mpic-core"),
                    "default_caa_domains": get_service().default_caa_domain_list,
                    "log_level": logger.getEffectiveLevel(),
                    "uvicorn_server_timeout_keep_alive": uvicorn_server_timeout_keep_alive,
                    "dns_timeout_seconds": get_service().dns_timeout_seconds,
                    "dns_resolution_lifetime_seconds": get_service().dns_resolution_lifetime_seconds,
                }
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
