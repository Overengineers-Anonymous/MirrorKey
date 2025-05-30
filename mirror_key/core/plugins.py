from .config import ConfigParser, config
import importlib
import logging


logger = logging.getLogger(__name__)

class UnloadedPluginError(Exception):
    pass



class PluginLoader:
    def __init__(self, config: ConfigParser):
        self.config = config
        self.loaded_plugins: list[str] = []

    def load(self):
        if self.config.config and (api_descriptors := self.config.config.api_descriptors):
            for plugin in api_descriptors:
                if plugin in self.loaded_plugins:
                    continue
                try:
                    importlib.import_module(f"plugins.{plugin}")
                except Exception as e:
                    try:
                        importlib.import_module(f"custom_plugins.{plugin}")
                    except Exception as e:
                        print(f"Failed to load plugin {plugin}: {e}")
        else:
            logger.warning("No Plugins to load")

    def register_plugin(self, plugin_name: str, dependancys: list[str] = []):
        self.ensure_dependencies(dependancys)
        if plugin_name in self.loaded_plugins:
            raise Exception(f"Plugin {plugin_name} already loaded")
        self.loaded_plugins.append(plugin_name)

    def ensure_dependencies(self, plugins: list[str]):
        for plugin in plugins:
            if plugin not in self.loaded_plugins:
                raise UnloadedPluginError(f"Plugin {plugin} not loaded")

plugin_loader = PluginLoader(config)
