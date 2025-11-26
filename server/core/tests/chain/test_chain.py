import pytest

from core.chain.chain import Chain


class TestChain:
    """Test cases for the Chain class."""

    @pytest.fixture
    def stage_class(self):
        """Create a concrete ChainStage implementation."""

        class ConcreteStage:
            def __init__(self, name: str = "stage"):
                self.name = name

        return ConcreteStage

    @pytest.fixture
    def chain(self, stage_class):
        """Create a Chain instance."""
        return Chain(name="test_chain", stage_class=stage_class)

    def test_init(self, stage_class):
        """Test Chain initialization."""
        chain = Chain(name="test_chain", stage_class=stage_class)

        assert chain.name == "test_chain"
        assert chain.stage_class is stage_class
        assert chain.stages == []
        assert isinstance(chain.stages, list)

    def test_add_stage_success(self, chain, stage_class):
        """Test successfully adding a stage to the chain."""
        stage = stage_class("stage1")

        chain.add_stage(stage)

        assert len(chain.stages) == 1
        assert chain.stages[0] is stage

    def test_add_multiple_stages(self, chain, stage_class):
        """Test adding multiple stages to the chain."""
        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")
        stage3 = stage_class("stage3")

        chain.add_stage(stage1)
        chain.add_stage(stage2)
        chain.add_stage(stage3)

        assert len(chain.stages) == 3
        assert chain.stages[0] is stage1
        assert chain.stages[1] is stage2
        assert chain.stages[2] is stage3

    def test_add_stage_wrong_type_raises_error(self, chain):
        """Test that adding a stage of wrong type raises TypeError."""

        class WrongStage:
            pass

        wrong_stage = WrongStage()

        with pytest.raises(TypeError) as exc_info:
            chain.add_stage(wrong_stage)

        assert "Stage must be an instance of the specified ChainStage protocol" in str(
            exc_info.value
        )

    def test_get_stages_by_index(self, chain, stage_class):
        """Test getting a stage by index."""
        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")
        stage3 = stage_class("stage3")

        chain.add_stage(stage1)
        chain.add_stage(stage2)
        chain.add_stage(stage3)

        assert chain.get_stages(0) is stage1
        assert chain.get_stages(1) is stage2
        assert chain.get_stages(2) is stage3

    def test_get_stages_negative_index(self, chain, stage_class):
        """Test getting a stage with negative index."""
        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")

        chain.add_stage(stage1)
        chain.add_stage(stage2)

        assert chain.get_stages(-1) is stage2
        assert chain.get_stages(-2) is stage1

    def test_get_stages_out_of_range_raises_error(self, chain, stage_class):
        """Test that accessing out of range index raises IndexError."""
        stage = stage_class("stage1")
        chain.add_stage(stage)

        with pytest.raises(IndexError):
            chain.get_stages(5)

    def test_get_stage_index_success(self, chain, stage_class):
        """Test getting the index of a stage."""
        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")
        stage3 = stage_class("stage3")

        chain.add_stage(stage1)
        chain.add_stage(stage2)
        chain.add_stage(stage3)

        assert chain.get_stage_index(stage1) == 0
        assert chain.get_stage_index(stage2) == 1
        assert chain.get_stage_index(stage3) == 2

    def test_get_stage_index_not_found_raises_error(self, chain, stage_class):
        """Test that getting index of non-existent stage raises ValueError."""
        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")

        chain.add_stage(stage1)

        with pytest.raises(ValueError) as exc_info:
            chain.get_stage_index(stage2)

        assert "Stage not found in chain" in str(exc_info.value)

    def test_len(self, chain, stage_class):
        """Test __len__ method returns correct number of stages."""
        assert len(chain) == 0

        chain.add_stage(stage_class("stage1"))
        assert len(chain) == 1

        chain.add_stage(stage_class("stage2"))
        assert len(chain) == 2

        chain.add_stage(stage_class("stage3"))
        assert len(chain) == 3

    def test_multiple_chains_independent(self, stage_class):
        """Test that multiple chain instances are independent."""
        chain1 = Chain(name="chain1", stage_class=stage_class)
        chain2 = Chain(name="chain2", stage_class=stage_class)

        stage1 = stage_class("stage1")
        stage2 = stage_class("stage2")

        chain1.add_stage(stage1)
        chain2.add_stage(stage2)

        assert len(chain1) == 1
        assert len(chain2) == 1
        assert chain1.stages[0] is stage1
        assert chain2.stages[0] is stage2

    def test_chain_preserves_order(self, chain, stage_class):
        """Test that chain preserves the order of added stages."""
        stages = [stage_class(f"stage{i}") for i in range(10)]

        for stage in stages:
            chain.add_stage(stage)

        for i, stage in enumerate(stages):
            assert chain.get_stages(i) is stage
            assert chain.get_stage_index(stage) == i
