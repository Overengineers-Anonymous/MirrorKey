from .plugin import APIPlugin


class APIPluginManager:
    def __init__(self):
        self.api_plugins: dict[str, APIPlugin] = {}

    def register_plugin(self, plugin: APIPlugin) -> APIPlugin:
        if plugin.name in self.api_plugins:
            raise ValueError(f"API with name '{plugin.name}' is already registered.")
        self.api_plugins[plugin.name] = plugin
        return plugin

    def get_api(self, name: str) -> APIPlugin | None:
        return self.api_plugins.get(name)


plugin_manager = APIPluginManager()
