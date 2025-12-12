from pathlib import Path

from core import api_builder
from core.config.loader import LoadedConfig
from fastapi import FastAPI

config = LoadedConfig.from_yaml(Path("dyrne.yml"))


api = api_builder.build(FastAPI(), config)


@api.get("/healthcheck")
def healthcheck():
    return {"status": "healthy"}
