from typing import Literal, Protocol
from shatter_api import Api, Mapping, JsonResponse, NotFoundResponse, ReqType
from .responses import SecretData, NotSupportedData, SecretNotFoundData
from .requests import KeyQueryParams, IDQueryParams, WriteSecretKeyQueryParams
from .middleware import WriteBlockPlaceHolder, ClientPlaceholder
from .client import SecretClient


class GenericSecretApi(Api, Protocol):
    mapping = Mapping("/genericsecret")

    @mapping.route("/key", middleware=[ClientPlaceholder])
    def get_key(
        self, params: KeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData] | JsonResponse[NotSupportedData] | JsonResponse[SecretNotFoundData, Literal[404]]:
        """
        Retrieve a secret key.
        """
        ...

    @mapping.route("/id", middleware=[ClientPlaceholder])
    def get_id(
        self, params: IDQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData] | JsonResponse[SecretNotFoundData, Literal[404]]:
        """
        Retrieve a secret by ID.
        """
        ...

    @mapping.route("/write/id", methods=[ReqType.POST], middleware=[WriteBlockPlaceHolder, ClientPlaceholder])
    def write_secret_key(
        self, params: WriteSecretKeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData, Literal[200]]:
        """
        Write a secret.
        """
        ...

    @mapping.route("/write/key", methods=[ReqType.POST], middleware=[WriteBlockPlaceHolder, ClientPlaceholder])
    def write_secret_id(
        self, params: WriteSecretKeyQueryParams, client: SecretClient
    ) -> JsonResponse[SecretData, Literal[200]] | JsonResponse[NotSupportedData]:
        """
        Write a secret.
        """
        ...
