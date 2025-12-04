import datetime
import time

from bws_sdk import BWSecretClient, Region
from interfaces.gsecret import Secret, Token, WriteSecret


class ApiRateLimiter:
    def __init__(self):
        self.max: int = 0
        self.window: int = 0
        self.remaining: int = 0
        self.reset = datetime.datetime.now(tz=datetime.timezone.utc)

    def delay(self) -> None:
        """delay needed to avoid rate limiting."""
        if self.max == 0:
            return
        time.sleep(self.window / (self.max * 0.8))  # 80% buffer

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
    def __init__(self, client: BWSecretClient):
        self.client = client
        self.sync_rate_limiter = ApiRateLimiter()
        self.id_rate_limiter: ApiRateLimiter = ApiRateLimiter()

    @classmethod
    def from_token(cls, region: Region, access_token: Token) -> "BwsClient":
        client = BWSecretClient(
            region=region,
            access_token=access_token.token,
        )

        bwclient = cls(client=client)
        return bwclient

    def write_secret(self, secret: WriteSecret, project_ids: list[str]) -> Secret:
        bws_secret = self.client.create(
            key=secret.key, value=secret.secret, note="", project_ids=project_ids
        )
        return Secret(
            key_id=bws_secret.id,
            key=bws_secret.key,
            secret=bws_secret.value,
        )


class BwsClientController:
    """Manages BWS client instances with caching based on tokens"""

    def __init__(self):
        self._client_cache: dict[str, BwsClient] = {}
        self._region_map: dict[str, str] = {}

    def _get_region_key(self, region: Region) -> str:
        return f"{region.api_url}|{region.identity_url}"

    def get_client(self, token: Token, region: Region) -> BwsClient:
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

        return client
