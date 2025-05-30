from typing import Any
from pydantic import BaseModel

class ApiDescriptor(BaseModel):
    config: Any

class Config(BaseModel):
    api_descriptors: dict[str, ApiDescriptor | None] | None
