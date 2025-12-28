from pathlib import Path
import pytest
from murmur.graph import load_graph, validate_graph, GraphValidationError
from murmur.registry import TransformerRegistry
from murmur.core import Transformer, TransformerIO


FIXTURES = Path(__file__).parent.parent / "fixtures"


class EchoTransformer(Transformer):
    name = "echo"
    inputs = ["message"]
    outputs = ["echoed"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        return TransformerIO(data={"echoed": input.data["message"]})


def make_registry():
    registry = TransformerRegistry()
    registry.register(EchoTransformer)
    return registry


def test_load_graph_from_yaml():
    """load_graph should parse YAML and return graph dict."""
    graph = load_graph(FIXTURES / "graphs" / "simple.yaml")
    assert graph["name"] == "simple-test"
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["name"] == "echo"
    assert graph["nodes"][0]["transformer"] == "echo"
    assert graph["nodes"][0]["inputs"]["message"] == "$config.greeting"


def test_validate_graph_success():
    """validate_graph should pass for valid graph."""
    graph = load_graph(FIXTURES / "graphs" / "simple.yaml")
    registry = make_registry()
    # Should not raise
    validate_graph(graph, registry)


def test_validate_graph_unknown_transformer():
    """validate_graph should fail for unknown transformer."""
    graph = load_graph(FIXTURES / "graphs" / "invalid_transformer.yaml")
    registry = make_registry()
    with pytest.raises(GraphValidationError, match="Unknown transformer: 'nonexistent'"):
        validate_graph(graph, registry)


def test_validate_graph_invalid_wiring():
    """validate_graph should fail for reference to non-existent node."""
    graph = load_graph(FIXTURES / "graphs" / "invalid_wiring.yaml")
    registry = make_registry()
    with pytest.raises(GraphValidationError, match="references unknown node 'step0'"):
        validate_graph(graph, registry)


def test_validate_graph_circular_dependency():
    """validate_graph should fail for circular dependencies."""
    graph = load_graph(FIXTURES / "graphs" / "circular.yaml")
    registry = make_registry()
    with pytest.raises(GraphValidationError, match="Circular dependency"):
        validate_graph(graph, registry)
