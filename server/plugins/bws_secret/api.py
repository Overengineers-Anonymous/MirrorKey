import logging
from enum import Enum
from tkinter import E
from typing import Literal

from core.config import config
from plugins.gsecret import (
    GenericSecretApi,
    IDQueryParams,
    KeyQueryParams,
    NotSupportedData,
    SecretClient,
    SecretData,
    SecretNotFoundData,
    WriteBlockMiddleware,
    WriteSecretKeyQueryParams,
)
from pydantic import BaseModel
from pydantic.type_adapter import R
from shatter_api import JsonResponse, Mapping, ReqType, route_map
from bws_sdk import Region
from .middleware import BWSClientProvider


class RegionEnum(Enum):
    DEFAULT = "Default"
    EU = "EU"
    US = "US"

class BwsSecretConfig(BaseModel):
    write_enabled: bool = False
    region: RegionEnum = RegionEnum.DEFAULT


bws_config = config.plugin_config("bws_secret", BwsSecretConfig, required=True)

REGION_MAPPING = {
    RegionEnum.DEFAULT: Region(
        api_url="https://api.bitwarden.com",
        identity_url="https://identity.bitwarden.com",
    ),
    RegionEnum.EU: Region(api_url="https://api.bitwarden.eu", identity_url="https://identity.bitwarden.eu"),
}


write_block = WriteBlockMiddleware(bws_config.write_enabled)
client_provider = BWSClientProvider(REGION_MAPPING[bws_config.region])

logger = logging.getLogger(__name__)

class BwsSecretApi(GenericSecretApi):
    mapping = Mapping("/genericsecret/bws")

    @mapping.route("/key", middleware=[client_provider])
    def get_key(
        self, params: KeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData] | JsonResponse[NotSupportedData] | JsonResponse[SecretNotFoundData, Literal[404]]:
        """
        Retrieve a secret key.
        """
        secret = client.get_secret_by_key(params.key)
        if secret:
            return JsonResponse(secret)
        return JsonResponse(SecretNotFoundData(), 404)

    @mapping.route("/id", middleware=[client_provider])
    def get_id(
        self, params: IDQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData] | JsonResponse[SecretNotFoundData, Literal[404]]:
        """
        Retrieve a secret by ID.
        """
        secret = client.get_secret_by_id(params.id)
        if secret:
            return JsonResponse(secret)
        return JsonResponse(SecretNotFoundData(), 404)

    @mapping.route("/write/id", methods=[ReqType.POST], middleware=[write_block, client_provider])
    def write_secret_key(
        self, params: WriteSecretKeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData, Literal[200]]:
        """
        Write a secret.
        """
        ...
    @mapping.route("/write/key", methods=[ReqType.POST], middleware=[write_block, client_provider])
    def write_secret_id(
        self, params: WriteSecretKeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData, Literal[200]] | JsonResponse[NotSupportedData]:
        """
        Write a secret.
        """
        ...

api = BwsSecretApi()
print(api.mapping.paths)
route_map.add_api(api)
