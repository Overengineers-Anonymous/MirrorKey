from core.api import ApiDescriptor, route_map, RouteMap
from core.plugins import plugin_loader
from pydantic import BaseModel



plugin_loader.register_plugin("secrets")

class SecretRequestCtx(BaseModel):
    param1: str
    param2: int

class SecretParam(BaseModel):
    id: str



class SecretApiDescriptor(ApiDescriptor):
    def __init__(self, route_map: "RouteMap[SecretApiDescriptor]"):
        self.route_map = route_map

    def by_id(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        child = self.route_map.cast_to_child(f".{url_param.id}")
        child.by_id(request_ctx, url_param)

    def create(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        child = self.route_map.cast_to_child(f".{url_param.id}")
        child.create(request_ctx, url_param)



secret_route_map = route_map.with_root(".secrets", SecretApiDescriptor)

api_descriptor = SecretApiDescriptor(secret_route_map)

secret_route_map.handler(".id", api_descriptor.by_id)
secret_route_map.handler(".create", api_descriptor.create)
