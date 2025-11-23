from plugins.gsecret import SecretClient
from plugins.gsecret import SecretData
from .bws_client.client import BWSClient
from bws_sdk import BitwardenSecret, BitwardenSecret


class BwsSecretClient(SecretClient):
    """
    BwsSecretClient extends the SecretClient protocol for BWS specific secret operations.
    It inherits all methods from SecretClient and can be used to implement BWS specific logic.
    """
    def __init__(self, client: BWSClient):
        self.client = client
        self.key_cache: dict[str, str] = {}
        self.secret_cache: dict[str, BitwardenSecret] = {}
        self._preload_cache()

    def _load_secrets(self, secrets: list[BitwardenSecret]) -> None:
        """
        Load all secrets from the BWS client and populate the caches.
        This method should be called to ensure that the client has the latest secrets.
        """
        secrets = self.client.list_secrets()
        for secret in secrets:
            self.secret_cache[secret.id] = secret
            self.key_cache[secret.key] = secret.id

    def _preload_cache(self) -> None:
        self._load_secrets(self.client.list_secrets())

    def get_secret_by_key(self, secret_key: str) -> SecretData | None:
        secret_id = self.key_cache.get(secret_key)
        if secret_id is not None:
            return self.get_secret_by_id(secret_id)
        return None

    def get_secret_by_id(self, secret_id: str) -> SecretData | None:
        secret = self.secret_cache.get(secret_id)
        if secret is None:
            secrets = self.client.list_secrets()
            for s in secrets:
                if s.id == secret_id:
                    secret = s
                    self.secret_cache[secret_id] = secret
                    self.key_cache[s.key] = secret_id
                    break
        if secret is not None:
            return SecretData(key=secret.key, id=str(secret.id), value=secret.value)
        return None

    def write_secret_id(self, value: str) -> SecretData:
        ...

    def write_secret_key(self, key: str, value: str) -> SecretData:
        ...
