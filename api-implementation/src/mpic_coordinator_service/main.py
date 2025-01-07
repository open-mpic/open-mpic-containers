import os
import json
from contextlib import asynccontextmanager

import yaml
import aiohttp
import requests

from dotenv import load_dotenv
from pathlib import Path
from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from pydantic import TypeAdapter, BaseModel, Field

from open_mpic_core.mpic_coordinator.domain.mpic_request_validation_error import MpicRequestValidationError
from open_mpic_core.mpic_coordinator.messages.mpic_request_validation_messages import MpicRequestValidationMessages
from open_mpic_core.common_domain.check_request import BaseCheckRequest
from open_mpic_core.common_domain.check_response import CheckResponse
from open_mpic_core.mpic_coordinator.domain.mpic_request import MpicRequest
from open_mpic_core.mpic_coordinator.mpic_coordinator import MpicCoordinator, MpicCoordinatorConfiguration
from open_mpic_core.common_domain.enum.check_type import CheckType
from open_mpic_core.mpic_coordinator.domain.remote_perspective import RemotePerspective
from open_mpic_core.mpic_coordinator.domain.mpic_response import MpicResponse


# 'config' directory should be a sibling of the directory containing this file
config_path = Path(__file__).parent / 'config' / 'app.conf'
load_dotenv(config_path)


class PerspectiveEndpointInfo(BaseModel):
    url: str
    headers: dict[str, str] | None = Field(default_factory=dict)


class PerspectiveEndpoints(BaseModel):
    dcv_endpoint_info: PerspectiveEndpointInfo
    caa_endpoint_info: PerspectiveEndpointInfo


class MpicCoordinatorService:
    def __init__(self):
        # load environment variables
        perspectives_json = os.environ['perspectives']
        perspectives = {code: PerspectiveEndpoints.model_validate(endpoints) for code, endpoints in json.loads(perspectives_json).items()}
        self.all_target_perspective_codes = list(perspectives.keys())
        self.default_perspective_count = int(os.environ['default_perspective_count'])
        self.global_max_attempts = int(os.environ['absolute_max_attempts']) if 'absolute_max_attempts' in os.environ else None
        self.hash_secret = os.environ['hash_secret']

        self.remotes_per_perspective_per_check_type = {
            CheckType.DCV: {perspective_code: perspective_config.dcv_endpoint_info for perspective_code, perspective_config in perspectives.items()},
            CheckType.CAA: {perspective_code: perspective_config.caa_endpoint_info for perspective_code, perspective_config in perspectives.items()}
        }

        all_possible_perspectives_by_code = MpicCoordinatorService.load_available_perspectives_config()
        self.target_perspectives = MpicCoordinatorService.convert_codes_to_remote_perspectives(
            self.all_target_perspective_codes, all_possible_perspectives_by_code)

        self.mpic_coordinator_configuration = MpicCoordinatorConfiguration(
            self.target_perspectives,
            self.default_perspective_count,
            self.global_max_attempts,
            self.hash_secret
        )

        self._async_http_client = None

        self.mpic_coordinator = MpicCoordinator(
            self.call_remote_perspective,
            self.mpic_coordinator_configuration
        )

        # for correct deserialization of responses based on discriminator field (check type)
        self.mpic_request_adapter = TypeAdapter(MpicRequest)
        self.check_response_adapter = TypeAdapter(CheckResponse)

    async def initialize(self):
        if self._async_http_client is None:
            self._async_http_client = aiohttp.ClientSession()

    async def shutdown(self):
        if self._async_http_client:
            await self._async_http_client.close()
            self._async_http_client = None

    @staticmethod
    def load_available_perspectives_config() -> dict[str, RemotePerspective]:
        """
        Reads in the available perspectives from a configuration yaml and returns them as a dict (map).
        Expects the yaml to be in the resources folder, next to the app folder containing this file.
        :return: dict of available perspectives with region code as key
        """
        resource_path = Path(__file__).parent / 'resources' / 'available_perspectives.yaml'

        with resource_path.open() as file:
            region_config_yaml = yaml.safe_load(file)
            region_type_adapter = TypeAdapter(list[RemotePerspective])
            regions_list = region_type_adapter.validate_python(region_config_yaml['available_regions'])
            regions_dict = {region.code: region for region in regions_list}
            return regions_dict

    @staticmethod
    def convert_codes_to_remote_perspectives(perspective_codes: list[str],
                                             all_possible_perspectives_by_code: dict[str, RemotePerspective]) -> list[RemotePerspective]:
        remote_perspectives = []

        for perspective_code in perspective_codes:
            if perspective_code not in all_possible_perspectives_by_code.keys():
                continue  # TODO throw an error? check this case in the validator?
            else:
                fully_defined_perspective = all_possible_perspectives_by_code[perspective_code]
                remote_perspectives.append(fully_defined_perspective)

        return remote_perspectives

    # This function MUST validate its response and return a proper open_mpic_core object type.
    async def call_remote_perspective(self, perspective: RemotePerspective, check_type: CheckType, check_request: BaseCheckRequest) -> CheckResponse:
        if self._async_http_client is None:
            raise RuntimeError("Service not initialized - call initialize() first")

        # Get the remote info from the data structure.
        endpoint_info: PerspectiveEndpointInfo = self.remotes_per_perspective_per_check_type[check_type][perspective.code]

        async with self._async_http_client.post(
                url=endpoint_info.url, headers=endpoint_info.headers, json=check_request.model_dump()
        ) as response:
            text = await response.text()
            return self.check_response_adapter.validate_json(text)

    async def perform_mpic(self, mpic_request: MpicRequest) -> MpicResponse:
        return await self.mpic_coordinator.coordinate_mpic(mpic_request)


# Global instance for Service
_service = None


def get_service() -> MpicCoordinatorService:
    """
    Singleton pattern to avoid recreating the service on every call
    """
    global _service
    if _service is None:
        _service = MpicCoordinatorService()
    return _service


@asynccontextmanager
async def lifespan(app_instance: FastAPI):
    # Initialize services
    service = get_service()
    await service.initialize()

    yield

    # Cleanup
    await service.shutdown()


app = FastAPI(lifespan=lifespan)


# noinspection PyUnusedLocal
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, e: RequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,  # If you want to use 400 instead of 422
        content={
            "error": MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key,
            "validation_issues": e.errors()
        }
    )


# noinspection PyUnusedLocal
@app.exception_handler(MpicRequestValidationError)
async def mpic_validation_exception_handler(request: Request, e: MpicRequestValidationError):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,  # If you want to use 400 instead of 422
        content={
            "error": MpicRequestValidationMessages.REQUEST_VALIDATION_FAILED.key,
            "validation_issues": json.loads(e.__notes__[0])
        }
    )


@app.middleware("http")  # This is a middleware that catches general exceptions and returns a 500 response
async def exception_handling_middleware(request: Request, call_next):
    try:
        return await call_next(request)
    except Exception as e:
        # Do some logging here
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "error": str(e)
            }
        )


@app.post("/mpic")
async def handle_mpic(request: MpicRequest):
    return await get_service().perform_mpic(request)
