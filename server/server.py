from core.plugins import plugin_loader, config
from shatter_api import route_map, WsgiDispatcher


config.load_config("mirrorkey.yml")
plugin_loader.load()

api = WsgiDispatcher(route_map)




