from unittest.mock import MagicMock

import pytest

from core.chain.chain import Chain
from core.chain.controller import (
    ChainController,
    ForwardChainExecutor,
    ReverseChainExecutor,
)
from core.interface.main import Interface


class TestForwardChainExecutor:
    """Test cases for the ForwardChainExecutor class."""

    @pytest.fixture
    def stage_class(self):
        """Create a concrete ChainStage implementation."""

        class ConcreteStage:
            def __init__(self, name: str = "stage"):
                self.name = name

        return ConcreteStage

    @pytest.fixture
    def chain_with_stages(self, stage_class):
        """Create a chain with multiple stages."""
        chain = Chain(name="test_chain", stage_class=stage_class)
        for i in range(5):
            chain.add_stage(stage_class(f"stage{i}"))
        return chain

    def test_init_default(self, chain_with_stages):
        """Test ForwardChainExecutor initialization."""
        executor = ForwardChainExecutor(chain_with_stages)

        assert executor.chain is chain_with_stages
        assert executor.current_index == 0

    def test_init_custom_index(self, chain_with_stages):
        """Test ForwardChainExecutor initialization with custom index."""
        executor = ForwardChainExecutor(chain_with_stages, current_index=2)

        assert executor.current_index == 2

    def test_forward_iteration(self, chain_with_stages):
        """Test complete forward iteration."""
        executor = ForwardChainExecutor(chain_with_stages)

        for i in range(5):
            stage = executor.next()
            assert stage is not None
            assert stage.name == f"stage{i}"

        # Should return None after all stages
        assert executor.next() is None


class TestReverseChainExecutor:
    """Test cases for the ReverseChainExecutor class."""

    @pytest.fixture
    def stage_class(self):
        """Create a concrete ChainStage implementation."""

        class ConcreteStage:
            def __init__(self, name: str = "stage"):
                self.name = name

        return ConcreteStage

    @pytest.fixture
    def chain_with_stages(self, stage_class):
        """Create a chain with multiple stages."""
        chain = Chain(name="test_chain", stage_class=stage_class)
        for i in range(5):
            chain.add_stage(stage_class(f"stage{i}"))
        return chain

    def test_init_default(self, chain_with_stages):
        """Test ReverseChainExecutor initialization with default index."""
        executor = ReverseChainExecutor(chain_with_stages)

        assert executor.chain is chain_with_stages
        assert executor.current_index == 4  # len(chain) - 1

    def test_init_explicit_negative_one(self, chain_with_stages):
        """Test ReverseChainExecutor initialization with -1."""
        executor = ReverseChainExecutor(chain_with_stages, current_index=-1)

        assert executor.current_index == 4  # len(chain) - 1

    def test_init_custom_index(self, chain_with_stages):
        """Test ReverseChainExecutor initialization with custom index."""
        executor = ReverseChainExecutor(chain_with_stages, current_index=2)

        assert executor.current_index == 2

    def test_reverse_iteration(self, chain_with_stages):
        """Test complete reverse iteration."""
        executor = ReverseChainExecutor(chain_with_stages)

        for i in range(4, -1, -1):
            stage = executor.next()
            assert stage is not None
            assert stage.name == f"stage{i}"

        # Should return None after all stages
        assert executor.next() is None


class TestChainController:
    """Test cases for the ChainController class."""

    @pytest.fixture
    def stage_class(self):
        """Create a concrete ChainStage implementation."""

        class ConcreteStage:
            def __init__(self, name: str = "stage"):
                self.name = name

        return ConcreteStage

    @pytest.fixture
    def interface(self, stage_class):
        """Create a mock Interface."""
        interface = MagicMock(spec=Interface)
        interface.stage_class = stage_class
        return interface

    @pytest.fixture
    def controller(self, interface):
        """Create a ChainController instance."""
        return ChainController(interface=interface)

    def test_init(self, interface, stage_class):
        """Test ChainController initialization."""
        controller = ChainController(interface=interface)

        assert controller.stage_class is stage_class
        assert controller.chains == {}
        assert isinstance(controller.chains, dict)

    def test_add_chain_success(self, controller, stage_class):
        """Test successfully adding a chain."""
        chain = Chain(name="test_chain", stage_class=stage_class)

        controller.add_chain(chain)

        assert "test_chain" in controller.chains
        assert controller.chains["test_chain"] is chain

    def test_add_chain_not_chain_instance_raises_error(self, controller):
        """Test that adding non-Chain instance raises TypeError."""
        not_a_chain = MagicMock()

        with pytest.raises(TypeError) as exc_info:
            controller.add_chain(not_a_chain)

        assert "chain must be an instance of Chain" in str(exc_info.value)

    def test_add_chain_wrong_stage_class_raises_error(self, controller, stage_class):
        """Test that adding chain with wrong stage_class raises TypeError."""

        class DifferentStage:
            pass

        wrong_chain = Chain(name="wrong_chain", stage_class=DifferentStage)

        with pytest.raises(TypeError) as exc_info:
            controller.add_chain(wrong_chain)

        assert "Chain's state_class must be a subclass of the executor_class" in str(
            exc_info.value
        )

    def test_add_multiple_chains(self, controller, stage_class):
        """Test adding multiple chains."""
        chain1 = Chain(name="chain1", stage_class=stage_class)
        chain2 = Chain(name="chain2", stage_class=stage_class)
        chain3 = Chain(name="chain3", stage_class=stage_class)

        controller.add_chain(chain1)
        controller.add_chain(chain2)
        controller.add_chain(chain3)

        assert len(controller.chains) == 3
        assert controller.chains["chain1"] is chain1
        assert controller.chains["chain2"] is chain2
        assert controller.chains["chain3"] is chain3

    def test_get_executor_existing_chain(self, controller, stage_class):
        """Test getting an executor for an existing chain."""
        chain = Chain(name="test_chain", stage_class=stage_class)
        chain.add_stage(stage_class("stage1"))
        controller.add_chain(chain)

        executor = controller.get_executor("test_chain")

        assert executor is not None
        assert isinstance(executor, ForwardChainExecutor)
        assert executor.chain is chain

    def test_get_executor_nonexistent_chain_returns_none(self, controller):
        """Test getting an executor for a non-existent chain returns None."""
        executor = controller.get_executor("nonexistent_chain")

        assert executor is None

    def test_get_executor_creates_new_executor_each_time(self, controller, stage_class):
        """Test that get_executor creates a new executor instance each time."""
        chain = Chain(name="test_chain", stage_class=stage_class)
        controller.add_chain(chain)

        executor1 = controller.get_executor("test_chain")
        executor2 = controller.get_executor("test_chain")

        assert executor1 is not executor2
        assert executor1.chain is executor2.chain

    def test_chain_overwrite(self, controller, stage_class):
        """Test that adding a chain with same name overwrites the previous one."""
        chain1 = Chain(name="same_name", stage_class=stage_class)
        chain2 = Chain(name="same_name", stage_class=stage_class)

        controller.add_chain(chain1)
        controller.add_chain(chain2)

        assert len(controller.chains) == 1
        assert controller.chains["same_name"] is chain2
        assert controller.chains["same_name"] is not chain1
