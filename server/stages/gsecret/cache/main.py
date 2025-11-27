from multiprocessing.spawn import old_main_modules
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
from pydantic import BaseModel, Field

from .cache_controller import CacheController


class CacheConfig(BaseModel):
    """Configuration for Cache stage"""

    ttl_seconds: int = Field(
        default=300,
        description="Time-to-live for cached secrets in seconds. 0 disables expiration.",
    )
    invalidate_on_upstream_error: bool = Field(
        default=True,
        description="Whether to invalidate cache on upstream errors",
    )


class CacheGSecretExecutor(GSecretExecutor):
    """Cache executor for gsecret interface"""

    def __init__(
        self,
        config: CacheConfig,
        controller: CacheController,
        chain: Chain[GSecretExecutor],
    ):
        self.config = config
        self.chain = chain
        self.cache_controller = controller

    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure:
        """Retrieve a secret by its ID, using cache if available"""
        token_hash = token.from_token_id()

        # Try to get from cache if caching is enabled

        token_cache = self.cache_controller.get_token_cache(token_hash)
        cached_secret = token_cache.get_by_id(key_id, self.config.ttl_seconds)
        if cached_secret:
            return cached_secret

        # Cache miss or caching disabled, fetch from next executor
        executor = next.next()
        if executor:
            result = executor.get_secret_id(key_id, token, next)

            # Cache the result if it's a successful secret retrieval
            if isinstance(result, Secret):
                token_cache.update_by_key(result, result.key)
            elif result.code == 404:
                token_cache.invalidate_by_id(key_id)
            elif self.config.invalidate_on_upstream_error:
                token_cache.invalidate_by_id(key_id)
            return result

        return GsecretFailure(reason="Secret not found", code=404)

    def get_secret_key(self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]) -> Secret | GsecretFailure:
        """Retrieve a secret by its key, using cache if available"""
        token_hash = token.from_token_id()

        # Try to get from cache if caching is enabled
        token_cache = self.cache_controller.get_token_cache(token_hash)
        cached_secret = token_cache.get_by_key(key, self.config.ttl_seconds)
        if cached_secret:
            return cached_secret

        # Cache miss or caching disabled, fetch from next executor
        executor = next.next()
        if executor:
            result = executor.get_secret_key(key, token, next)

            # Cache the result if it's a successful secret retrieval
            if isinstance(result, Secret):
                token_cache.update_by_key(result, result.key)
            elif result.code == 404:
                token_cache.invalidate_by_key(key)
            elif self.config.invalidate_on_upstream_error:
                token_cache.invalidate_by_key(key)

            return result

        return GsecretFailure(reason="Secret not found", code=404)

    def write_secret(
        self,
        secret: WriteSecret,
        token: Token,
        next: ForwardChainExecutor["GSecretExecutor"],
    ) -> Secret | GsecretFailure:
        """Write a secret, optionally invalidating or updating cache"""
        token_hash = token.from_token_id()


        # Pass to next executor
        executor = next.next()
        if executor:
            result = executor.write_secret(secret, token, next)

            # Cache the result if it's a successful write and caching is enabled
            if isinstance(result, Secret):
                token_cache = self.cache_controller.get_token_cache(token_hash)
                token_cache.update_by_key(result, result.key)
                token_cache.update_by_id(result, result.key_id)
            return result

        return GsecretFailure(reason="Write operations not supported", code=501)

    def secret_updated(
        self,
        secrets: list[UpdatedSecret],
        token_hash: TokenID,
        priority: int,
        next: ReverseChainExecutor["GSecretExecutor"],
    ):
        """Handle secret update notifications from reverse chain"""
        # Update cache with the latest secret values
        token_cache = self.cache_controller.get_token_cache(token_hash)
        ids = set()
        keys = set()
        for secret in secrets:
            ids.add(secret.key_id)
            keys.add(secret.key)
            token_cache.update_by_id(secret, secret.key_id)
            token_cache.update_by_key(secret, secret.key)
        stale_ids = token_cache.ids - ids
        stale_keys = token_cache.keys - keys
        for stale_id in stale_ids:
            token_cache.invalidate_by_id(stale_id)
        for stale_key in stale_keys:
            token_cache.invalidate_by_key(stale_key)


        # Pass to next executor in reverse chain
        executor = next.next()
        if executor:
            return executor.secret_updated(secrets, token_hash, priority, next)


class CacheGSecretStageBuilder(ChainStageBuilder[GSecretExecutor]):
    """Builder for Cache stage"""

    def build(self, config: Any, chain: Chain[GSecretExecutor]) -> GSecretExecutor:
        if config is None:
            config = {}
        cache_controller = CacheController()
        parsed_config = CacheConfig.model_validate(config)
        return CacheGSecretExecutor(parsed_config, cache_controller, chain)


# Register the stage builder with the gsecret interface
builder = CacheGSecretStageBuilder()
gsecret_interface.register_stage("cache", builder)
