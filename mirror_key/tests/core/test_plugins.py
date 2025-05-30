import pytest
from unittest.mock import patch, MagicMock
from mirror_key.core.plugins import PluginLoader

@pytest.fixture
def vpl():
    mock = MagicMock()
    mock.config.api_descriptors = {"test_plugin": None}
    return PluginLoader(mock)

def test_register(vpl):
    vpl.register_plugin("test_plugin")
    assert "test_plugin" in vpl.loaded_plugins


def test_register_plugin_already_loaded(vpl):
    vpl.loaded_plugins = ["test_plugin"]
    with pytest.raises(Exception) as excinfo:
        vpl.register_plugin("test_plugin")
    assert "already loaded" in str(excinfo.value)

def test_register_plugin_missing_dependency(vpl):
    # test_plugin2 is not loaded, should raise UnloadedPluginError
    with pytest.raises(Exception) as excinfo:
        vpl.register_plugin("test_plugin", ["test_plugin2"])
    assert "not loaded" in str(excinfo.value)

def test_ensure_dependencies_all_loaded(vpl):
    vpl.loaded_plugins = ["a", "b", "c"]
    # Should not raise
    vpl.ensure_dependencies(["a", "b"])

def test_ensure_dependencies_not_loaded(vpl):
    vpl.loaded_plugins = ["a"]
    with pytest.raises(Exception):
        vpl.ensure_dependencies(["a", "b"])

def test_load_plugins_success(monkeypatch):
    mock_config = MagicMock()
    mock_config.config.api_descriptors = ["foo"]
    loader = PluginLoader(mock_config)
    monkeypatch.setattr("importlib.import_module", lambda name: None)
    loader.load()
    # No exception means success

def test_load_plugins_fallback(monkeypatch):
    mock_config = MagicMock()
    mock_config.config.api_descriptors = ["foo"]
    loader = PluginLoader(mock_config)
    # First import fails, second succeeds
    def import_module_side_effect(name):
        if name.startswith("plugins."):
            raise ImportError("fail")
        return None
    monkeypatch.setattr("importlib.import_module", import_module_side_effect)
    loader.load()

def test_load_plugins_both_fail(monkeypatch, capsys):
    mock_config = MagicMock()
    mock_config.config.api_descriptors = ["foo"]
    loader = PluginLoader(mock_config)
    def import_module_side_effect(name):
        raise ImportError("fail")
    monkeypatch.setattr("importlib.import_module", import_module_side_effect)
    loader.load()
    captured = capsys.readouterr()
    assert "Failed to load plugin foo" in captured.out

def test_load_no_plugins(monkeypatch, caplog):
    mock_config = MagicMock()
    mock_config.config.api_descriptors = []
    loader = PluginLoader(mock_config)
    with caplog.at_level("WARNING"):
        loader.load()
    assert "No Plugins to load" in caplog.text
