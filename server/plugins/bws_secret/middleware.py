from shatter_api import Middleware, CallNext, InheritedResponses, JsonResponse
from plugins.gsecret import SecretClient, UnauthorisedData, ClientPlaceholder, AuthHeader
from typing import Literal
from .client import BwsSecretClient
from .bws_client.client import BWSClient
from bws_sdk import Region

class BWSClientProvider(Middleware, ClientPlaceholder):
    """
    Middleware to provide a client instance for secret operations.
    This middleware is used to handle client operations in the API.
    """

    def __init__(self, region: Region):
        self.clients: dict[str, BwsSecretClient] = {}
        self.region = region
        super().__init__()

    def process(
        self, call_next: CallNext[SecretClient], auth_header: AuthHeader
    ) -> InheritedResponses | JsonResponse[UnauthorisedData, Literal[401]]:
        """
        Process the request and provide a client instance.
        """
        token = auth_header.authorization.removeprefix("Bearer ").strip()
        if token:
            if client := self.clients.get(token):
                return call_next(client)
            else:
                bws_client = BWSClient(token, self.region)
                client = BwsSecretClient(bws_client)
                self.clients[token] = client
                return call_next(client)
        else:
            return JsonResponse(UnauthorisedData(detail="Invalid Token"), 401)
