import pytest
from murmur.core import Transformer, TransformerIO
from murmur.registry import TransformerRegistry


class MockTransformer(Transformer):
    name = "mock"
    inputs = ["input"]
    outputs = ["output"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        return TransformerIO(data={"output": "done"})


def test_registry_register_and_get():
    """Registry should store and retrieve transformers by name."""
    registry = TransformerRegistry()
    registry.register(MockTransformer)

    transformer = registry.get("mock")
    assert transformer.name == "mock"


def test_registry_get_unknown_raises():
    """Registry should raise KeyError for unknown transformer."""
    registry = TransformerRegistry()
    with pytest.raises(KeyError, match="Unknown transformer: 'unknown'"):
        registry.get("unknown")


def test_registry_list_all():
    """Registry should list all registered transformer names."""
    registry = TransformerRegistry()
    registry.register(MockTransformer)

    names = registry.list_all()
    assert "mock" in names
