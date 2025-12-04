from typing import Any

from bws_sdk import Region
from bws_sdk.errors import (
    ApiError,
    APIRateLimitError,
    SecretNotFoundError,
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


class BwsReadConfig(BaseModel):
    """Configuration for BWS Read stage"""

    api_url: str = "https://api.bitwarden.com"
    identity_url: str = "https://identity.bitwarden.com"


class BwsReadGSecretExecutor(GSecretExecutor):
    """Read-only Bitwarden Secrets Manager executor using bws-sdk"""

    def __init__(
        self,
        config: BwsReadConfig,
        controller: BwsClientController,
        chain: Chain[GSecretExecutor],
    ):
        self.config = config
        self.chain = chain
        self.client_controller = controller

        # Initialize BWS region configuration
        self.region = Region(
            api_url=config.api_url,
            identity_url=config.identity_url,
        )

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its ID from Bitwarden"""
        try:
            client = self.client_controller.get_client(
                token, self.region, self.secrets_sync
            )
            secret = client.get_by_id(key_id)
            if secret is not None:
                return secret

        except UnauthorisedError:
            return GsecretFailure(reason="Unauthorized access", code=401)
        except APIRateLimitError:
            return GsecretFailure(reason="Rate limit exceeded", code=429)
        except ApiError as e:
            return GsecretFailure(reason=f"API error: {e!s}", code=500)
        except Exception as e:
            return GsecretFailure(reason=f"Unexpected error: {e!s}", code=500)

        executor = next.next()
        if executor:
            stage, next_executor = executor
            return stage.get_secret_id(key_id, token, next_executor)
        return GsecretFailure(reason="Secret not found", code=404)

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """
        Retrieve a secret by its key name from Bitwarden.
        Note: BWS SDK doesn't support direct key lookup, so we pass to next executor.
        """
        # BWS SDK only supports get_by_id, not get_by_key
        # Pass to next executor in chain
        try:
            client = self.client_controller.get_client(
                token, self.region, self.secrets_sync
            )
            secret = client.get_by_key(key)
            if secret:
                return secret
        except SecretNotFoundError:
            # Try next executor in chain if secret not found
            pass
        except UnauthorisedError:
            return GsecretFailure(reason="Unauthorized access", code=401)
        except APIRateLimitError:
            return GsecretFailure(reason="Rate limit exceeded", code=429)
        except ApiError as e:
            return GsecretFailure(reason=f"API error: {e!s}", code=500)
        except Exception as e:
            return GsecretFailure(reason=f"Unexpected error: {e!s}", code=500)
        executor = next.next()
        if executor:
            stage, next_executor = executor
            return stage.get_secret_id(key, token, next_executor)

        return GsecretFailure(reason="Secret not found", code=404)

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """
        Write operations are not supported in read-only mode.
        Pass to next executor in chain.
        """
        # This is a read-only executor, pass to next
        executor = next.next()
        if executor:
            stage, next_executor = executor
            return stage.write_secret(secret, token, next_executor)
        return GsecretFailure(
            reason="Write operations not supported in BWS read-only mode", code=501
        )

    def secrets_sync(self, token_hash: TokenID, secrets: list[UpdatedSecret]):
        print("Syncing secrets update notification...", len(secrets))
        chain_controller = ReverseChainExecutor(
            self.chain, self.chain.get_stage_index(self)
        )
        executor = chain_controller.next()
        if executor:
            stage, next_executor = executor
            stage.secret_updated(
                secrets, token_hash, self.chain.get_stage_index(self), next_executor
            )

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications in reverse chain"""
        # For read-only mode, we don't need to handle updates
        # Just pass to next executor
        executor = next.next()
        if executor:
            stage, next_executor = executor
            return stage.secret_updated(secrets, token_hash, priority, next_executor)


class BwsReadGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for BWS Read stage"""

    def __init__(self):
        self.client_controller = BwsClientController()

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        parsed_config = BwsReadConfig.model_validate(config)
        return BwsReadGSecretExecutor(parsed_config, self.client_controller, chain)


# Register the stage builder with the gsecret interface
builder = BwsReadGSecretStageBuilder()
gsecret_interface.register_stage("bws_read", builder)
