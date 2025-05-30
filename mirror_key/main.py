from core.api import route_map
from core.plugins import plugin_loader
from core.config import config

config.load_config("mirrorkey.yml")
plugin_loader.load()
print(plugin_loader.loaded_plugins)

# app = route_map.make_app()
