from unittest.mock import MagicMock, patch

import pytest

from core.api.manager import APIPluginManager
from core.importer import Importer


class TestImporter:
    """Test cases for the Importer class."""

    @pytest.fixture
    def plugin_manager(self):
        """Create a mock plugin manager."""
        return MagicMock(spec=APIPluginManager)

    @pytest.fixture
    def importer(self, plugin_manager):
        """Create an Importer instance with a mock plugin manager."""
        return Importer(plugin_manager=plugin_manager)

    def test_init(self, plugin_manager):
        """Test Importer initialization."""
        importer = Importer(plugin_manager=plugin_manager)
        assert importer.imported_modules == {}
        assert importer.plugin_manager == plugin_manager

    def test_import_module_new(self, importer):
        """Test importing a new module."""
        with patch("core.importer.import_module") as mock_import:
            mock_module = MagicMock()
            mock_import.return_value = mock_module

            importer.import_module("test.module")

            mock_import.assert_called_once_with("test.module")
            assert "test.module" in importer.imported_modules
            assert importer.imported_modules["test.module"] == mock_module

    def test_import_module_cached(self, importer):
        """Test importing an already imported module (should use cache)."""
        mock_module = MagicMock()
        importer.imported_modules["cached.module"] = mock_module

        with patch("core.importer.import_module") as mock_import:
            result = importer.import_module("cached.module")

            mock_import.assert_not_called()
            assert result == mock_module

    def test_import_api_success(self, importer, plugin_manager):
        """Test successful API import."""
        plugin_manager.api_plugins = {"test_api": MagicMock()}

        with patch("core.importer.import_module") as mock_import:
            mock_import.return_value = MagicMock()

            importer.import_api("test_api")

            mock_import.assert_called_once_with("apis.test_api")
            assert "apis.test_api" in importer.imported_modules

    def test_import_api_not_registered(self, importer, plugin_manager):
        """Test API import when API doesn't register with plugin manager."""
        plugin_manager.api_plugins = {}

        with patch("core.importer.import_module") as mock_import:
            mock_import.return_value = MagicMock()

            with pytest.raises(ImportError) as exc_info:
                importer.import_api("test_api")

            assert "API 'test_api' failed to register" in str(exc_info.value)
            assert "apis.test_api" in str(exc_info.value)

    def test_import_stage_plugin_success(self, importer, plugin_manager):
        """Test successful stage plugin import."""
        mock_api = MagicMock()
        mock_api.chain_stages = {"test_stage": MagicMock()}
        plugin_manager.get_api.return_value = mock_api

        with patch("core.importer.import_module") as mock_import:
            mock_import.return_value = MagicMock()

            importer.import_stage_plugin("test_api", "test_stage")

            plugin_manager.get_api.assert_called_once_with("test_api")
            mock_import.assert_called_once_with("stages.test_api.test_stage")
            assert "stages.test_api.test_stage" in importer.imported_modules

    def test_import_stage_plugin_api_not_found(self, importer, plugin_manager):
        """Test stage plugin import when API is not found."""
        plugin_manager.get_api.return_value = None

        with pytest.raises(ValueError) as exc_info:
            importer.import_stage_plugin("test_api", "test_stage")

        assert "API 'test_api' not found" in str(exc_info.value)

    def test_import_stage_plugin_stage_not_registered(self, importer, plugin_manager):
        """Test stage plugin import when stage doesn't register."""
        mock_api = MagicMock()
        mock_api.chain_stages = {}
        mock_api.interface.name = "test_api"
        plugin_manager.get_api.return_value = mock_api

        with patch("core.importer.import_module") as mock_import:
            mock_import.return_value = MagicMock()

            with pytest.raises(ImportError) as exc_info:
                importer.import_stage_plugin("test_api", "test_stage")

            assert "Stage 'test_stage' for API 'test_api' failed to register" in str(
                exc_info.value
            )
            assert "stages.test_api.test_stage" in str(exc_info.value)
