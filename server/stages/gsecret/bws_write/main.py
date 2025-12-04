from typing import Any

from bws_sdk import Region
from bws_sdk.errors import (
    ApiError,
    APIRateLimitError,
    SecretParseError,
    SendRequestError,
    UnauthorisedError,
)
from core.chain.chain import ChainStageBuilder
from core.chain.controller import Chain, ForwardChainExecutor, ReverseChainExecutor
from interfaces.gsecret import (
    GSecretExecutor,
    GsecretFailure,
    Secret,
    Token,
    TokenID,
    UpdatedSecret,
    WriteSecret,
    gsecret_interface,
)
from pydantic import BaseModel

from .client_controller import BwsClientController


class BwsWriteRegionConfig(BaseModel):
    api_url: str = "https://api.bitwarden.com"
    identity_url: str = "https://identity.bitwarden.com"


class BwsWriteConfig(BaseModel):
    """Configuration for BWS Write stage"""

    region: BwsWriteRegionConfig = BwsWriteRegionConfig()

    project_ids: list[str] = []


class BwsWriteGSecretExecutor(GSecretExecutor):
    """Write-capable Bitwarden Secrets Manager executor using bws-sdk"""

    def __init__(
        self,
        config: BwsWriteConfig,
        controller: BwsClientController,
        chain: Chain[GSecretExecutor],
    ):
        self.config = config
        self.chain = chain
        self.client_controller = controller

        # Initialize BWS region configuration
        self.region = Region(
            api_url=config.region.api_url,
            identity_url=config.region.identity_url,
        )

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its ID from Bitwarden"""

        executor = next.next()
        if executor:
            return executor.get_secret_id(key_id, token, next)
        return GsecretFailure(reason="Secret not found", code=404)

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """
        Retrieve a secret by its key name from Bitwarden.
        Note: BWS SDK doesn't support direct key lookup, so we pass to next executor.
        """
        executor = next.next()
        if executor:
            return executor.get_secret_id(key, token, next)

        return GsecretFailure(reason="Secret not found", code=404)

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """Write a secret to Bitwarden Secrets Manager using bws-sdk"""
        try:
            client = self.client_controller.get_client(token, self.region)
            # Convert secret value to string if needed
            written = client.write_secret(
                secret=secret,
                project_ids=self.config.project_ids,
            )
            if written is not None:
                return written

        except UnauthorisedError:
            return GsecretFailure(reason="Unauthorized access", code=401)
        except APIRateLimitError:
            return GsecretFailure(reason="Rate limit exceeded", code=429)
        except SecretParseError as e:
            return GsecretFailure(reason=f"Secret parse error: {e!s}", code=500)
        except SendRequestError as e:
            return GsecretFailure(reason=f"Network request failed: {e!s}", code=503)
        except ApiError as e:
            return GsecretFailure(reason=f"API error: {e!s}", code=500)
        except Exception as e:
            return GsecretFailure(reason=f"Unexpected error: {e!s}", code=500)

        # If write failed to return a secret, try next executor
        executor = next.next()
        if executor:
            return executor.write_secret(secret, token, next)
        return GsecretFailure(reason="Write operation failed", code=500)

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications in reverse chain"""
        # Pass to next executor in reverse chain
        executor = next.next()
        if executor:
            return executor.secret_updated(secrets, token_hash, priority, next)


class BwsWriteGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for BWS Write stage"""

    def __init__(self):
        self.client_controller = BwsClientController()

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        parsed_config = BwsWriteConfig.model_validate(config)
        return BwsWriteGSecretExecutor(parsed_config, self.client_controller, chain)


# Register the stage builder with the gsecret interface
builder = BwsWriteGSecretStageBuilder()
gsecret_interface.register_stage("bws_write", builder)
