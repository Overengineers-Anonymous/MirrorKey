from typing import Any
from pydantic import BaseModel


class Plugin(BaseModel):
    config: Any


class Config(BaseModel):
    plugins: dict[str, Plugin | None] | None = None
