from core.api.manager import APIPluginManager, plugin_manager
from core.chain.controller import Chain
from core.config.loader import LoadedConfig
from core.importer import Importer, importer
from fastapi import FastAPI


class ApiBuilder:
    def __init__(self, plugins_src: APIPluginManager, importer: Importer):
        self.plugins_src = plugins_src
        self.importer = importer

    def load_stages(self, config: LoadedConfig) -> None:
        for api_name in config.apis():
            self.importer.import_api(api_name)
            api = self.plugins_src.get_api(api_name)
            if not api:
                raise ValueError(f"API '{api_name}' not found.")
            for chain_name in config.chains(api_name):
                chain = Chain(chain_name, api.stage_class)

                for stage_name in config.stages(api_name, chain_name):
                    self.importer.import_stage_plugin(api.interface.name, stage_name)
                    stage_config = config.stage_config(api_name, chain_name, stage_name)
                    if stage_name not in api.chain_stages:
                        raise ValueError(
                            f"Stage '{stage_name}' not registered in API '{api_name}'."
                        )
                    stage_builder = api.chain_stages[stage_name]
                    stage_instance = stage_builder.build(stage_config, chain)
                    chain.add_stage(stage_instance)
                api.chain_controller.add_chain(chain)

    def build(self, api: FastAPI, config: LoadedConfig) -> FastAPI:
        self.load_stages(config)
        for plugin_name, plugin in self.plugins_src.api_plugins.items():
            api.include_router(plugin.router, prefix=f"/{plugin_name}")
        return api


api_builder = ApiBuilder(plugins_src=plugin_manager, importer=importer)
