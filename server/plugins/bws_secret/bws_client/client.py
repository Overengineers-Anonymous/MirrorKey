import logging
import datetime
from threading import Lock
import hashlib
from bws_sdk import BWSecretClient, Region, BitwardenSecret

logger = logging.getLogger("bwssecret.client")


def generate_hash(value: str, region: Region) -> str:
    value = f"{value}{region.api_url}{region.identity_url}"
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class BWSClient:
    def __init__(self, bws_token: str, region: Region):
        self.region = region
        self.bws_token = bws_token
        self.client_lock = Lock()
        self.last_sync = datetime.datetime.now(tz=datetime.timezone.utc) - datetime.timedelta(seconds=60)
        self.bws_client = self.make_client(bws_token, region)

    def make_client(self, bws_token: str, region: Region) -> BWSecretClient:
        return BWSecretClient(region, bws_token, f"/dev/shm/token_{self.client_hash}")

    def list_secrets(self) -> list[BitwardenSecret]:
        with self.client_lock:
            logger.debug("Listing secrets")
            secrets = self.bws_client.sync(datetime.datetime.fromtimestamp(0, tz=datetime.timezone.utc))
        if not secrets:
            logger.debug("No secrets found")
        else:
            logger.debug("Found %s secrets", len(secrets))
        return secrets

    def get_updated_secrets(self) -> list[BitwardenSecret]:
        update_secrets: list[BitwardenSecret] = []
        latest_sync = datetime.datetime.now(tz=datetime.timezone.utc)
        with self.client_lock:
            logger.debug("Getting updated secrets")
            secrets = self.bws_client.sync(self.last_sync)
        logger.debug("Got updated secrets")
        self.last_sync = latest_sync
        if secrets:
            for secret in secrets:
                logger.debug("Got updated secret %s", secret.id)
                update_secrets.append(secret)
        else:
            logger.debug("No secrets updated")
        return update_secrets

    @property
    def client_hash(self):
        return generate_hash(self.bws_token, self.region)
