from typing import Any

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

from .buffer import BufferController, BufferDelay, BufferedStageClient, BufferRateLimits


class RateLimiterConfig(BaseModel):
    """Configuration for Rate Limiter stage"""

    default_delay: float = 2.0  # Default delay in seconds for buffering
    timeout: float = 10


class RateLimiterGSecretExecutor(GSecretExecutor):
    """
    Rate limiting executor that buffers requests to prevent overwhelming downstream services.
    Implements a sliding window rate limiter with request buffering.
    """

    def __init__(self, stage_client: BufferedStageClient, config: RateLimiterConfig):
        self.stage_client = stage_client
        self.config = config

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by ID with rate limiting"""
        delay = BufferDelay(timeout=self.config.timeout)
        self.stage_client.id_delay(key_id, delay)
        executor = next.next()
        if executor:
            secret = executor.get_secret_id(key_id, token, next)
            if isinstance(secret, Secret) and secret.rate_limit is not None:
                self.stage_client.log_id_rate_limit(
                    key_id,
                    secret.rate_limit.api_relation,
                    BufferRateLimits(
                        remaining=secret.rate_limit.remaining,
                        resets=secret.rate_limit.reset,
                    ),
                )
            return secret
        return GsecretFailure(reason="No executor available", code=500)

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by key with rate limiting"""
        delay = BufferDelay(timeout=self.config.timeout)
        self.stage_client.key_delay(key, delay)
        executor = next.next()
        if executor:
            secret = executor.get_secret_key(key, token, next)
            if isinstance(secret, Secret) and secret.rate_limit is not None:
                self.stage_client.log_key_rate_limit(
                    key,
                    secret.rate_limit.api_relation,
                    BufferRateLimits(
                        remaining=secret.rate_limit.remaining,
                        resets=secret.rate_limit.reset,
                    ),
                )
            return secret
        return GsecretFailure(reason="No executor available", code=500)

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """Write a secret with rate limiting"""

        executor = next.next()
        if executor:
            return executor.write_secret(secret, token, next)
        return GsecretFailure(reason="No executor available", code=500)

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications - pass through without rate limiting"""
        # Secret updates from downstream should not be rate limited
        for secret in secrets:
            if secret.api_id_relation:
                self.stage_client.register_id_api_map(
                    secret.key_id, secret.api_id_relation
                )
            if secret.api_key_relation:
                self.stage_client.register_key_api_map(
                    secret.key, secret.api_key_relation
                )

        executor = next.next()
        if executor:
            return executor.secret_updated(secrets, token_hash, priority, next)


class RateLimiterGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for rate limiter stage"""

    def __init__(self):
        self.controller = BufferController()

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        rate_limiter_config = RateLimiterConfig(**config)
        stage_controller = BufferedStageClient(
            self.controller, default_delay=rate_limiter_config.default_delay
        )
        return RateLimiterGSecretExecutor(
            stage_client=stage_controller, config=rate_limiter_config
        )


# Register the stage builder with the gsecret interface
builder = RateLimiterGSecretStageBuilder()
gsecret_interface.register_stage("rate_limiter", builder)
