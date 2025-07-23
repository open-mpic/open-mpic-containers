import json
import os
import tomllib
import importlib.metadata
import tracemalloc

from pympler import muppy, summary

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
            if "http_client_timeout_seconds" in os.environ and float(os.environ["http_client_timeout_seconds"])
            else 30
        )
        self.dns_timeout_seconds = (
            float(os.environ["dns_timeout_seconds"]) if "dns_timeout_seconds" in os.environ else None
        )
        self.dns_resolution_lifetime_seconds = (
            float(os.environ["dns_resolution_lifetime_seconds"])
            if "dns_resolution_lifetime_seconds" in os.environ
            else None
        )

        self.dcv_checker = MpicDcvChecker(
            http_client_timeout=self.http_client_timeout_seconds,
            reuse_http_client=True,
            verify_ssl=self.verify_ssl,
            dns_timeout=self.dns_timeout_seconds,
            dns_resolution_lifetime=self.dns_resolution_lifetime_seconds,
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

# Start memory tracing for leak detection
tracemalloc.start(5)


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


class PrettyJSONResponse(JSONResponse):
    """
    Custom JSONResponse to pretty print the response body.
    """

    def render(self, content: dict) -> bytes:
        return json.dumps(
            content,
            ensure_ascii=False,
            allow_nan=False,
            indent=4,
            separators=(",", ": "),
        ).encode("utf-8")


# noinspection PyUnresolvedReferences
@app.post("/dcv")
async def perform_mpic(request: DcvCheckRequest):
    async with logger.trace_timing("Remote DCV check processing"):
        result = await get_service().check_dcv(request)
        logger.trace("DCV check result: %s", result)
        return result


@app.get("/healthz")
async def health_check():
    return {"status": "healthy"}


@app.get("/memprofilez")
async def memory_profile():
    """
    Endpoint to check for memory leaks.
    """
    all_objects = muppy.get_objects()
    sum_objects = summary.summarize(all_objects)

    # Convert summary to JSON-serializable format
    json_summary = []
    for row in sum_objects:
        if len(row) == 3:  # Ensure we have [type, count, size]
            json_summary.append({"type": row[0], "count": row[1], "size": row[2]})

    # Sort by size in descending order and limit to top 20
    json_summary.sort(key=lambda x: x["size"], reverse=True)
    json_summary = json_summary[:100]

    # Get total memory size
    total_memory = muppy.get_size(all_objects)

    tracemalloc_snapshot = tracemalloc.take_snapshot()
    filtered_snapshot = tracemalloc_snapshot.filter_traces(
        [
            tracemalloc.Filter(False, tracemalloc.__file__),
            tracemalloc.Filter(False, "muppy.py"),
            tracemalloc.Filter(False, "summary.py"),
        ]
    )
    top_stats = filtered_snapshot.statistics("traceback")
    tracebacks = [stat.traceback.format() for stat in top_stats[:20]]

    return PrettyJSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "message": "Memory profile",
            "summary": json_summary,
            "total_memory": total_memory,
            "top_tracebacks": tracebacks,
        },
    )


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
                result = {
                    "open_mpic_api_spec_version": pyproject["tool"]["api"]["spec_version"],
                    "app_version": pyproject["project"]["version"],
                    "mpic_core_version": importlib.metadata.version("open-mpic-core"),
                    "verify_ssl": get_service().verify_ssl,
                    "http_client_timeout_seconds": get_service().http_client_timeout_seconds,
                    "log_level": logger.getEffectiveLevel(),
                    "uvicorn_server_timeout_keep_alive": uvicorn_server_timeout_keep_alive,
                    "dns_timeout_seconds": get_service().dns_timeout_seconds,
                    "dns_resolution_lifetime_seconds": get_service().dns_resolution_lifetime_seconds,
                }
                return PrettyJSONResponse(
                    status_code=status.HTTP_200_OK,
                    content=result,
                )
        current = current.parent
    raise FileNotFoundError("Could not find pyproject.toml")
