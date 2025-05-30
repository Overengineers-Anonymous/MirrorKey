from pydantic import BaseModel
from core.api import RouteMap, ApiDescriptor
from core.config import config
from plugins.secrets.main import SecretRequestCtx, SecretParam, secret_route_map, SecretApiDescriptor
from core.plugins import plugin_loader


plugin_loader.register_plugin("bws_cache", ["secrets"])


class BWSCacheConfig(BaseModel):
    org_id: str
    token: str


bws_config = config.api_descriptor("bws_cache", BWSCacheConfig, True)
print(bws_config.org_id)


class BWSApiDescriptor(SecretApiDescriptor):
    def __init__(self, route_map: "RouteMap[BWSApiDescriptor]"):
        self.route_map = route_map

    def by_id(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        # bws tings
        ...

    def create(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        # bws_tings
        ...


bws_route_map = secret_route_map.with_root(".bws", BWSApiDescriptor)

api_descriptor = BWSApiDescriptor(bws_route_map)


bws_route_map.handler(".id.<id>.secret.<secret>", api_descriptor.by_id)
bws_route_map.handler(".create", api_descriptor.create)
