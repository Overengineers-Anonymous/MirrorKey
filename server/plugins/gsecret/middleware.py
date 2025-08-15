from typing import Literal, Protocol
from shatter_api import Middleware, PlaceholderMiddleware, CallNext, InheritedResponses, JsonResponse
from .responses import NotSupportedData, UnauthorisedData
from .requests import AuthHeader
from .client import SecretClient

class WriteBlockPlaceHolder(PlaceholderMiddleware, Protocol):
    """
    Middleware to handle write operations for secrets.
    This middleware is used to block write operations if the key is not supported.
    """

    def process(self, call_next: CallNext) -> InheritedResponses | JsonResponse[NotSupportedData, Literal[403]]: ...


class WriteBlockMiddleware(Middleware, WriteBlockPlaceHolder):
    """
    Middleware to block write operations for secrets.
    This middleware is used to block write operations if the key is not supported.
    """

    def __init__(self, write_blocked: bool):
        self.write_blocked = write_blocked
        super().__init__()

    def process(self, call_next: CallNext) -> InheritedResponses | JsonResponse[NotSupportedData, Literal[403]]:
        if self.write_blocked:
            return JsonResponse(NotSupportedData(), 403)
        return call_next()


class ClientPlaceholder(PlaceholderMiddleware, Protocol):
    """
    Placeholder middleware for client operations.
    This middleware is used to handle client operations in the API.
    """

    def process(
        self, call_next: CallNext[SecretClient], auth_header: AuthHeader
    ) -> InheritedResponses | JsonResponse[UnauthorisedData, Literal[401]]: ...
