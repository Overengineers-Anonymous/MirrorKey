import datetime
from threading import Lock, Thread
import time
from typing import Protocol

from bws_sdk import BWSecretClient, BitwardenSecret, Region
from interfaces.gsecret import Secret, Token, TokenID


class SyncCallback(Protocol):
    def __call__(self, token_hash: TokenID, secrets: list[Secret]) -> None: ...


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

    def populate_kv_cache(self):
        """Populate the key-value cache from existing secrets."""
        secrets = self.client.sync(datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))
        with self.kv_lock:
            for secret in secrets:
                self.kv_translater[secret.key] = secret.id
        self.sync_thread.start()

    @classmethod
    def from_token(cls, region: Region, access_token: Token) -> "BwsClient":
        token_hash = access_token.from_token_id()
        client = BWSecretClient(
            region=region,
            access_token=access_token.token,
        )
        return cls(client=client, token_hash=token_hash)

    def ensure_callback(self, callback: SyncCallback):
        if callback not in self.sync_callbacks:
            self.sync_callbacks.append(callback)
            self.sync_all.append(callback)

    def get_by_id(self, key_id: str) -> Secret:
        bw_secret = self.client.get_by_id(key_id)
        return Secret(
            key_id=bw_secret.id,
            key=bw_secret.key,
            secret=bw_secret.value,
        )

    def get_by_key(self, key: str) -> Secret | None:
        secret_id = self.kv_translater.get(key)
        if not secret_id:
            return None
        return self.get_by_id(secret_id)

    def _convert_secrets(self, secrets: list[BitwardenSecret]) -> list[Secret]:
        native_secrets: list[Secret] = []
        for secret in secrets:
            native_secrets.append(
                Secret(
                    key_id=secret.id,
                    key=secret.key,
                    secret=secret.value,
                )
            )
        return native_secrets

    def _sync(self, last_sync: datetime.datetime) -> list[BitwardenSecret]:
        secrets = self.client.sync(last_sync)
        with self.kv_lock:
            for secret in secrets:
                self.kv_translater[secret.key] = secret.id
        return secrets

    def _sync_loop(self):
        while True:
            with self.sync_lock:
                new_callbacks = self.sync_all.copy()
                self.sync_all = []
            for callback in new_callbacks:
                secrets = self._sync(datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))
                callback(self.token_hash, self._convert_secrets(secrets))
                time.sleep(self.sync_delay)

            now = datetime.datetime.now(tz=datetime.timezone.utc)
            secrets = self._sync(self.last_sync)
            self.last_sync = now
            for callback in self.sync_callbacks:
                callback(self.token_hash, self._convert_secrets(secrets))
            time.sleep(self.sync_delay)


class BwsClientController:
    """Manages BWS client instances with caching based on tokens"""

    def __init__(self):
        self._client_cache: dict[str, BwsClient] = {}
        self._region_map: dict[str, str] = {}

    def _get_region_key(self, region: Region) -> str:
        return f"{region.api_url}|{region.identity_url}"

    def get_client(self, token: Token, region: Region, sync_callback: SyncCallback) -> BwsClient:
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
            self._client_cache[token_hash].populate_kv_cache()
            self._region_map[token_hash] = self._get_region_key(region)

        client = self._client_cache[token_hash]

        if self._region_map[token_hash] != self._get_region_key(region):
            raise ValueError("Region mismatch for cached client")

        client.ensure_callback(sync_callback)

        return client
