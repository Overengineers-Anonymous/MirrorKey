from typing import Any

from pydantic import BaseModel


class ChainStepConfig(BaseModel):
    name: str
    config: dict[str, Any] | None = None


class ChainConfig(BaseModel):
    api: str
    name: str
    steps: list[ChainStepConfig]


class RootConfig(BaseModel):
    chains: list[ChainConfig]
