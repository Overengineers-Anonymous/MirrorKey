import pytest
from unittest.mock import MagicMock
from fastapi import APIRouter
from core.api.plugin import APIPlugin
from core.chain.controller import ChainController
from core.interface.main import Interface
from core.chain.chain import ChainStage


class TestAPIPlugin:
    """Test cases for the APIPlugin class."""

    @pytest.fixture
    def mock_stage_class(self):
        """Create a mock ChainStage class."""

        class MockStage:
            pass

        return MockStage

    @pytest.fixture
    def mock_chain_controller(self, mock_stage_class):
        """Create a mock ChainController."""
        controller = MagicMock(spec=ChainController)
        controller.stage_class = mock_stage_class
        return controller

    @pytest.fixture
    def mock_interface(self, mock_stage_class):
        """Create a mock Interface."""
        interface = MagicMock(spec=Interface)
        interface.stage_class = mock_stage_class
        interface.stages = {"stage1": MagicMock(), "stage2": MagicMock()}
        return interface

    @pytest.fixture
    def mock_router(self):
        """Create a mock APIRouter."""
        return MagicMock(spec=APIRouter)

    @pytest.fixture
    def api_plugin(self, mock_chain_controller, mock_interface, mock_router):
        """Create an APIPlugin instance."""
        return APIPlugin(
            name="test_plugin",
            chain_controller=mock_chain_controller,
            interface=mock_interface,
            router=mock_router,
        )

    def test_init(self, mock_chain_controller, mock_interface, mock_router, mock_stage_class):
        """Test APIPlugin initialization."""
        plugin = APIPlugin(
            name="test_plugin",
            chain_controller=mock_chain_controller,
            interface=mock_interface,
            router=mock_router,
        )

        assert plugin.name == "test_plugin"
        assert plugin.chain_controller is mock_chain_controller
        assert plugin.interface is mock_interface
        assert plugin.router is mock_router

    def test_name_attribute(self, api_plugin):
        """Test name attribute access."""
        assert api_plugin.name == "test_plugin"

    def test_chain_controller_attribute(self, api_plugin, mock_chain_controller):
        """Test chain_controller attribute access."""
        assert api_plugin.chain_controller is mock_chain_controller

    def test_interface_attribute(self, api_plugin, mock_interface):
        """Test interface attribute access."""
        assert api_plugin.interface is mock_interface

    def test_router_attribute(self, api_plugin, mock_router):
        """Test router attribute access."""
        assert api_plugin.router is mock_router

    def test_stage_class_property(self, api_plugin, mock_stage_class):
        """Test stage_class property returns correct class from chain_controller."""
        assert api_plugin.stage_class is mock_stage_class

    def test_chain_stages_property(self, api_plugin, mock_interface):
        """Test chain_stages property returns stages from interface."""
        stages = api_plugin.chain_stages

        assert stages is mock_interface.stages
        assert "stage1" in stages
        assert "stage2" in stages

    def test_properties_reflect_controller_changes(self, mock_chain_controller, mock_interface, mock_router):
        """Test that properties reflect changes in underlying objects."""
        plugin = APIPlugin(
            name="dynamic_test",
            chain_controller=mock_chain_controller,
            interface=mock_interface,
            router=mock_router,
        )

        # Change stage_class on controller
        new_stage_class = type("NewStage", (), {})
        mock_chain_controller.stage_class = new_stage_class

        assert plugin.stage_class is new_stage_class

    def test_properties_reflect_interface_changes(self, mock_chain_controller, mock_interface, mock_router):
        """Test that properties reflect changes in interface."""
        plugin = APIPlugin(
            name="dynamic_test",
            chain_controller=mock_chain_controller,
            interface=mock_interface,
            router=mock_router,
        )

        # Add new stage to interface
        new_stage = MagicMock()
        mock_interface.stages["stage3"] = new_stage

        assert "stage3" in plugin.chain_stages
        assert plugin.chain_stages["stage3"] is new_stage

    def test_multiple_plugins_independent(self):
        """Test that multiple plugin instances are independent."""
        controller1 = MagicMock(spec=ChainController)
        controller1.stage_class = type("Stage1", (), {})
        interface1 = MagicMock(spec=Interface)
        interface1.stages = {"s1": MagicMock()}
        router1 = MagicMock(spec=APIRouter)

        controller2 = MagicMock(spec=ChainController)
        controller2.stage_class = type("Stage2", (), {})
        interface2 = MagicMock(spec=Interface)
        interface2.stages = {"s2": MagicMock()}
        router2 = MagicMock(spec=APIRouter)

        plugin1 = APIPlugin("plugin1", controller1, interface1, router1)
        plugin2 = APIPlugin("plugin2", controller2, interface2, router2)

        assert plugin1.name != plugin2.name
        assert plugin1.stage_class != plugin2.stage_class
        assert plugin1.chain_stages != plugin2.chain_stages
