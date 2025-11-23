import pytest
from unittest.mock import MagicMock
from core.api.manager import APIPluginManager
from core.api.plugin import APIPlugin


class TestAPIPluginManager:
    """Test cases for the APIPluginManager class."""

    @pytest.fixture
    def manager(self):
        """Create an APIPluginManager instance."""
        return APIPluginManager()

    @pytest.fixture
    def mock_plugin(self):
        """Create a mock API plugin."""
        plugin = MagicMock(spec=APIPlugin)
        plugin.name = "test_plugin"
        return plugin

    def test_init(self):
        """Test APIPluginManager initialization."""
        manager = APIPluginManager()
        assert manager.api_plugins == {}
        assert isinstance(manager.api_plugins, dict)

    def test_register_plugin_success(self, manager, mock_plugin):
        """Test successful plugin registration."""
        result = manager.register_plugin(mock_plugin)

        assert "test_plugin" in manager.api_plugins
        assert manager.api_plugins["test_plugin"] is mock_plugin
        assert result is mock_plugin

    def test_register_plugin_duplicate_raises_error(self, manager, mock_plugin):
        """Test that registering a plugin with duplicate name raises ValueError."""
        manager.register_plugin(mock_plugin)

        # Try to register another plugin with the same name
        duplicate_plugin = MagicMock(spec=APIPlugin)
        duplicate_plugin.name = "test_plugin"

        with pytest.raises(ValueError) as exc_info:
            manager.register_plugin(duplicate_plugin)

        assert "API with name 'test_plugin' is already registered" in str(exc_info.value)

    def test_register_multiple_plugins(self, manager):
        """Test registering multiple plugins with different names."""
        plugin1 = MagicMock(spec=APIPlugin)
        plugin1.name = "plugin1"
        plugin2 = MagicMock(spec=APIPlugin)
        plugin2.name = "plugin2"
        plugin3 = MagicMock(spec=APIPlugin)
        plugin3.name = "plugin3"

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)
        manager.register_plugin(plugin3)

        assert len(manager.api_plugins) == 3
        assert manager.api_plugins["plugin1"] is plugin1
        assert manager.api_plugins["plugin2"] is plugin2
        assert manager.api_plugins["plugin3"] is plugin3

    def test_get_api_existing_plugin(self, manager, mock_plugin):
        """Test getting an existing plugin."""
        manager.register_plugin(mock_plugin)

        result = manager.get_api("test_plugin")

        assert result is mock_plugin

    def test_get_api_nonexistent_plugin_returns_none(self, manager):
        """Test getting a non-existent plugin returns None."""
        result = manager.get_api("nonexistent_plugin")

        assert result is None

    def test_get_api_after_multiple_registrations(self, manager):
        """Test getting specific API after registering multiple plugins."""
        plugin1 = MagicMock(spec=APIPlugin)
        plugin1.name = "plugin1"
        plugin2 = MagicMock(spec=APIPlugin)
        plugin2.name = "plugin2"

        manager.register_plugin(plugin1)
        manager.register_plugin(plugin2)

        result1 = manager.get_api("plugin1")
        result2 = manager.get_api("plugin2")

        assert result1 is plugin1
        assert result2 is plugin2

    def test_api_plugins_is_mutable(self, manager, mock_plugin):
        """Test that api_plugins dict is accessible and mutable."""
        assert len(manager.api_plugins) == 0

        manager.register_plugin(mock_plugin)
        assert len(manager.api_plugins) == 1

        # Should be able to access the dict directly
        plugins_dict = manager.api_plugins
        assert "test_plugin" in plugins_dict
