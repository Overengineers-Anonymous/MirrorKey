from importlib import import_module

from core.api.manager import APIPluginManager, plugin_manager


class Importer:
    def __init__(self, plugin_manager: APIPluginManager):
        self.imported_modules = {}
        self.plugin_manager = plugin_manager

    def import_module(self, module_path: str):
        if module_path in self.imported_modules:
            return self.imported_modules[module_path]

        module = import_module(module_path)
        self.imported_modules[module_path] = module

    def import_api(self, api_name: str):
        self.import_module(f"apis.{api_name}")

        if api_name not in self.plugin_manager.api_plugins:
            raise ImportError(
                f"API '{api_name}' failed to register with plugin manager after import. Path was 'apis.{api_name}'."
            )

    def import_stage_plugin(self, api_name: str, stage_name: str):
        module_path = f"stages.{api_name}.{stage_name}"
        api = self.plugin_manager.get_api(api_name)
        if not api:
            raise ValueError(f"API '{api_name}' not found.")

        self.import_module(module_path)
        if stage_name not in api.chain_stages:
            raise ImportError(
                f"Stage '{stage_name}' for API '{api_name}' failed to register with API plugin after import. "
                f"Path was '{module_path}'."
            )


importer = Importer(plugin_manager=plugin_manager)
