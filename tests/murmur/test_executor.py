from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.registry import TransformerRegistry
from murmur.executor import GraphExecutor, topological_sort


class AddOneTransformer(Transformer):
    name = "add-one"
    inputs = ["value"]
    outputs = ["result"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        value = input.data.get("value", 0)
        return TransformerIO(data={"result": value + 1})


class DoubleTransformer(Transformer):
    name = "double"
    inputs = ["value"]
    outputs = ["result"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        value = input.data.get("value", 0)
        return TransformerIO(data={"result": value * 2})


def test_executor_runs_single_node():
    """Executor should run a single node with config input."""
    registry = TransformerRegistry()
    registry.register(AddOneTransformer)

    graph = {
        "name": "test",
        "nodes": [
            {
                "name": "step1",
                "transformer": "add-one",
                "inputs": {"value": "$config.start"},
            }
        ]
    }
    config = {"start": 5}

    executor = GraphExecutor(graph, registry)
    result = executor.execute(config)

    assert result.data["step1"]["result"] == 6


def test_executor_runs_chain():
    """Executor should run nodes in dependency order."""
    registry = TransformerRegistry()
    registry.register(AddOneTransformer)
    registry.register(DoubleTransformer)

    graph = {
        "name": "test",
        "nodes": [
            {
                "name": "add",
                "transformer": "add-one",
                "inputs": {"value": "$config.start"},
            },
            {
                "name": "double",
                "transformer": "double",
                "inputs": {"value": "$add.result"},
            }
        ]
    }
    config = {"start": 5}

    executor = GraphExecutor(graph, registry)
    result = executor.execute(config)

    # (5 + 1) * 2 = 12
    assert result.data["double"]["result"] == 12


def test_topological_sort_simple_chain():
    """topological_sort should order nodes by dependencies."""
    deps = {
        "c": {"b"},
        "b": {"a"},
        "a": set(),
    }
    order = topological_sort(deps)
    assert order.index("a") < order.index("b")
    assert order.index("b") < order.index("c")


def test_topological_sort_parallel_nodes():
    """topological_sort should handle independent nodes."""
    deps = {
        "merge": {"a", "b"},
        "a": set(),
        "b": set(),
    }
    order = topological_sort(deps)
    assert order.index("a") < order.index("merge")
    assert order.index("b") < order.index("merge")
