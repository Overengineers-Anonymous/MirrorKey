from pathlib import Path
from typing import Any

import yaml

from .schema import RootConfig


class LoadedConfig:
    ROOT_CONFIG_CLS = RootConfig

    def __init__(
        self,
        stage_cfg_map: dict[str, dict[str, dict[str, Any]]],
        chain_stage_map: dict[str, dict[str, list[str]]],
    ) -> None:
        self.stage_cfg_map = stage_cfg_map
        self.chain_stage_map = chain_stage_map

    def apis(self) -> list[str]:
        return list(self.chain_stage_map.keys())

    def chains(self, api: str) -> list[str]:
        return list(self.chain_stage_map.get(api, {}).keys())

    def stages(self, api: str, chain: str) -> list[str]:
        return self.chain_stage_map.get(api, {}).get(chain, [])

    def stage_config(self, api: str, chain: str, stage: str) -> dict[str, Any] | None:
        return self.stage_cfg_map.get(api, {}).get(chain, {}).get(stage)

    @classmethod
    def from_yaml(cls, file_path: Path) -> "LoadedConfig":
        with open(file_path, "r") as file:
            data = yaml.safe_load(file)
        root_cfg = cls.ROOT_CONFIG_CLS(**data)
        stage_cfg_map = {}
        chain_stage_map = {}
        for chain_cfg in root_cfg.chains:
            if chain_cfg.api not in chain_stage_map:
                chain_stage_map[chain_cfg.api] = {}
            if chain_cfg.name not in chain_stage_map[chain_cfg.api]:
                chain_stage_map[chain_cfg.api][chain_cfg.name] = []

            if chain_cfg.api not in stage_cfg_map:
                stage_cfg_map[chain_cfg.api] = {}
            if chain_cfg.name not in stage_cfg_map[chain_cfg.api]:
                stage_cfg_map[chain_cfg.api][chain_cfg.name] = {}

            for step in chain_cfg.steps:
                chain_stage_map[chain_cfg.api][chain_cfg.name].append(step.name)
                # Build stage config map
                stage_cfg_map[chain_cfg.api][chain_cfg.name][step.name] = step.config

        return cls(stage_cfg_map=stage_cfg_map, chain_stage_map=chain_stage_map)
