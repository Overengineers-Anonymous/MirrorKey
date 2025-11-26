import datetime
import hashlib
from typing import Any, Protocol

from core.chain.chain import ChainStage
from core.chain.controller import ForwardChainExecutor, ReverseChainExecutor
from core.interface.main import Interface
from pydantic import BaseModel


class GsecretFailure(BaseModel):
    reason: str
    code: int

class RateLimit(BaseModel):
    limit: int
    remaining: int
    reset: datetime.datetime
    api_relation: str

class Secret(BaseModel):
    key_id: str
    key: str
    secret: Any | str
    rate_limit: RateLimit | None = None

class UpdatedSecret(Secret):
    api_id_relation: str | None = None
    api_key_relation: str | None = None

class WriteSecret(BaseModel):
    key: str
    secret: Any | str

class TokenID(BaseModel):
    token_id: str

    def __eq__(self, value: object) -> bool:
        if not isinstance(value, TokenID):
            return False
        return self.token_id == value.token_id

class Token(BaseModel):
    token: str

    def from_token_id(self) -> TokenID:
        token_hash = hashlib.sha256(self.token.encode()).hexdigest()
        return TokenID(token_id=token_hash)

class GSecretExecutor(ChainStage, Protocol):
    def get_secret_id(
        self, key_id: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure: ...

    def get_secret_key(
        self, key: str, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure: ...

    def write_secret(
        self, secret: WriteSecret, token: Token, next: ForwardChainExecutor["GSecretExecutor"]
    ) -> Secret | GsecretFailure: ...

    # reverse chain methods

    def secret_updated(
        self, secrets: list[UpdatedSecret], token_hash: TokenID, priority: int, next: ReverseChainExecutor["GSecretExecutor"]
    ): ...


gsecret_interface = Interface("gsecret", GSecretExecutor)
