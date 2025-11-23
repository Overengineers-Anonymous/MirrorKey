import pytest
from pydantic import ValidationError
from core.config.schema import ChainStepConfig, ChainConfig, RootConfig


class TestChainStepConfig:
    """Test cases for the ChainStepConfig pydantic model."""

    def test_init_with_config(self):
        """Test ChainStepConfig initialization with config."""
        step = ChainStepConfig(name="test_step", config={"key": "value"})

        assert step.name == "test_step"
        assert step.config == {"key": "value"}

    def test_init_without_config(self):
        """Test ChainStepConfig initialization without config (defaults to None)."""
        step = ChainStepConfig(name="test_step")

        assert step.name == "test_step"
        assert step.config is None

    def test_init_with_none_config(self):
        """Test ChainStepConfig initialization with explicit None config."""
        step = ChainStepConfig(name="test_step", config=None)

        assert step.name == "test_step"
        assert step.config is None

    def test_init_with_empty_config(self):
        """Test ChainStepConfig initialization with empty config dict."""
        step = ChainStepConfig(name="test_step", config={})

        assert step.name == "test_step"
        assert step.config == {}

    def test_init_with_nested_config(self):
        """Test ChainStepConfig initialization with nested config."""
        config_data = {
            "level1": {
                "level2": {
                    "key": "value",
                    "list": [1, 2, 3],
                }
            }
        }
        step = ChainStepConfig(name="complex_step", config=config_data)

        assert step.name == "complex_step"
        assert step.config == config_data

    def test_missing_name_raises_error(self):
        """Test that missing name field raises ValidationError."""
        with pytest.raises(ValidationError):
            ChainStepConfig(config={"key": "value"})

    def test_model_serialization(self):
        """Test that model can be serialized to dict."""
        step = ChainStepConfig(name="test_step", config={"key": "value"})
        data = step.model_dump()

        assert data["name"] == "test_step"
        assert data["config"] == {"key": "value"}


class TestChainConfig:
    """Test cases for the ChainConfig pydantic model."""

    def test_init_basic(self):
        """Test ChainConfig initialization."""
        steps = [
            ChainStepConfig(name="step1", config={"key1": "value1"}),
            ChainStepConfig(name="step2", config={"key2": "value2"}),
        ]
        chain = ChainConfig(api="test_api", name="test_chain", steps=steps)

        assert chain.api == "test_api"
        assert chain.name == "test_chain"
        assert len(chain.steps) == 2
        assert chain.steps[0].name == "step1"
        assert chain.steps[1].name == "step2"

    def test_init_with_empty_steps(self):
        """Test ChainConfig initialization with empty steps list."""
        chain = ChainConfig(api="test_api", name="test_chain", steps=[])

        assert chain.api == "test_api"
        assert chain.name == "test_chain"
        assert chain.steps == []

    def test_init_with_dict_steps(self):
        """Test ChainConfig initialization with dict steps (pydantic conversion)."""
        chain = ChainConfig(
            api="test_api",
            name="test_chain",
            steps=[
                {"name": "step1", "config": {"key": "value"}},
                {"name": "step2"},
            ],
        )

        assert len(chain.steps) == 2
        assert isinstance(chain.steps[0], ChainStepConfig)
        assert chain.steps[0].name == "step1"
        assert chain.steps[0].config == {"key": "value"}
        assert chain.steps[1].name == "step2"
        assert chain.steps[1].config is None

    def test_missing_api_raises_error(self):
        """Test that missing api field raises ValidationError."""
        with pytest.raises(ValidationError):
            ChainConfig(name="test_chain", steps=[])

    def test_missing_name_raises_error(self):
        """Test that missing name field raises ValidationError."""
        with pytest.raises(ValidationError):
            ChainConfig(api="test_api", steps=[])

    def test_missing_steps_raises_error(self):
        """Test that missing steps field raises ValidationError."""
        with pytest.raises(ValidationError):
            ChainConfig(api="test_api", name="test_chain")

    def test_model_serialization(self):
        """Test that model can be serialized to dict."""
        chain = ChainConfig(
            api="test_api",
            name="test_chain",
            steps=[{"name": "step1", "config": {"key": "value"}}],
        )
        data = chain.model_dump()

        assert data["api"] == "test_api"
        assert data["name"] == "test_chain"
        assert len(data["steps"]) == 1
        assert data["steps"][0]["name"] == "step1"


class TestRootConfig:
    """Test cases for the RootConfig pydantic model."""

    def test_init_basic(self):
        """Test RootConfig initialization."""
        chains = [
            ChainConfig(
                api="api1",
                name="chain1",
                steps=[ChainStepConfig(name="step1", config={"key": "value"})],
            ),
            ChainConfig(api="api2", name="chain2", steps=[]),
        ]
        root = RootConfig(chains=chains)

        assert len(root.chains) == 2
        assert root.chains[0].api == "api1"
        assert root.chains[1].api == "api2"

    def test_init_with_empty_chains(self):
        """Test RootConfig initialization with empty chains list."""
        root = RootConfig(chains=[])

        assert root.chains == []

    def test_init_with_dict_chains(self):
        """Test RootConfig initialization with dict chains (pydantic conversion)."""
        root = RootConfig(
            chains=[
                {
                    "api": "test_api",
                    "name": "test_chain",
                    "steps": [{"name": "step1", "config": {"key": "value"}}],
                }
            ]
        )

        assert len(root.chains) == 1
        assert isinstance(root.chains[0], ChainConfig)
        assert root.chains[0].api == "test_api"
        assert root.chains[0].name == "test_chain"
        assert len(root.chains[0].steps) == 1

    def test_missing_chains_raises_error(self):
        """Test that missing chains field raises ValidationError."""
        with pytest.raises(ValidationError):
            RootConfig()

    def test_model_serialization(self):
        """Test that model can be serialized to dict."""
        root = RootConfig(
            chains=[
                {
                    "api": "test_api",
                    "name": "test_chain",
                    "steps": [{"name": "step1"}],
                }
            ]
        )
        data = root.model_dump()

        assert "chains" in data
        assert len(data["chains"]) == 1
        assert data["chains"][0]["api"] == "test_api"

    def test_complex_nested_structure(self):
        """Test RootConfig with complex nested structure."""
        root = RootConfig(
            chains=[
                {
                    "api": "api1",
                    "name": "chain1",
                    "steps": [
                        {"name": "step1", "config": {"param1": "value1"}},
                        {"name": "step2", "config": {"param2": {"nested": "value2"}}},
                        {"name": "step3", "config": None},
                    ],
                },
                {
                    "api": "api2",
                    "name": "chain2",
                    "steps": [
                        {"name": "step4", "config": {"list": [1, 2, 3]}},
                    ],
                },
            ]
        )

        assert len(root.chains) == 2
        assert len(root.chains[0].steps) == 3
        assert root.chains[0].steps[0].config["param1"] == "value1"
        assert root.chains[0].steps[1].config["param2"]["nested"] == "value2"
        assert root.chains[0].steps[2].config is None
        assert root.chains[1].steps[0].config["list"] == [1, 2, 3]

    def test_from_dict(self):
        """Test creating RootConfig from dictionary (simulating YAML load)."""
        data = {
            "chains": [
                {
                    "api": "test_api",
                    "name": "test_chain",
                    "steps": [
                        {"name": "step1", "config": {"key": "value"}},
                    ],
                }
            ]
        }
        root = RootConfig(**data)

        assert isinstance(root, RootConfig)
        assert len(root.chains) == 1
        assert root.chains[0].api == "test_api"
