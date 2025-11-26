from pathlib import Path

import pytest

from core.config.loader import LoadedConfig
from core.config.schema import RootConfig


class TestLoadedConfig:
    """Test cases for the LoadedConfig class."""

    @pytest.fixture
    def stage_cfg_map(self):
        """Create a sample stage configuration map."""
        return {
            "api1": {
                "chain1": {
                    "stage1": {"key1": "value1"},
                    "stage2": {"key2": "value2"},
                },
                "chain2": {
                    "stage3": {"key3": "value3"},
                },
            },
            "api2": {
                "chain3": {
                    "stage4": {"key4": "value4"},
                },
            },
        }

    @pytest.fixture
    def chain_stage_map(self):
        """Create a sample chain-stage map."""
        return {
            "api1": {
                "chain1": ["stage1", "stage2"],
                "chain2": ["stage3"],
            },
            "api2": {
                "chain3": ["stage4"],
            },
        }

    @pytest.fixture
    def loaded_config(self, stage_cfg_map, chain_stage_map):
        """Create a LoadedConfig instance."""
        return LoadedConfig(
            stage_cfg_map=stage_cfg_map, chain_stage_map=chain_stage_map
        )

    def test_init(self, stage_cfg_map, chain_stage_map):
        """Test LoadedConfig initialization."""
        config = LoadedConfig(
            stage_cfg_map=stage_cfg_map, chain_stage_map=chain_stage_map
        )

        assert config.stage_cfg_map == stage_cfg_map
        assert config.chain_stage_map == chain_stage_map

    def test_apis(self, loaded_config):
        """Test apis() method returns list of API names."""
        apis = loaded_config.apis()

        assert isinstance(apis, list)
        assert set(apis) == {"api1", "api2"}

    def test_chains(self, loaded_config):
        """Test chains() method returns chains for a specific API."""
        chains_api1 = loaded_config.chains("api1")
        chains_api2 = loaded_config.chains("api2")

        assert isinstance(chains_api1, list)
        assert set(chains_api1) == {"chain1", "chain2"}
        assert chains_api2 == ["chain3"]

    def test_chains_nonexistent_api(self, loaded_config):
        """Test chains() method with non-existent API returns empty list."""
        chains = loaded_config.chains("nonexistent_api")

        assert chains == []

    def test_stages(self, loaded_config):
        """Test stages() method returns stages for a specific chain."""
        stages = loaded_config.stages("api1", "chain1")

        assert isinstance(stages, list)
        assert stages == ["stage1", "stage2"]

    def test_stages_nonexistent_chain(self, loaded_config):
        """Test stages() method with non-existent chain returns empty list."""
        stages = loaded_config.stages("api1", "nonexistent_chain")

        assert stages == []

    def test_stage_config(self, loaded_config):
        """Test stage_config() method returns stage configuration."""
        config = loaded_config.stage_config("api1", "chain1", "stage1")

        assert config == {"key1": "value1"}

    def test_stage_config_multiple_stages(self, loaded_config):
        """Test stage_config() for multiple stages."""
        config1 = loaded_config.stage_config("api1", "chain1", "stage1")
        config2 = loaded_config.stage_config("api1", "chain1", "stage2")
        config3 = loaded_config.stage_config("api1", "chain2", "stage3")

        assert config1 == {"key1": "value1"}
        assert config2 == {"key2": "value2"}
        assert config3 == {"key3": "value3"}

    def test_stage_config_nonexistent_returns_none(self, loaded_config):
        """Test stage_config() with non-existent stage returns None."""
        config = loaded_config.stage_config("api1", "chain1", "nonexistent_stage")

        assert config is None

    def test_from_yaml_success(self, tmp_path):
        """Test from_yaml() successfully loads configuration from YAML file."""
        yaml_content = """
chains:
  - api: test_api
    name: test_chain
    steps:
      - name: step1
        config:
          param1: value1
          param2: value2
      - name: step2
        config:
          param3: value3
  - api: test_api
    name: another_chain
    steps:
      - name: step3
        config: null
"""
        yaml_file = tmp_path / "test_config.yml"
        yaml_file.write_text(yaml_content)

        config = LoadedConfig.from_yaml(yaml_file)

        # Verify APIs
        assert "test_api" in config.apis()

        # Verify chains
        assert set(config.chains("test_api")) == {"test_chain", "another_chain"}

        # Verify stages
        assert config.stages("test_api", "test_chain") == ["step1", "step2"]
        assert config.stages("test_api", "another_chain") == ["step3"]

        # Verify stage configs
        assert config.stage_config("test_api", "test_chain", "step1") == {
            "param1": "value1",
            "param2": "value2",
        }
        assert config.stage_config("test_api", "test_chain", "step2") == {
            "param3": "value3"
        }
        assert config.stage_config("test_api", "another_chain", "step3") is None

    def test_from_yaml_multiple_apis(self, tmp_path):
        """Test from_yaml() with multiple APIs."""
        yaml_content = """
chains:
  - api: api1
    name: chain1
    steps:
      - name: stage1
        config:
          key: value1
  - api: api2
    name: chain2
    steps:
      - name: stage2
        config:
          key: value2
"""
        yaml_file = tmp_path / "multi_api_config.yml"
        yaml_file.write_text(yaml_content)

        config = LoadedConfig.from_yaml(yaml_file)

        assert set(config.apis()) == {"api1", "api2"}
        assert config.chains("api1") == ["chain1"]
        assert config.chains("api2") == ["chain2"]

    def test_from_yaml_empty_config(self, tmp_path):
        """Test from_yaml() with minimal configuration."""
        yaml_content = """
chains: []
"""
        yaml_file = tmp_path / "empty_config.yml"
        yaml_file.write_text(yaml_content)

        config = LoadedConfig.from_yaml(yaml_file)

        assert config.apis() == []

    def test_from_yaml_with_pathlib_path(self, tmp_path):
        """Test from_yaml() accepts pathlib.Path."""
        yaml_content = """
chains:
  - api: test_api
    name: test_chain
    steps:
      - name: test_stage
"""
        yaml_file = tmp_path / "pathlib_test.yml"
        yaml_file.write_text(yaml_content)

        config = LoadedConfig.from_yaml(Path(yaml_file))

        assert "test_api" in config.apis()

    def test_root_config_cls_attribute(self):
        """Test that ROOT_CONFIG_CLS is set to RootConfig."""
        assert LoadedConfig.ROOT_CONFIG_CLS is RootConfig

    def test_stage_config_with_none_value(self):
        """Test stage configuration with None value."""
        stage_cfg_map = {
            "api1": {
                "chain1": {
                    "stage1": None,
                },
            },
        }
        chain_stage_map = {
            "api1": {
                "chain1": ["stage1"],
            },
        }

        config = LoadedConfig(
            stage_cfg_map=stage_cfg_map, chain_stage_map=chain_stage_map
        )

        assert config.stage_config("api1", "chain1", "stage1") is None
