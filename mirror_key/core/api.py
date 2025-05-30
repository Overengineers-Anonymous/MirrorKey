from enum import Enum
from fastapi import FastAPI, APIRouter
from typing import Callable, Protocol

from pydantic import BaseModel


class RouteMap[T: "ApiDescriptor"]:
    def __init__(self, root: str, api_descriptor: type[T]):
        self.root = root

    def handler(self, path: str, handler: Callable): ...

    def with_root[TD: "ApiDescriptor"](self, root: str, descriptor: "type[TD]") -> "RouteMap[TD]":
        return RouteMap(self.root+root, descriptor)

    def cast_to_child(self, path: str) -> "T": ...

    def validate(self) -> None: ...

    def make_app(self) -> FastAPI:
        app = FastAPI()
        return app

class ApiDescriptor:
    def __init__(self, route_map: "RouteMap[ApiDescriptor]"): ...



class Methods(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"



route_map = RouteMap(".", ApiDescriptor)
