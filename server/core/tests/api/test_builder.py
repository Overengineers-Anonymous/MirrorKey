from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI

from core.api.builder import ApiBuilder
from core.api.manager import APIPluginManager
from core.config.loader import LoadedConfig
from core.importer import Importer


class TestApiBuilder:
    """Test cases for the ApiBuilder class."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a mock plugin manager."""
        return MagicMock(spec=APIPluginManager)

    @pytest.fixture
    def importer(self):
        """Create a mock importer."""
        return MagicMock(spec=Importer)

    @pytest.fixture
    def api_builder(self, plugin_manager, importer):
        """Create an ApiBuilder instance."""
        return ApiBuilder(plugins_src=plugin_manager, importer=importer)

    @pytest.fixture
    def config(self):
        """Create a mock configuration."""
        mock_config = MagicMock(spec=LoadedConfig)
        mock_config.apis.return_value = ["test_api"]
        mock_config.chains.return_value = ["test_chain"]
        mock_config.stages.return_value = ["test_stage"]
        mock_config.stage_config.return_value = {"key": "value"}
        return mock_config

    def test_init(self, plugin_manager, importer):
        """Test ApiBuilder initialization."""
        builder = ApiBuilder(plugins_src=plugin_manager, importer=importer)
        assert builder.plugins_src == plugin_manager
        assert builder.importer == importer

    def test_load_stages_success(self, api_builder, config, plugin_manager, importer):
        """Test successful loading of stages."""
        # Setup mock API
        mock_api = MagicMock()
        mock_stage_class = MagicMock()
        mock_api.stage_class = mock_stage_class
        mock_api.interface.name = "test_api"

        # Setup chain stages
        mock_stage_builder = MagicMock()
        mock_stage_instance = MagicMock()
        mock_stage_builder.build.return_value = mock_stage_instance
        mock_api.chain_stages = {"test_stage": mock_stage_builder}

        # Setup chain controller
        mock_chain_controller = MagicMock()
        mock_api.chain_controller = mock_chain_controller

        plugin_manager.get_api.return_value = mock_api

        with patch("core.api.builder.Chain") as mock_chain_class:
            mock_chain = MagicMock()
            mock_chain_class.return_value = mock_chain

            api_builder.load_stages(config)

            # Verify imports
            importer.import_api.assert_called_once_with("test_api")
            importer.import_stage_plugin.assert_called_once_with(
                "test_api", "test_stage"
            )

            # Verify chain creation
            mock_chain_class.assert_called_once_with("test_chain", mock_stage_class)

            # Verify stage building and adding
            mock_stage_builder.build.assert_called_once_with(
                {"key": "value"}, mock_chain
            )
            mock_chain.add_stage.assert_called_once_with(mock_stage_instance)

            # Verify chain added to controller
            mock_chain_controller.add_chain.assert_called_once_with(mock_chain)

    def test_load_stages_api_not_found(self, api_builder, config, plugin_manager):
        """Test load_stages when API is not found."""
        plugin_manager.get_api.return_value = None

        with pytest.raises(ValueError) as exc_info:
            api_builder.load_stages(config)

        assert "API 'test_api' not found" in str(exc_info.value)

    def test_load_stages_stage_not_registered(
        self, api_builder, config, plugin_manager, importer
    ):
        """Test load_stages when stage is not registered."""
        mock_api = MagicMock()
        mock_api.stage_class = MagicMock()
        mock_api.interface.name = "test_api"
        mock_api.chain_stages = {}  # Empty chain stages
        plugin_manager.get_api.return_value = mock_api

        with patch("core.api.builder.Chain"):
            with pytest.raises(ValueError) as exc_info:
                api_builder.load_stages(config)

            assert "Stage 'test_stage' not registered in API 'test_api'" in str(
                exc_info.value
            )

    def test_load_stages_multiple_chains(self, api_builder, plugin_manager, importer):
        """Test loading multiple chains and stages."""
        config = MagicMock(spec=LoadedConfig)
        config.apis.return_value = ["api1"]
        config.chains.return_value = ["chain1", "chain2"]
        config.stages.side_effect = [["stage1"], ["stage2"]]
        config.stage_config.return_value = {}

        mock_api = MagicMock()
        mock_api.stage_class = MagicMock()
        mock_api.interface.name = "api1"
        mock_api.chain_stages = {
            "stage1": MagicMock(),
            "stage2": MagicMock(),
        }
        plugin_manager.get_api.return_value = mock_api

        with patch("core.api.builder.Chain"):
            api_builder.load_stages(config)

            # Verify multiple chains were processed
            assert config.chains.call_count == 1
            assert importer.import_stage_plugin.call_count == 2

    def test_build_success(self, api_builder, config, plugin_manager):
        """Test successful build of FastAPI app."""
        fastapi_app = FastAPI()

        # Setup mock plugin with router
        mock_plugin = MagicMock()
        mock_router = MagicMock()
        mock_plugin.router = mock_router

        plugin_manager.api_plugins = {"test_api": mock_plugin}

        with patch.object(api_builder, "load_stages"):
            with patch.object(fastapi_app, "include_router") as mock_include_router:
                result = api_builder.build(fastapi_app, config)

                # Verify stages were loaded
                api_builder.load_stages.assert_called_once_with(config)

                # Verify router was included
                mock_include_router.assert_called_once_with(
                    mock_router, prefix="/test_api"
                )

                # Verify the same app is returned
                assert result is fastapi_app

    def test_build_multiple_plugins(self, api_builder, config, plugin_manager):
        """Test building with multiple API plugins."""
        fastapi_app = FastAPI()

        # Setup multiple mock plugins
        mock_plugin1 = MagicMock()
        mock_plugin1.router = MagicMock()
        mock_plugin2 = MagicMock()
        mock_plugin2.router = MagicMock()

        plugin_manager.api_plugins = {
            "api1": mock_plugin1,
            "api2": mock_plugin2,
        }

        with patch.object(api_builder, "load_stages"):
            with patch.object(fastapi_app, "include_router") as mock_include_router:
                api_builder.build(fastapi_app, config)

                # Verify both routers were included
                assert mock_include_router.call_count == 2
