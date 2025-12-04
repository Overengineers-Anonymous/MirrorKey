import datetime
import time
from threading import Lock, Thread
from typing import Protocol

from bws_sdk import BWSecretClient, Region
from bws_sdk.bws_types import BitwardenSync
from interfaces.gsecret import RateLimit, Secret, Token, TokenID, UpdatedSecret


class SyncCallback(Protocol):
    def __call__(self, token_hash: TokenID, secrets: list[UpdatedSecret]) -> None: ...


class ApiRateLimiter:
    def __init__(self, min_delay: float = 0.0):
        self.max: int = 0
        self.window: int = 0
        self.remaining: int = 0
        self.min_delay = min_delay
        self.reset = datetime.datetime.now(tz=datetime.timezone.utc)

    def delay(self) -> None:
        """delay needed to avoid rate limiting."""
        if self.max == 0:
            return
        time.sleep(max(self.min_delay, (self.window / (self.max) * 2)))  # 50% buffer

    def _rt_window_seconds(self, window: str) -> int:
        match (int(window[:-1]), window[-1]):
            case (x, "s"):
                return x * 1
            case (x, "m"):
                return x * 60
            case (x, "h"):
                return x * 3600
            case _:
                return 0

    def trigger(self, window: str, remaining: int):
        if remaining >= self.remaining:
            self.max = remaining + 1
            self.window = self._rt_window_seconds(window)
            now = datetime.datetime.now(tz=datetime.timezone.utc)
            self.reset = now + datetime.timedelta(seconds=self.window)
        self.remaining = remaining


class BwsClient:
    def __init__(self, client: BWSecretClient, token_hash: TokenID):
        self.token_hash = token_hash
        self.client = client
        self.sync_callbacks: list[SyncCallback] = []
        self.last_sync = datetime.datetime.now(tz=datetime.timezone.utc)
        self.sync_delay = 10
        self.sync_thread = Thread(target=self._sync_loop, daemon=True)
        self.sync_all: list[SyncCallback] = []
        self.sync_lock = Lock()
        self.kv_lock = Lock()
        self.kv_translater: dict[str, str] = {}

        self.sync_rate_limiter = ApiRateLimiter(2)
        self.id_rate_limiter: dict[str, ApiRateLimiter] = {}

    def populate_kv_cache(self):
        """Populate the key-value cache from existing secrets."""
        self._sync(datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))
        self.sync_thread.start()

    @classmethod
    def from_token(cls, region: Region, access_token: Token) -> "BwsClient":
        token_hash = access_token.from_token_id()
        client = BWSecretClient(
            region=region,
            access_token=access_token.token,
        )

        bwclient = cls(client=client, token_hash=token_hash)
        bwclient.populate_kv_cache()
        return bwclient

    def ensure_callback(self, callback: SyncCallback):
        if callback not in self.sync_callbacks:
            self.sync_callbacks.append(callback)
            self.sync_all.append(callback)

    def get_by_id(self, key_id: str) -> Secret | None:
        bw_secret = self.client.get_by_id(key_id)
        if not bw_secret:
            return None
        if bw_secret.id not in self.id_rate_limiter:
            self.id_rate_limiter[bw_secret.id] = ApiRateLimiter()
        rate_limiter = self.id_rate_limiter[bw_secret.id]
        rate_limiter.trigger(
            window=bw_secret.ratelimit.limit,
            remaining=bw_secret.ratelimit.remaining,
        )
        return Secret(
            key_id=bw_secret.id,
            key=bw_secret.key,
            secret=bw_secret.value,
            rate_limit=RateLimit(
                limit=rate_limiter.max,
                remaining=rate_limiter.remaining,
                reset=rate_limiter.reset,
                api_relation=f"bws_read:id:{bw_secret.id}",
            ),
        )

    def get_by_key(self, key: str) -> Secret | None:
        secret_id = self.kv_translater.get(key)
        if not secret_id:
            return None
        return self.get_by_id(secret_id)

    def _convert_secrets(self, secrets: BitwardenSync) -> list[UpdatedSecret]:
        native_secrets: list[UpdatedSecret] = []
        if secrets.secrets is None:
            return native_secrets
        for secret in secrets.secrets:
            native_secrets.append(
                UpdatedSecret(
                    key_id=secret.id,
                    key=secret.key,
                    secret=secret.value,
                    api_id_relation=f"bws_read:id:{secret.id}",
                    api_key_relation=f"bws_read:key:{secret.id}",
                )
            )
        return native_secrets

    def _sync(self, last_sync: datetime.datetime) -> BitwardenSync | None:
        secrets = self.client.sync(last_sync)
        self.sync_rate_limiter.trigger(
            window=secrets.ratelimit.limit,
            remaining=secrets.ratelimit.remaining,
        )
        if secrets.secrets is None:
            return None

        new_secret_ids = {secret.id for secret in secrets.secrets}
        old_secret_ids = set(self.id_rate_limiter.keys())
        stale_secret_ids = old_secret_ids - new_secret_ids
        secret_ids = new_secret_ids - old_secret_ids
        for stale_id in stale_secret_ids:
            del self.id_rate_limiter[stale_id]
        for secret_id in secret_ids:
            self.id_rate_limiter[secret_id] = ApiRateLimiter()

        with self.kv_lock:
            self.kv_translater.clear()
            for secret in secrets.secrets:
                self.kv_translater[secret.key] = secret.id

        return secrets

    def _sync_loop(self):
        self.sync_rate_limiter.delay()
        while True:
            with self.sync_lock:
                new_callbacks = self.sync_all.copy()
                self.sync_all = []
            if new_callbacks:
                secrets = self._sync(
                    datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc)
                )
                if secrets is None:
                    continue  # Skip if no sync data
                for callback in new_callbacks:
                    callback(self.token_hash, self._convert_secrets(secrets))
                self.sync_rate_limiter.delay()

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            secrets = self._sync(self.last_sync)
            self.last_sync = now
            if secrets is None:
                continue  # Skip if no sync data
            for callback in self.sync_callbacks:
                callback(self.token_hash, self._convert_secrets(secrets))
            self.sync_rate_limiter.delay()


class BwsClientController:
    """Manages BWS client instances with caching based on tokens"""

    def __init__(self):
        self._client_cache: dict[str, BwsClient] = {}
        self._region_map: dict[str, str] = {}

    def _get_region_key(self, region: Region) -> str:
        return f"{region.api_url}|{region.identity_url}"

    def get_client(
        self, token: Token, region: Region, sync_callback: SyncCallback
    ) -> BwsClient:
        """
        Get a BWS client for the given token.
        Returns cached client if available, otherwise creates a new one.
        """
        token_hash = token.from_token_id().token_id

        if token_hash not in self._client_cache:
            self._client_cache[token_hash] = BwsClient.from_token(
                region=region,
                access_token=token,
            )
            self._region_map[token_hash] = self._get_region_key(region)

        client = self._client_cache[token_hash]

        if self._region_map[token_hash] != self._get_region_key(region):
            raise ValueError("Region mismatch for cached client")

        client.ensure_callback(sync_callback)

        return client
