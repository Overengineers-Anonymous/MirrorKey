from core.api import RouteMap, ApiDescriptor
from plugins.secrets.main import SecretRequestCtx, SecretParam, secret_route_map, SecretApiDescriptor
from plugins.bws_cache.main import api_descriptor
from core.plugins import plugin_loader

plugin_loader.register_plugin("bws_cache_generic", ["bws_cache"])

class BWSApiDescriptor(SecretApiDescriptor):
    def __init__(self, route_map: "RouteMap[BWSApiDescriptor]"):
        self.route_map = route_map

    def by_id(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        api_descriptor.by_id()
        ...

    def create(self, request_ctx: SecretRequestCtx, url_param: SecretParam):
        # bws_tings
        ...



bws_route_map = secret_route_map.with_root(".bws", BWSApiDescriptor)

api_descriptor_bws = BWSApiDescriptor(bws_route_map)

bws_route_map.handler(".id", api_descriptor.by_id)
bws_route_map.handler(".create", api_descriptor.create)

