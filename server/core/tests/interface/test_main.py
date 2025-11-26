from unittest.mock import MagicMock

import pytest

from core.chain.chain import ChainStageBuilder
from core.interface.main import Interface


class TestInterface:
    """Test cases for the Interface class."""

    @pytest.fixture
    def stage_class(self):
        """Create a concrete ChainStage implementation."""

        class ConcreteStage:
            def __init__(self, name: str = "stage"):
                self.name = name

        return ConcreteStage

    @pytest.fixture
    def interface(self, stage_class):
        """Create an Interface instance."""
        return Interface(name="test_interface", stage_class=stage_class)

    @pytest.fixture
    def mock_stage_builder(self):
        """Create a mock ChainStageBuilder."""
        builder = MagicMock(spec=ChainStageBuilder)
        return builder

    def test_init(self, stage_class):
        """Test Interface initialization."""
        interface = Interface(name="test_interface", stage_class=stage_class)

        assert interface.name == "test_interface"
        assert interface.stage_class is stage_class
        assert interface.stages == {}
        assert isinstance(interface.stages, dict)

    def test_name_attribute(self, interface):
        """Test name attribute access."""
        assert interface.name == "test_interface"

    def test_stage_class_attribute(self, interface, stage_class):
        """Test stage_class attribute access."""
        assert interface.stage_class is stage_class

    def test_stages_attribute_initial(self, interface):
        """Test stages attribute is initially empty."""
        assert interface.stages == {}

    def test_register_stage_success(self, interface, mock_stage_builder):
        """Test successfully registering a stage."""
        interface.register_stage("stage1", mock_stage_builder)

        assert "stage1" in interface.stages
        assert interface.stages["stage1"] is mock_stage_builder

    def test_register_multiple_stages(self, interface):
        """Test registering multiple stages."""
        builder1 = MagicMock(spec=ChainStageBuilder)
        builder2 = MagicMock(spec=ChainStageBuilder)
        builder3 = MagicMock(spec=ChainStageBuilder)

        interface.register_stage("stage1", builder1)
        interface.register_stage("stage2", builder2)
        interface.register_stage("stage3", builder3)

        assert len(interface.stages) == 3
        assert interface.stages["stage1"] is builder1
        assert interface.stages["stage2"] is builder2
        assert interface.stages["stage3"] is builder3

    def test_register_stage_duplicate_name_raises_error(
        self, interface, mock_stage_builder
    ):
        """Test that registering a stage with duplicate name raises ValueError."""
        interface.register_stage("duplicate", mock_stage_builder)

        another_builder = MagicMock(spec=ChainStageBuilder)

        with pytest.raises(ValueError) as exc_info:
            interface.register_stage("duplicate", another_builder)

        assert "Stage 'duplicate' is already registered" in str(exc_info.value)

    def test_register_stage_not_protocol_instance_raises_error(self, interface):
        """Test that registering non-ChainStageBuilder raises TypeError."""
        not_a_builder = "not a builder"

        with pytest.raises(TypeError) as exc_info:
            interface.register_stage("invalid", not_a_builder)

        assert "Stage must be an instance of the specified ChainStage protocol" in str(
            exc_info.value
        )

    def test_stages_is_mutable(self, interface, mock_stage_builder):
        """Test that stages dict is accessible and mutable through registration."""
        assert len(interface.stages) == 0

        interface.register_stage("stage1", mock_stage_builder)
        assert len(interface.stages) == 1

        # Should be able to access the dict directly
        stages_dict = interface.stages
        assert "stage1" in stages_dict

    def test_multiple_interfaces_independent(self, stage_class):
        """Test that multiple interface instances are independent."""
        interface1 = Interface(name="interface1", stage_class=stage_class)
        interface2 = Interface(name="interface2", stage_class=stage_class)

        builder1 = MagicMock(spec=ChainStageBuilder)
        builder2 = MagicMock(spec=ChainStageBuilder)

        interface1.register_stage("stage1", builder1)
        interface2.register_stage("stage2", builder2)

        assert "stage1" in interface1.stages
        assert "stage1" not in interface2.stages
        assert "stage2" in interface2.stages
        assert "stage2" not in interface1.stages

    def test_interface_with_different_stage_classes(self):
        """Test interfaces with different stage classes."""

        class StageClass1:
            pass

        class StageClass2:
            pass

        interface1 = Interface(name="interface1", stage_class=StageClass1)
        interface2 = Interface(name="interface2", stage_class=StageClass2)

        assert interface1.stage_class is StageClass1
        assert interface2.stage_class is StageClass2
        assert interface1.stage_class != interface2.stage_class

    def test_register_stage_preserves_builder_reference(self, interface):
        """Test that registered builder maintains its reference."""
        builder = MagicMock(spec=ChainStageBuilder)
        builder.custom_attribute = "custom_value"

        interface.register_stage("test_stage", builder)

        retrieved_builder = interface.stages["test_stage"]
        assert retrieved_builder is builder
        assert retrieved_builder.custom_attribute == "custom_value"

    def test_stage_registration_order_preserved(self, interface):
        """Test that stage registration order is preserved in dict."""
        builders = [MagicMock(spec=ChainStageBuilder) for _ in range(5)]

        for i, builder in enumerate(builders):
            interface.register_stage(f"stage{i}", builder)

        # Python 3.7+ dicts maintain insertion order
        stage_names = list(interface.stages.keys())
        assert stage_names == [f"stage{i}" for i in range(5)]
