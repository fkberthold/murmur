# Murmur v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a working news briefing pipeline that gathers news, plans a narrative, generates a script, and synthesizes audio via Piper TTS.

**Architecture:** Python graph executor runs YAML-defined transformer pipelines. Each transformer declares inputs/outputs validated at load time. Claude subprocess (`claude --print`) handles intelligence; Piper handles TTS.

**Tech Stack:** Python 3.11+, Typer (CLI), PyYAML, Piper TTS, pytest

---

## Phase 1: Project Foundation

### Task 1: Create pyproject.toml

**Files:**
- Create: `pyproject.toml`

**Step 1: Write pyproject.toml**

```toml
[project]
name = "murmur"
version = "0.1.0"
description = "A personal intelligence briefing system"
requires-python = ">=3.11"
dependencies = [
    "typer>=0.9.0",
    "rich>=13.0.0",
    "pyyaml>=6.0",
]

[project.optional-dependencies]
tts = ["piper-tts>=1.2.0", "numpy>=1.24.0"]
dev = ["pytest>=7.0.0", "pytest-cov>=4.0.0"]

[project.scripts]
murmur = "murmur.cli:app"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["src"]
```

**Step 2: Create package structure**

```bash
mkdir -p src/murmur/transformers src/murmur/lib tests/murmur
touch src/murmur/__init__.py
touch src/murmur/transformers/__init__.py
touch src/murmur/lib/__init__.py
touch tests/__init__.py
touch tests/murmur/__init__.py
```

**Step 3: Install in dev mode**

Run: `pip install -e ".[dev]"`
Expected: Successfully installed murmur

**Step 4: Commit**

```bash
git add pyproject.toml src/ tests/
git commit -m "feat: initialize project structure with pyproject.toml"
```

---

### Task 2: Core Data Classes

**Files:**
- Create: `src/murmur/core.py`
- Test: `tests/murmur/test_core.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_core.py
from pathlib import Path
from murmur.core import TransformerIO


def test_transformer_io_defaults():
    """TransformerIO should initialize with empty defaults."""
    io = TransformerIO()
    assert io.data == {}
    assert io.artifacts == {}


def test_transformer_io_with_data():
    """TransformerIO should accept data and artifacts."""
    io = TransformerIO(
        data={"key": "value"},
        artifacts={"audio": Path("/tmp/test.mp3")}
    )
    assert io.data["key"] == "value"
    assert io.artifacts["audio"] == Path("/tmp/test.mp3")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_core.py -v`
Expected: FAIL with "No module named 'murmur.core'"

**Step 3: Write minimal implementation**

```python
# src/murmur/core.py
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class TransformerIO:
    """Universal I/O container for all transformers."""
    data: dict = field(default_factory=dict)
    artifacts: dict[str, Path] = field(default_factory=dict)
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_core.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/core.py tests/murmur/test_core.py
git commit -m "feat: add TransformerIO data class"
```

---

### Task 3: Transformer Base Class

**Files:**
- Modify: `src/murmur/core.py`
- Modify: `tests/murmur/test_core.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_core.py (append)
from murmur.core import Transformer, TransformerIO


class EchoTransformer(Transformer):
    """Test transformer that echoes input to output."""
    name = "echo"
    inputs = ["message"]
    outputs = ["echoed"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        return TransformerIO(
            data={"echoed": input.data.get("message", "")},
            artifacts=input.artifacts
        )


def test_transformer_has_required_attributes():
    """Transformer subclass should have name, inputs, outputs, effects."""
    t = EchoTransformer()
    assert t.name == "echo"
    assert t.inputs == ["message"]
    assert t.outputs == ["echoed"]
    assert t.input_effects == []
    assert t.output_effects == []


def test_transformer_process():
    """Transformer.process should transform input to output."""
    t = EchoTransformer()
    result = t.process(TransformerIO(data={"message": "hello"}))
    assert result.data["echoed"] == "hello"
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_core.py::test_transformer_has_required_attributes -v`
Expected: FAIL with "cannot import name 'Transformer'"

**Step 3: Write minimal implementation**

```python
# src/murmur/core.py (append after TransformerIO)

class Transformer(ABC):
    """
    Base class for all graph nodes.

    Subclasses must define:
    - name: str - unique identifier
    - inputs: list[str] - required input keys
    - outputs: list[str] - produced output keys
    - input_effects: list[str] - side effects consumed (e.g., ["llm", "http"])
    - output_effects: list[str] - side effects produced (e.g., ["filesystem", "tts"])
    """
    name: str
    inputs: list[str] = []
    outputs: list[str] = []
    input_effects: list[str] = []
    output_effects: list[str] = []

    @abstractmethod
    def process(self, input: TransformerIO) -> TransformerIO:
        """Transform input to output."""
        pass
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_core.py -v`
Expected: PASS (all tests)

**Step 5: Commit**

```bash
git add src/murmur/core.py tests/murmur/test_core.py
git commit -m "feat: add Transformer abstract base class"
```

---

## Phase 2: Graph Loading and Validation

### Task 4: Graph Config Loading

**Files:**
- Create: `src/murmur/graph.py`
- Create: `tests/murmur/test_graph.py`
- Create: `tests/fixtures/graphs/simple.yaml`

**Step 1: Create test fixture**

```yaml
# tests/fixtures/graphs/simple.yaml
name: simple-test

nodes:
  - name: echo
    transformer: echo
    inputs:
      message: $config.greeting
```

**Step 2: Write the failing test**

```python
# tests/murmur/test_graph.py
from pathlib import Path
from murmur.graph import load_graph


FIXTURES = Path(__file__).parent.parent / "fixtures"


def test_load_graph_from_yaml():
    """load_graph should parse YAML and return graph dict."""
    graph = load_graph(FIXTURES / "graphs" / "simple.yaml")
    assert graph["name"] == "simple-test"
    assert len(graph["nodes"]) == 1
    assert graph["nodes"][0]["name"] == "echo"
    assert graph["nodes"][0]["transformer"] == "echo"
    assert graph["nodes"][0]["inputs"]["message"] == "$config.greeting"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/test_graph.py -v`
Expected: FAIL with "No module named 'murmur.graph'"

**Step 4: Write minimal implementation**

```python
# src/murmur/graph.py
from pathlib import Path
import yaml


def load_graph(path: Path) -> dict:
    """Load a graph definition from a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/test_graph.py -v`
Expected: PASS

**Step 6: Commit**

```bash
mkdir -p tests/fixtures/graphs
git add src/murmur/graph.py tests/murmur/test_graph.py tests/fixtures/graphs/simple.yaml
git commit -m "feat: add graph YAML loading"
```

---

### Task 5: Transformer Registry

**Files:**
- Create: `src/murmur/registry.py`
- Create: `tests/murmur/test_registry.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_registry.py
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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_registry.py -v`
Expected: FAIL with "No module named 'murmur.registry'"

**Step 3: Write minimal implementation**

```python
# src/murmur/registry.py
from typing import Type
from murmur.core import Transformer


class TransformerRegistry:
    """Registry for transformer classes."""

    def __init__(self):
        self._transformers: dict[str, Transformer] = {}

    def register(self, transformer_class: Type[Transformer]) -> None:
        """Register a transformer class."""
        instance = transformer_class()
        self._transformers[instance.name] = instance

    def get(self, name: str) -> Transformer:
        """Get a transformer by name."""
        if name not in self._transformers:
            raise KeyError(f"Unknown transformer: '{name}'")
        return self._transformers[name]

    def list_all(self) -> list[str]:
        """List all registered transformer names."""
        return list(self._transformers.keys())
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_registry.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/registry.py tests/murmur/test_registry.py
git commit -m "feat: add TransformerRegistry"
```

---

### Task 6: Graph Validation

**Files:**
- Modify: `src/murmur/graph.py`
- Modify: `tests/murmur/test_graph.py`
- Create: `tests/fixtures/graphs/invalid_transformer.yaml`
- Create: `tests/fixtures/graphs/invalid_wiring.yaml`

**Step 1: Create test fixtures**

```yaml
# tests/fixtures/graphs/invalid_transformer.yaml
name: invalid-transformer
nodes:
  - name: step1
    transformer: nonexistent
    inputs: {}
```

```yaml
# tests/fixtures/graphs/invalid_wiring.yaml
name: invalid-wiring
nodes:
  - name: step1
    transformer: echo
    inputs:
      message: $step0.missing_output
```

**Step 2: Write the failing tests**

```python
# tests/murmur/test_graph.py (append)
import pytest
from murmur.graph import load_graph, validate_graph, GraphValidationError
from murmur.registry import TransformerRegistry
from murmur.core import Transformer, TransformerIO


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
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/test_graph.py::test_validate_graph_success -v`
Expected: FAIL with "cannot import name 'validate_graph'"

**Step 4: Write minimal implementation**

```python
# src/murmur/graph.py (replace entire file)
from pathlib import Path
from typing import TYPE_CHECKING
import yaml

if TYPE_CHECKING:
    from murmur.registry import TransformerRegistry


class GraphValidationError(Exception):
    """Raised when graph validation fails."""
    pass


def load_graph(path: Path) -> dict:
    """Load a graph definition from a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)


def validate_graph(graph: dict, registry: "TransformerRegistry") -> None:
    """
    Validate a graph definition against a transformer registry.

    Checks:
    - All referenced transformers exist
    - All node references ($node.output) point to valid nodes
    - Referenced outputs exist on the source transformer
    """
    nodes = {node["name"]: node for node in graph.get("nodes", [])}

    for node in graph.get("nodes", []):
        node_name = node["name"]
        transformer_name = node["transformer"]

        # Check transformer exists
        try:
            transformer = registry.get(transformer_name)
        except KeyError:
            raise GraphValidationError(
                f"Node '{node_name}': Unknown transformer: '{transformer_name}'"
            )

        # Check input wiring
        for input_key, source in node.get("inputs", {}).items():
            if not isinstance(source, str):
                continue
            if not source.startswith("$"):
                continue
            if source.startswith("$config."):
                continue  # Config references validated separately

            # Parse $node.output reference
            parts = source[1:].split(".", 1)
            if len(parts) != 2:
                raise GraphValidationError(
                    f"Node '{node_name}': Invalid reference format: '{source}'"
                )

            source_node, source_output = parts

            # Check source node exists
            if source_node not in nodes:
                raise GraphValidationError(
                    f"Node '{node_name}': Input '{input_key}' references unknown node '{source_node}'"
                )

            # Check source output exists on transformer
            source_transformer_name = nodes[source_node]["transformer"]
            source_transformer = registry.get(source_transformer_name)
            if source_output not in source_transformer.outputs:
                raise GraphValidationError(
                    f"Node '{node_name}': Input '{input_key}' references output '{source_output}' "
                    f"but transformer '{source_transformer_name}' only outputs: {source_transformer.outputs}"
                )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/test_graph.py -v`
Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/murmur/graph.py tests/murmur/test_graph.py tests/fixtures/graphs/
git commit -m "feat: add graph validation with wiring checks"
```

---

### Task 7: Detect Circular Dependencies

**Files:**
- Modify: `src/murmur/graph.py`
- Modify: `tests/murmur/test_graph.py`
- Create: `tests/fixtures/graphs/circular.yaml`

**Step 1: Create test fixture**

```yaml
# tests/fixtures/graphs/circular.yaml
name: circular
nodes:
  - name: a
    transformer: echo
    inputs:
      message: $b.echoed
  - name: b
    transformer: echo
    inputs:
      message: $a.echoed
```

**Step 2: Write the failing test**

```python
# tests/murmur/test_graph.py (append)

def test_validate_graph_circular_dependency():
    """validate_graph should fail for circular dependencies."""
    graph = load_graph(FIXTURES / "graphs" / "circular.yaml")
    registry = make_registry()
    with pytest.raises(GraphValidationError, match="Circular dependency"):
        validate_graph(graph, registry)
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/test_graph.py::test_validate_graph_circular_dependency -v`
Expected: FAIL (no exception raised, or wrong exception)

**Step 4: Add cycle detection to validate_graph**

```python
# src/murmur/graph.py - add this function before validate_graph

def _build_dependency_graph(graph: dict) -> dict[str, set[str]]:
    """Build adjacency list of node dependencies."""
    deps: dict[str, set[str]] = {}
    for node in graph.get("nodes", []):
        node_name = node["name"]
        deps[node_name] = set()
        for source in node.get("inputs", {}).values():
            if isinstance(source, str) and source.startswith("$") and not source.startswith("$config."):
                parts = source[1:].split(".", 1)
                if len(parts) == 2:
                    deps[node_name].add(parts[0])
    return deps


def _detect_cycle(deps: dict[str, set[str]]) -> list[str] | None:
    """Detect cycle using DFS. Returns cycle path if found, None otherwise."""
    WHITE, GRAY, BLACK = 0, 1, 2
    color = {node: WHITE for node in deps}
    path = []

    def dfs(node: str) -> list[str] | None:
        color[node] = GRAY
        path.append(node)
        for neighbor in deps.get(node, set()):
            if neighbor not in color:
                continue
            if color[neighbor] == GRAY:
                cycle_start = path.index(neighbor)
                return path[cycle_start:] + [neighbor]
            if color[neighbor] == WHITE:
                result = dfs(neighbor)
                if result:
                    return result
        color[node] = BLACK
        path.pop()
        return None

    for node in deps:
        if color[node] == WHITE:
            cycle = dfs(node)
            if cycle:
                return cycle
    return None
```

```python
# src/murmur/graph.py - add to end of validate_graph function, before final return

    # Check for circular dependencies
    deps = _build_dependency_graph(graph)
    cycle = _detect_cycle(deps)
    if cycle:
        cycle_str = " -> ".join(cycle)
        raise GraphValidationError(f"Circular dependency detected: {cycle_str}")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/test_graph.py -v`
Expected: PASS (all tests)

**Step 6: Commit**

```bash
git add src/murmur/graph.py tests/murmur/test_graph.py tests/fixtures/graphs/circular.yaml
git commit -m "feat: detect circular dependencies in graph validation"
```

---

## Phase 3: Graph Executor

### Task 8: Topological Sort

**Files:**
- Create: `src/murmur/executor.py`
- Create: `tests/murmur/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_executor.py
from murmur.executor import topological_sort


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_executor.py -v`
Expected: FAIL with "No module named 'murmur.executor'"

**Step 3: Write minimal implementation**

```python
# src/murmur/executor.py
from murmur.graph import _build_dependency_graph


def topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """
    Return nodes in topological order (dependencies before dependents).
    Assumes no cycles (validate_graph checks this).
    """
    in_degree = {node: 0 for node in deps}
    for node, neighbors in deps.items():
        for neighbor in neighbors:
            if neighbor in in_degree:
                pass  # neighbor is a dependency, not a dependent

    # Calculate in-degrees (how many nodes depend on each node)
    reverse_deps: dict[str, set[str]] = {node: set() for node in deps}
    for node, dependencies in deps.items():
        for dep in dependencies:
            if dep in reverse_deps:
                reverse_deps[dep].add(node)

    in_degree = {node: len(dependencies) for node, dependencies in deps.items()}

    # Kahn's algorithm
    queue = [node for node, degree in in_degree.items() if degree == 0]
    result = []

    while queue:
        node = queue.pop(0)
        result.append(node)
        for dependent in reverse_deps[node]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    return result
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/executor.py tests/murmur/test_executor.py
git commit -m "feat: add topological sort for execution ordering"
```

---

### Task 9: Graph Executor Basic Execution

**Files:**
- Modify: `src/murmur/executor.py`
- Modify: `tests/murmur/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_executor.py (append)
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.registry import TransformerRegistry
from murmur.executor import GraphExecutor


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
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_executor.py::test_executor_runs_single_node -v`
Expected: FAIL with "cannot import name 'GraphExecutor'"

**Step 3: Write minimal implementation**

```python
# src/murmur/executor.py (add to file)
from pathlib import Path
from typing import Any
from murmur.core import TransformerIO
from murmur.registry import TransformerRegistry
from murmur.graph import _build_dependency_graph, validate_graph


class GraphExecutor:
    """Executes a transformer graph."""

    def __init__(self, graph: dict, registry: TransformerRegistry):
        self.graph = graph
        self.registry = registry
        self.nodes = {node["name"]: node for node in graph.get("nodes", [])}

        # Validate at construction time
        validate_graph(graph, registry)

    def execute(self, config: dict) -> TransformerIO:
        """Execute the graph and return final state."""
        deps = _build_dependency_graph(self.graph)
        execution_order = topological_sort(deps)

        # Store outputs from each node
        node_outputs: dict[str, dict] = {}
        all_artifacts: dict[str, Path] = {}

        for node_name in execution_order:
            node = self.nodes[node_name]
            transformer = self.registry.get(node["transformer"])

            # Resolve inputs
            resolved_inputs = {}
            for input_key, source in node.get("inputs", {}).items():
                resolved_inputs[input_key] = self._resolve_reference(
                    source, config, node_outputs
                )

            # Execute transformer
            input_io = TransformerIO(data=resolved_inputs)
            output_io = transformer.process(input_io)

            # Store outputs
            node_outputs[node_name] = output_io.data
            all_artifacts.update(output_io.artifacts)

        return TransformerIO(data=node_outputs, artifacts=all_artifacts)

    def _resolve_reference(
        self, source: Any, config: dict, node_outputs: dict[str, dict]
    ) -> Any:
        """Resolve a $config.x or $node.output reference."""
        if not isinstance(source, str) or not source.startswith("$"):
            return source

        ref = source[1:]  # Remove $

        if ref.startswith("config."):
            key = ref[7:]  # Remove "config."
            return config.get(key)

        # Node reference: $node.output
        parts = ref.split(".", 1)
        if len(parts) == 2:
            node_name, output_key = parts
            return node_outputs.get(node_name, {}).get(output_key)

        return source  # Return as-is if can't resolve
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/executor.py tests/murmur/test_executor.py
git commit -m "feat: add GraphExecutor with config and node reference resolution"
```

---

### Task 10: Artifact Saving

**Files:**
- Modify: `src/murmur/executor.py`
- Modify: `tests/murmur/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_executor.py (append)
import tempfile


class FileWriterTransformer(Transformer):
    name = "file-writer"
    inputs = ["content"]
    outputs = ["written"]
    input_effects = []
    output_effects = ["filesystem"]

    def process(self, input: TransformerIO) -> TransformerIO:
        # Simulate writing a file
        return TransformerIO(
            data={"written": True},
            artifacts={"output": Path("/tmp/fake-output.txt")}
        )


def test_executor_saves_intermediate_artifacts(tmp_path):
    """Executor should save node outputs to artifact directory."""
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

    executor = GraphExecutor(graph, registry, artifact_dir=tmp_path)
    result = executor.execute(config)

    # Check artifact was saved
    artifacts = list(tmp_path.glob("*_step1.json"))
    assert len(artifacts) == 1
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_executor.py::test_executor_saves_intermediate_artifacts -v`
Expected: FAIL (TypeError about artifact_dir parameter)

**Step 3: Update implementation**

```python
# src/murmur/executor.py - update GraphExecutor.__init__ and execute
import json
from datetime import datetime


class GraphExecutor:
    """Executes a transformer graph."""

    def __init__(
        self,
        graph: dict,
        registry: TransformerRegistry,
        artifact_dir: Path | None = None
    ):
        self.graph = graph
        self.registry = registry
        self.nodes = {node["name"]: node for node in graph.get("nodes", [])}
        self.artifact_dir = artifact_dir
        self.run_id = datetime.now().strftime("%Y%m%d_%H%M%S")

        # Validate at construction time
        validate_graph(graph, registry)

    def execute(self, config: dict) -> TransformerIO:
        """Execute the graph and return final state."""
        deps = _build_dependency_graph(self.graph)
        execution_order = topological_sort(deps)

        # Store outputs from each node
        node_outputs: dict[str, dict] = {}
        all_artifacts: dict[str, Path] = {}

        for node_name in execution_order:
            node = self.nodes[node_name]
            transformer = self.registry.get(node["transformer"])

            # Resolve inputs
            resolved_inputs = {}
            for input_key, source in node.get("inputs", {}).items():
                resolved_inputs[input_key] = self._resolve_reference(
                    source, config, node_outputs
                )

            # Execute transformer
            input_io = TransformerIO(data=resolved_inputs)
            output_io = transformer.process(input_io)

            # Store outputs
            node_outputs[node_name] = output_io.data
            all_artifacts.update(output_io.artifacts)

            # Save intermediate artifact
            self._save_artifact(node_name, output_io.data)

        return TransformerIO(data=node_outputs, artifacts=all_artifacts)

    def _save_artifact(self, node_name: str, data: dict) -> None:
        """Save node output to artifact directory."""
        if self.artifact_dir is None:
            return

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.artifact_dir / f"{self.run_id}_{node_name}.json"
        with open(artifact_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _resolve_reference(
        self, source: Any, config: dict, node_outputs: dict[str, dict]
    ) -> Any:
        """Resolve a $config.x or $node.output reference."""
        if not isinstance(source, str) or not source.startswith("$"):
            return source

        ref = source[1:]  # Remove $

        if ref.startswith("config."):
            key = ref[7:]  # Remove "config."
            return config.get(key)

        # Node reference: $node.output
        parts = ref.split(".", 1)
        if len(parts) == 2:
            node_name, output_key = parts
            return node_outputs.get(node_name, {}).get(output_key)

        return source  # Return as-is if can't resolve
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/executor.py tests/murmur/test_executor.py
git commit -m "feat: save intermediate artifacts during graph execution"
```

---

### Task 11: Load Cached Artifacts

**Files:**
- Modify: `src/murmur/executor.py`
- Modify: `tests/murmur/test_executor.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_executor.py (append)

def test_executor_uses_cached_nodes(tmp_path):
    """Executor should load cached outputs instead of running transformer."""
    registry = TransformerRegistry()
    registry.register(AddOneTransformer)
    registry.register(DoubleTransformer)

    # Pre-create cached artifact
    run_id = "20241227_120000"
    cached_file = tmp_path / f"{run_id}_add.json"
    cached_file.write_text('{"result": 100}')  # Fake cached value

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

    executor = GraphExecutor(
        graph, registry,
        artifact_dir=tmp_path,
        cached_nodes=["add"],
        run_id=run_id
    )
    result = executor.execute(config)

    # Should use cached value (100) not computed (6)
    # 100 * 2 = 200
    assert result.data["double"]["result"] == 200
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_executor.py::test_executor_uses_cached_nodes -v`
Expected: FAIL (TypeError about cached_nodes parameter)

**Step 3: Update implementation**

```python
# src/murmur/executor.py - update GraphExecutor class

class GraphExecutor:
    """Executes a transformer graph."""

    def __init__(
        self,
        graph: dict,
        registry: TransformerRegistry,
        artifact_dir: Path | None = None,
        cached_nodes: list[str] | None = None,
        run_id: str | None = None,
    ):
        self.graph = graph
        self.registry = registry
        self.nodes = {node["name"]: node for node in graph.get("nodes", [])}
        self.artifact_dir = artifact_dir
        self.cached_nodes = set(cached_nodes or [])
        self.run_id = run_id or datetime.now().strftime("%Y%m%d_%H%M%S")

        # Validate at construction time
        validate_graph(graph, registry)

    def execute(self, config: dict) -> TransformerIO:
        """Execute the graph and return final state."""
        deps = _build_dependency_graph(self.graph)
        execution_order = topological_sort(deps)

        # Store outputs from each node
        node_outputs: dict[str, dict] = {}
        all_artifacts: dict[str, Path] = {}

        for node_name in execution_order:
            # Try to load from cache
            if node_name in self.cached_nodes:
                cached_data = self._load_cached_artifact(node_name)
                if cached_data is not None:
                    node_outputs[node_name] = cached_data
                    continue

            node = self.nodes[node_name]
            transformer = self.registry.get(node["transformer"])

            # Resolve inputs
            resolved_inputs = {}
            for input_key, source in node.get("inputs", {}).items():
                resolved_inputs[input_key] = self._resolve_reference(
                    source, config, node_outputs
                )

            # Execute transformer
            input_io = TransformerIO(data=resolved_inputs)
            output_io = transformer.process(input_io)

            # Store outputs
            node_outputs[node_name] = output_io.data
            all_artifacts.update(output_io.artifacts)

            # Save intermediate artifact
            self._save_artifact(node_name, output_io.data)

        return TransformerIO(data=node_outputs, artifacts=all_artifacts)

    def _load_cached_artifact(self, node_name: str) -> dict | None:
        """Load cached node output if it exists."""
        if self.artifact_dir is None:
            return None

        artifact_path = self.artifact_dir / f"{self.run_id}_{node_name}.json"
        if not artifact_path.exists():
            return None

        with open(artifact_path) as f:
            return json.load(f)

    def _save_artifact(self, node_name: str, data: dict) -> None:
        """Save node output to artifact directory."""
        if self.artifact_dir is None:
            return

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.artifact_dir / f"{self.run_id}_{node_name}.json"
        with open(artifact_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _resolve_reference(
        self, source: Any, config: dict, node_outputs: dict[str, dict]
    ) -> Any:
        """Resolve a $config.x or $node.output reference."""
        if not isinstance(source, str) or not source.startswith("$"):
            return source

        ref = source[1:]  # Remove $

        if ref.startswith("config."):
            key = ref[7:]  # Remove "config."
            return config.get(key)

        # Node reference: $node.output
        parts = ref.split(".", 1)
        if len(parts) == 2:
            node_name, output_key = parts
            return node_outputs.get(node_name, {}).get(output_key)

        return source  # Return as-is if can't resolve
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_executor.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/executor.py tests/murmur/test_executor.py
git commit -m "feat: support cached node outputs in executor"
```

---

## Phase 4: Claude Integration

### Task 12: Claude Subprocess Wrapper

**Files:**
- Create: `src/murmur/claude.py`
- Create: `tests/murmur/test_claude.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_claude.py
import pytest
from unittest.mock import patch, MagicMock
from murmur.claude import run_claude, ClaudeError


def test_run_claude_returns_stdout():
    """run_claude should return stdout from subprocess."""
    mock_result = MagicMock()
    mock_result.returncode = 0
    mock_result.stdout = "Hello from Claude"
    mock_result.stderr = ""

    with patch("subprocess.run", return_value=mock_result) as mock_run:
        result = run_claude("Say hello")
        assert result == "Hello from Claude"

        # Verify subprocess was called correctly
        call_args = mock_run.call_args
        assert "claude" in call_args[0][0]
        assert "--print" in call_args[0][0]


def test_run_claude_raises_on_failure():
    """run_claude should raise ClaudeError on non-zero exit."""
    mock_result = MagicMock()
    mock_result.returncode = 1
    mock_result.stdout = ""
    mock_result.stderr = "Error message"

    with patch("subprocess.run", return_value=mock_result):
        with pytest.raises(ClaudeError, match="Error message"):
            run_claude("Bad prompt")
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_claude.py -v`
Expected: FAIL with "No module named 'murmur.claude'"

**Step 3: Write minimal implementation**

```python
# src/murmur/claude.py
import subprocess
from pathlib import Path


class ClaudeError(Exception):
    """Raised when Claude subprocess fails."""
    pass


def run_claude(
    prompt: str,
    allowed_tools: list[str] | None = None,
    cwd: Path | None = None,
    timeout: int = 600,
) -> str:
    """
    Run Claude CLI in headless mode and return response.

    Args:
        prompt: The prompt to send to Claude
        allowed_tools: Optional list of tools to allow (e.g., ["WebSearch"])
        cwd: Working directory for subprocess
        timeout: Timeout in seconds (default 10 minutes)

    Returns:
        Claude's response text

    Raises:
        ClaudeError: If subprocess fails
    """
    cmd = ["claude", "--print", "--dangerously-skip-permissions"]

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise ClaudeError(result.stderr or f"Claude exited with code {result.returncode}")

    return result.stdout
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_claude.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/claude.py tests/murmur/test_claude.py
git commit -m "feat: add Claude subprocess wrapper"
```

---

## Phase 5: Transformers

### Task 13: News Fetcher Transformer

**Files:**
- Create: `src/murmur/transformers/news_fetcher.py`
- Create: `tests/murmur/transformers/__init__.py`
- Create: `tests/murmur/transformers/test_news_fetcher.py`
- Create: `prompts/gather.md`

**Step 1: Create gather prompt**

```markdown
# prompts/gather.md
You are a news researcher. Your job is to find current, relevant news based on the provided topics.

## Topics to Research

{{topics}}

## Instructions

1. For each topic, use web search to find 3-5 recent, relevant news items
2. Focus on factual, newsworthy content from reputable sources
3. Include the headline, source, and a brief summary for each item

## Output Format

Return a JSON object with this structure:

```json
{
  "items": [
    {
      "topic": "topic name",
      "headline": "Article headline",
      "source": "Publication name",
      "summary": "2-3 sentence summary of the key facts",
      "url": "source url if available"
    }
  ],
  "gathered_at": "ISO timestamp"
}
```

Return ONLY the JSON object, no other text.
```

**Step 2: Write the failing test**

```python
# tests/murmur/transformers/test_news_fetcher.py
import json
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.news_fetcher import NewsFetcher


def test_news_fetcher_has_correct_metadata():
    """NewsFetcher should declare correct inputs/outputs/effects."""
    fetcher = NewsFetcher()
    assert fetcher.name == "news-fetcher"
    assert fetcher.inputs == ["topics"]
    assert fetcher.outputs == ["gathered_data"]
    assert "llm" in fetcher.input_effects


def test_news_fetcher_calls_claude():
    """NewsFetcher should call Claude with topics and return parsed JSON."""
    mock_response = json.dumps({
        "items": [
            {
                "topic": "AI",
                "headline": "New AI breakthrough",
                "source": "Tech News",
                "summary": "Researchers announced a new model.",
                "url": "https://example.com/ai"
            }
        ],
        "gathered_at": "2024-12-27T10:00:00Z"
    })

    with patch("murmur.transformers.news_fetcher.run_claude", return_value=mock_response):
        fetcher = NewsFetcher()
        input_io = TransformerIO(data={
            "topics": [
                {"name": "AI", "query": "artificial intelligence news", "priority": "high"}
            ]
        })

        result = fetcher.process(input_io)

        assert "gathered_data" in result.data
        assert len(result.data["gathered_data"]["items"]) == 1
        assert result.data["gathered_data"]["items"][0]["headline"] == "New AI breakthrough"
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/transformers/test_news_fetcher.py -v`
Expected: FAIL with "No module named 'murmur.transformers.news_fetcher'"

**Step 4: Write minimal implementation**

```python
# src/murmur/transformers/news_fetcher.py
import json
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "gather.md"


class NewsFetcher(Transformer):
    """Fetches news using Claude's web search capability."""

    name = "news-fetcher"
    inputs = ["topics"]
    outputs = ["gathered_data"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        topics = input.data.get("topics", [])

        # Format topics for prompt
        topics_text = "\n".join(
            f"- **{t['name']}** (priority: {t.get('priority', 'medium')}): {t['query']}"
            for t in topics
        )

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{topics}}", topics_text)

        # Call Claude with web search
        response = run_claude(prompt, allowed_tools=["WebSearch"])

        # Parse JSON response
        gathered_data = json.loads(response)

        return TransformerIO(data={"gathered_data": gathered_data})
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/transformers/test_news_fetcher.py -v`
Expected: PASS

**Step 6: Commit**

```bash
mkdir -p prompts tests/murmur/transformers
touch tests/murmur/transformers/__init__.py
git add src/murmur/transformers/news_fetcher.py tests/murmur/transformers/ prompts/gather.md
git commit -m "feat: add NewsFetcher transformer"
```

---

### Task 14: Brief Planner Transformer

**Files:**
- Create: `src/murmur/transformers/brief_planner.py`
- Create: `tests/murmur/transformers/test_brief_planner.py`
- Create: `prompts/plan.md`

**Step 1: Create plan prompt**

```markdown
# prompts/plan.md
You are a briefing planner. Your job is to select and organize news items into a coherent narrative for a spoken briefing.

## Available News Items

{{gathered_data}}

## Instructions

1. Select the most important and relevant items (aim for 5-8 items)
2. Group related items together
3. Order them for natural flow (e.g., most important first, or thematic grouping)
4. Note any connections between items
5. Suggest transitions between sections

## Output Format

Return a JSON object with this structure:

```json
{
  "sections": [
    {
      "title": "Section name",
      "items": ["headline1", "headline2"],
      "connection": "How these items relate",
      "transition_to_next": "Suggested transition phrase"
    }
  ],
  "total_items": 5,
  "estimated_duration_minutes": 8
}
```

Return ONLY the JSON object, no other text.
```

**Step 2: Write the failing test**

```python
# tests/murmur/transformers/test_brief_planner.py
import json
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.brief_planner import BriefPlanner


def test_brief_planner_has_correct_metadata():
    """BriefPlanner should declare correct inputs/outputs/effects."""
    planner = BriefPlanner()
    assert planner.name == "brief-planner"
    assert planner.inputs == ["gathered_data"]
    assert planner.outputs == ["plan"]
    assert "llm" in planner.input_effects


def test_brief_planner_calls_claude():
    """BriefPlanner should call Claude with gathered data and return plan."""
    mock_response = json.dumps({
        "sections": [
            {
                "title": "AI Developments",
                "items": ["New AI breakthrough"],
                "connection": "Recent advances in AI",
                "transition_to_next": "Speaking of technology..."
            }
        ],
        "total_items": 1,
        "estimated_duration_minutes": 3
    })

    with patch("murmur.transformers.brief_planner.run_claude", return_value=mock_response):
        planner = BriefPlanner()
        input_io = TransformerIO(data={
            "gathered_data": {
                "items": [{"headline": "New AI breakthrough", "summary": "..."}]
            }
        })

        result = planner.process(input_io)

        assert "plan" in result.data
        assert len(result.data["plan"]["sections"]) == 1
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/transformers/test_brief_planner.py -v`
Expected: FAIL with "No module named 'murmur.transformers.brief_planner'"

**Step 4: Write minimal implementation**

```python
# src/murmur/transformers/brief_planner.py
import json
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "plan.md"


class BriefPlanner(Transformer):
    """Plans the narrative structure of a briefing."""

    name = "brief-planner"
    inputs = ["gathered_data"]
    outputs = ["plan"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        gathered_data = input.data.get("gathered_data", {})

        # Format gathered data for prompt
        gathered_text = json.dumps(gathered_data, indent=2)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{gathered_data}}", gathered_text)

        # Call Claude (no tools needed for planning)
        response = run_claude(prompt, allowed_tools=[])

        # Parse JSON response
        plan = json.loads(response)

        return TransformerIO(data={"plan": plan})
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/transformers/test_brief_planner.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/transformers/brief_planner.py tests/murmur/transformers/test_brief_planner.py prompts/plan.md
git commit -m "feat: add BriefPlanner transformer"
```

---

### Task 15: Script Generator Transformer

**Files:**
- Create: `src/murmur/transformers/script_generator.py`
- Create: `tests/murmur/transformers/test_script_generator.py`
- Create: `prompts/generate.md`

**Step 1: Create generate prompt**

```markdown
# prompts/generate.md
You are writing a spoken briefing script. Your output will be read aloud by a text-to-speech system.

## Narrator Style

{{narrator_style}}

## Briefing Plan

{{plan}}

## Original News Data

{{gathered_data}}

## Instructions

Write a natural, conversational script that:

1. Sounds good when read aloud (use contractions, natural phrasing)
2. Uses punctuation to guide pacing (periods for pauses, commas for brief breaks)
3. Avoids jargon and acronyms unless explained
4. Maintains a warm but professional tone
5. Includes natural transitions between topics
6. Is approximately {{target_duration}} minutes when read at 150 words per minute

## Output

Write the script as plain text, ready for text-to-speech. No headers, no markup, just the spoken words.

Start with a brief greeting and end with a sign-off.
```

**Step 2: Write the failing test**

```python
# tests/murmur/transformers/test_script_generator.py
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.script_generator import ScriptGenerator


def test_script_generator_has_correct_metadata():
    """ScriptGenerator should declare correct inputs/outputs/effects."""
    generator = ScriptGenerator()
    assert generator.name == "script-generator"
    assert "plan" in generator.inputs
    assert "gathered_data" in generator.inputs
    assert generator.outputs == ["script"]
    assert "llm" in generator.input_effects


def test_script_generator_calls_claude():
    """ScriptGenerator should call Claude and return script text."""
    mock_response = "Good morning! Here's your briefing for today. First up, exciting news in AI..."

    with patch("murmur.transformers.script_generator.run_claude", return_value=mock_response):
        generator = ScriptGenerator()
        input_io = TransformerIO(data={
            "plan": {"sections": [{"title": "AI", "items": ["headline"]}]},
            "gathered_data": {"items": []},
            "narrator_style": "warm-professional",
            "target_duration": 5
        })

        result = generator.process(input_io)

        assert "script" in result.data
        assert "Good morning" in result.data["script"]
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/transformers/test_script_generator.py -v`
Expected: FAIL with "No module named 'murmur.transformers.script_generator'"

**Step 4: Write minimal implementation**

```python
# src/murmur/transformers/script_generator.py
import json
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "generate.md"

NARRATOR_STYLES = {
    "warm-professional": """
You are a warm but professional assistant, like an NPR morning host.
- Friendly and approachable, but not overly casual
- Clear and informative without being dry
- Occasionally show personality through word choice
- Use "you" to address the listener directly
""",
}


class ScriptGenerator(Transformer):
    """Generates TTS-ready script from a briefing plan."""

    name = "script-generator"
    inputs = ["plan", "gathered_data", "narrator_style", "target_duration"]
    outputs = ["script"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        plan = input.data.get("plan", {})
        gathered_data = input.data.get("gathered_data", {})
        narrator_style = input.data.get("narrator_style", "warm-professional")
        target_duration = input.data.get("target_duration", 5)

        # Get narrator style description
        style_text = NARRATOR_STYLES.get(narrator_style, NARRATOR_STYLES["warm-professional"])

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = (
            prompt_template
            .replace("{{narrator_style}}", style_text)
            .replace("{{plan}}", json.dumps(plan, indent=2))
            .replace("{{gathered_data}}", json.dumps(gathered_data, indent=2))
            .replace("{{target_duration}}", str(target_duration))
        )

        # Call Claude (no tools needed for generation)
        response = run_claude(prompt, allowed_tools=[])

        return TransformerIO(data={"script": response.strip()})
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/transformers/test_script_generator.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/transformers/script_generator.py tests/murmur/transformers/test_script_generator.py prompts/generate.md
git commit -m "feat: add ScriptGenerator transformer"
```

---

### Task 16: Piper Synthesizer Transformer

**Files:**
- Create: `src/murmur/lib/piper.py`
- Create: `src/murmur/transformers/piper_synthesizer.py`
- Create: `tests/murmur/transformers/test_piper_synthesizer.py`

**Step 1: Write the failing test**

```python
# tests/murmur/transformers/test_piper_synthesizer.py
from pathlib import Path
from unittest.mock import patch, MagicMock
from murmur.core import TransformerIO
from murmur.transformers.piper_synthesizer import PiperSynthesizer


def test_piper_synthesizer_has_correct_metadata():
    """PiperSynthesizer should declare correct inputs/outputs/effects."""
    synth = PiperSynthesizer()
    assert synth.name == "piper-synthesizer"
    assert "script" in synth.inputs
    assert synth.outputs == ["audio"]
    assert "tts" in synth.output_effects
    assert "filesystem" in synth.output_effects


def test_piper_synthesizer_creates_audio(tmp_path):
    """PiperSynthesizer should create audio file and return path."""
    mock_voice = MagicMock()
    mock_voice.synthesize.return_value = b"fake audio data"

    with patch("murmur.transformers.piper_synthesizer.synthesize_with_piper") as mock_synth:
        output_path = tmp_path / "test.wav"
        mock_synth.return_value = output_path

        synth = PiperSynthesizer()
        input_io = TransformerIO(data={
            "script": "Hello, this is a test.",
            "piper_model": "en_US-libritts_r-medium",
            "output_dir": str(tmp_path),
        })

        result = synth.process(input_io)

        assert "audio" in result.data
        assert "audio" in result.artifacts
        mock_synth.assert_called_once()
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/transformers/test_piper_synthesizer.py -v`
Expected: FAIL with "No module named 'murmur.transformers.piper_synthesizer'"

**Step 3: Write Piper wrapper**

```python
# src/murmur/lib/piper.py
from pathlib import Path
from datetime import datetime


def synthesize_with_piper(
    text: str,
    model_path: Path,
    output_dir: Path,
    sentence_silence: float = 0.3,
) -> Path:
    """
    Synthesize text to audio using Piper TTS.

    Args:
        text: Text to synthesize
        model_path: Path to Piper .onnx model file
        output_dir: Directory to save output
        sentence_silence: Pause between sentences in seconds

    Returns:
        Path to generated WAV file
    """
    try:
        from piper import PiperVoice
        import wave
        import struct
    except ImportError:
        raise ImportError("piper-tts not installed. Run: pip install piper-tts")

    # Load voice model
    voice = PiperVoice.load(str(model_path))

    # Generate audio
    audio_data = voice.synthesize(text, sentence_silence=sentence_silence)

    # Save to WAV file
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"brief_{timestamp}.wav"

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(voice.config.sample_rate)
        wav_file.writeframes(audio_data)

    return output_path
```

**Step 4: Write synthesizer transformer**

```python
# src/murmur/transformers/piper_synthesizer.py
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.lib.piper import synthesize_with_piper


class PiperSynthesizer(Transformer):
    """Synthesizes script to audio using Piper TTS."""

    name = "piper-synthesizer"
    inputs = ["script", "piper_model", "output_dir"]
    outputs = ["audio"]
    input_effects = []
    output_effects = ["tts", "filesystem"]

    def process(self, input: TransformerIO) -> TransformerIO:
        script = input.data.get("script", "")
        model_name = input.data.get("piper_model", "en_US-libritts_r-medium")
        output_dir = Path(input.data.get("output_dir", "output"))
        sentence_silence = input.data.get("sentence_silence", 0.3)

        # Construct model path
        model_path = Path("models/piper") / f"{model_name}.onnx"

        # Synthesize
        audio_path = synthesize_with_piper(
            text=script,
            model_path=model_path,
            output_dir=output_dir,
            sentence_silence=sentence_silence,
        )

        # Create latest.wav symlink
        latest_path = output_dir / "latest.wav"
        if latest_path.exists():
            latest_path.unlink()
        latest_path.symlink_to(audio_path.name)

        return TransformerIO(
            data={"audio": str(audio_path)},
            artifacts={"audio": audio_path}
        )
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/transformers/test_piper_synthesizer.py -v`
Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/lib/piper.py src/murmur/transformers/piper_synthesizer.py tests/murmur/transformers/test_piper_synthesizer.py
git commit -m "feat: add PiperSynthesizer transformer"
```

---

## Phase 6: CLI

### Task 17: Basic CLI Structure

**Files:**
- Create: `src/murmur/cli.py`
- Create: `tests/murmur/test_cli.py`

**Step 1: Write the failing test**

```python
# tests/murmur/test_cli.py
from typer.testing import CliRunner
from murmur.cli import app

runner = CliRunner()


def test_cli_help():
    """CLI should show help text."""
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "murmur" in result.stdout.lower() or "generate" in result.stdout.lower()


def test_cli_list_transformers():
    """CLI should list available transformers."""
    result = runner.invoke(app, ["list", "transformers"])
    assert result.exit_code == 0
    assert "news-fetcher" in result.stdout
```

**Step 2: Run test to verify it fails**

Run: `pytest tests/murmur/test_cli.py -v`
Expected: FAIL with "No module named 'murmur.cli'" or similar

**Step 3: Write minimal implementation**

```python
# src/murmur/cli.py
import typer
from rich import print as rprint
from murmur.registry import TransformerRegistry
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer

app = typer.Typer(help="Murmur: A personal intelligence briefing system")
list_app = typer.Typer(help="List available resources")
app.add_typer(list_app, name="list")


def get_registry() -> TransformerRegistry:
    """Build and return the transformer registry."""
    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)
    registry.register(ScriptGenerator)
    registry.register(PiperSynthesizer)
    return registry


@list_app.command("transformers")
def list_transformers():
    """List available transformers."""
    registry = get_registry()
    rprint("[bold]Available Transformers:[/bold]\n")
    for name in sorted(registry.list_all()):
        transformer = registry.get(name)
        rprint(f"  [cyan]{name}[/cyan]")
        rprint(f"    inputs:  {transformer.inputs}")
        rprint(f"    outputs: {transformer.outputs}")
        rprint()


@list_app.command("graphs")
def list_graphs():
    """List available graphs."""
    from pathlib import Path
    graphs_dir = Path("config/graphs")
    if not graphs_dir.exists():
        rprint("[yellow]No graphs directory found[/yellow]")
        return

    rprint("[bold]Available Graphs:[/bold]\n")
    for path in sorted(graphs_dir.glob("*.yaml")):
        rprint(f"  [cyan]{path.stem}[/cyan]")


@list_app.command("profiles")
def list_profiles():
    """List available profiles."""
    from pathlib import Path
    profiles_dir = Path("config/profiles")
    if not profiles_dir.exists():
        rprint("[yellow]No profiles directory found[/yellow]")
        return

    rprint("[bold]Available Profiles:[/bold]\n")
    for path in sorted(profiles_dir.glob("*.yaml")):
        rprint(f"  [cyan]{path.stem}[/cyan]")


if __name__ == "__main__":
    app()
```

**Step 4: Run test to verify it passes**

Run: `pytest tests/murmur/test_cli.py -v`
Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/cli.py tests/murmur/test_cli.py
git commit -m "feat: add basic CLI with list commands"
```

---

### Task 18: Generate Command

**Files:**
- Modify: `src/murmur/cli.py`
- Modify: `tests/murmur/test_cli.py`
- Create: `config/graphs/full.yaml`
- Create: `config/profiles/default.yaml`
- Create: `config/news_topics.yaml`

**Step 1: Create config files**

```yaml
# config/news_topics.yaml
topics:
  - name: ai-developments
    query: "artificial intelligence breakthroughs"
    priority: high

  - name: tech-industry
    query: "technology industry news"
    priority: medium

  - name: science
    query: "scientific discoveries"
    priority: low
```

```yaml
# config/profiles/default.yaml
name: default
graph: full

config:
  news_topics_file: news_topics.yaml
  piper_model: en_US-libritts_r-medium
  sentence_silence: 0.3
  narrator_style: warm-professional
  target_duration: 5
```

```yaml
# config/graphs/full.yaml
name: full-brief

nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics

  - name: plan
    transformer: brief-planner
    inputs:
      gathered_data: $gather.gathered_data

  - name: generate
    transformer: script-generator
    inputs:
      plan: $plan.plan
      gathered_data: $gather.gathered_data
      narrator_style: $config.narrator_style
      target_duration: $config.target_duration

  - name: synthesize
    transformer: piper-synthesizer
    inputs:
      script: $generate.script
      piper_model: $config.piper_model
      output_dir: $config.output_dir
      sentence_silence: $config.sentence_silence
```

**Step 2: Write the failing test**

```python
# tests/murmur/test_cli.py (append)

def test_cli_generate_dry_run(tmp_path):
    """CLI generate --dry-run should validate without executing."""
    # Create minimal config files
    config_dir = tmp_path / "config"
    graphs_dir = config_dir / "graphs"
    profiles_dir = config_dir / "profiles"
    graphs_dir.mkdir(parents=True)
    profiles_dir.mkdir(parents=True)

    (config_dir / "news_topics.yaml").write_text("""
topics:
  - name: test
    query: "test query"
    priority: high
""")

    (profiles_dir / "default.yaml").write_text("""
name: default
graph: full
config:
  news_topics_file: news_topics.yaml
""")

    (graphs_dir / "full.yaml").write_text("""
name: full
nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics
""")

    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        result = runner.invoke(app, ["generate", "--dry-run"])
        assert result.exit_code == 0
        assert "Would execute" in result.stdout or "Validation" in result.stdout
    finally:
        os.chdir(old_cwd)
```

**Step 3: Run test to verify it fails**

Run: `pytest tests/murmur/test_cli.py::test_cli_generate_dry_run -v`
Expected: FAIL (no generate command)

**Step 4: Add generate command**

```python
# src/murmur/cli.py (add to file, before if __name__ block)
from pathlib import Path
import yaml
from murmur.graph import load_graph, validate_graph
from murmur.executor import GraphExecutor


def load_profile(name: str) -> dict:
    """Load a profile configuration."""
    profile_path = Path("config/profiles") / f"{name}.yaml"
    with open(profile_path) as f:
        return yaml.safe_load(f)


def load_config(profile: dict) -> dict:
    """Load and resolve config values from profile."""
    config = profile.get("config", {}).copy()

    # Load news topics if referenced
    if "news_topics_file" in config:
        topics_path = Path("config") / config["news_topics_file"]
        with open(topics_path) as f:
            topics_data = yaml.safe_load(f)
            config["news_topics"] = topics_data.get("topics", [])

    # Set defaults
    config.setdefault("output_dir", "output")

    return config


@app.command()
def generate(
    profile: str = typer.Option("default", "--profile", "-p", help="Profile to use"),
    graph_override: str = typer.Option(None, "--graph", "-g", help="Override graph from profile"),
    dry_run: bool = typer.Option(False, "--dry-run", "-n", help="Validate without executing"),
    cached: str = typer.Option(None, "--cached", help="Comma-separated nodes to load from cache"),
    run_id: str = typer.Option(None, "--run", help="Run ID for cached artifacts"),
):
    """Generate a briefing."""
    # Load profile and config
    profile_data = load_profile(profile)
    config = load_config(profile_data)

    # Determine graph
    graph_name = graph_override or profile_data.get("graph", "full")
    graph_path = Path("config/graphs") / f"{graph_name}.yaml"
    graph = load_graph(graph_path)

    # Build registry
    registry = get_registry()

    # Validate
    try:
        validate_graph(graph, registry)
        rprint(f"[green]✓[/green] Graph '{graph_name}' validated successfully")
    except Exception as e:
        rprint(f"[red]✗[/red] Validation failed: {e}")
        raise typer.Exit(1)

    if dry_run:
        rprint(f"\n[bold]Would execute graph:[/bold] {graph_name}")
        rprint(f"[bold]Nodes:[/bold] {[n['name'] for n in graph['nodes']]}")
        return

    # Parse cached nodes
    cached_nodes = cached.split(",") if cached else None

    # Execute
    artifact_dir = Path("data/generation")
    executor = GraphExecutor(
        graph,
        registry,
        artifact_dir=artifact_dir,
        cached_nodes=cached_nodes,
        run_id=run_id,
    )

    rprint(f"\n[bold]Executing graph:[/bold] {graph_name}\n")
    result = executor.execute(config)

    # Report results
    rprint("\n[bold]Artifacts:[/bold]")
    for name, path in result.artifacts.items():
        rprint(f"  {name}: [cyan]{path}[/cyan]")
```

**Step 5: Run test to verify it passes**

Run: `pytest tests/murmur/test_cli.py -v`
Expected: PASS

**Step 6: Commit**

```bash
mkdir -p config/graphs config/profiles
git add src/murmur/cli.py tests/murmur/test_cli.py config/
git commit -m "feat: add generate command with dry-run and caching"
```

---

## Phase 7: Integration

### Task 19: End-to-End Test (Mocked)

**Files:**
- Create: `tests/murmur/test_integration.py`

**Step 1: Write integration test**

```python
# tests/murmur/test_integration.py
"""
Integration test for full pipeline with mocked Claude and Piper.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from murmur.registry import TransformerRegistry
from murmur.graph import load_graph
from murmur.executor import GraphExecutor
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer


def test_full_pipeline_mocked(tmp_path):
    """Full pipeline should execute with mocked external dependencies."""

    # Create graph
    graph = {
        "name": "test-full",
        "nodes": [
            {
                "name": "gather",
                "transformer": "news-fetcher",
                "inputs": {"topics": "$config.news_topics"},
            },
            {
                "name": "plan",
                "transformer": "brief-planner",
                "inputs": {"gathered_data": "$gather.gathered_data"},
            },
            {
                "name": "generate",
                "transformer": "script-generator",
                "inputs": {
                    "plan": "$plan.plan",
                    "gathered_data": "$gather.gathered_data",
                    "narrator_style": "$config.narrator_style",
                    "target_duration": "$config.target_duration",
                },
            },
            {
                "name": "synthesize",
                "transformer": "piper-synthesizer",
                "inputs": {
                    "script": "$generate.script",
                    "piper_model": "$config.piper_model",
                    "output_dir": "$config.output_dir",
                },
            },
        ],
    }

    # Build registry
    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)
    registry.register(ScriptGenerator)
    registry.register(PiperSynthesizer)

    # Config
    config = {
        "news_topics": [{"name": "AI", "query": "AI news", "priority": "high"}],
        "narrator_style": "warm-professional",
        "target_duration": 5,
        "piper_model": "en_US-libritts_r-medium",
        "output_dir": str(tmp_path / "output"),
    }

    # Mock responses
    gather_response = json.dumps({
        "items": [{"topic": "AI", "headline": "AI News", "summary": "Summary"}],
        "gathered_at": "2024-12-27T10:00:00Z",
    })
    plan_response = json.dumps({
        "sections": [{"title": "AI", "items": ["AI News"]}],
        "total_items": 1,
        "estimated_duration_minutes": 3,
    })
    generate_response = "Good morning! Here's your AI briefing. Exciting developments today."

    def mock_claude(prompt, allowed_tools=None):
        if "researcher" in prompt.lower():
            return gather_response
        elif "planner" in prompt.lower():
            return plan_response
        else:
            return generate_response

    output_audio = tmp_path / "output" / "brief_test.wav"
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    output_audio.write_bytes(b"fake audio")

    with patch("murmur.transformers.news_fetcher.run_claude", side_effect=mock_claude):
        with patch("murmur.transformers.brief_planner.run_claude", side_effect=mock_claude):
            with patch("murmur.transformers.script_generator.run_claude", side_effect=mock_claude):
                with patch("murmur.transformers.piper_synthesizer.synthesize_with_piper", return_value=output_audio):
                    executor = GraphExecutor(
                        graph,
                        registry,
                        artifact_dir=tmp_path / "artifacts",
                    )
                    result = executor.execute(config)

    # Verify all nodes executed
    assert "gather" in result.data
    assert "plan" in result.data
    assert "generate" in result.data
    assert "synthesize" in result.data

    # Verify artifacts
    assert "audio" in result.artifacts

    # Verify intermediate artifacts saved
    artifacts = list((tmp_path / "artifacts").glob("*.json"))
    assert len(artifacts) == 4  # One per node
```

**Step 2: Run test**

Run: `pytest tests/murmur/test_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/murmur/test_integration.py
git commit -m "test: add full pipeline integration test with mocks"
```

---

### Task 20: Final Wiring and Manual Test

**Files:**
- Update: `src/murmur/transformers/__init__.py`

**Step 1: Update transformers __init__**

```python
# src/murmur/transformers/__init__.py
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer

__all__ = [
    "NewsFetcher",
    "BriefPlanner",
    "ScriptGenerator",
    "PiperSynthesizer",
]
```

**Step 2: Run all tests**

Run: `pytest tests/ -v --cov=murmur`
Expected: All tests pass

**Step 3: Manual test (if Piper and Claude available)**

```bash
# Install with TTS support
pip install -e ".[tts]"

# Download a Piper model
mkdir -p models/piper
cd models/piper
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/resolve/main/en/en_US/libritts_r/medium/en_US-libritts_r-medium.onnx.json
cd ../..

# Dry run
murmur generate --dry-run

# Full run (requires Claude CLI configured)
murmur generate
```

**Step 4: Commit**

```bash
git add src/murmur/transformers/__init__.py
git commit -m "feat: complete v1 implementation"
```

---

## Summary

This plan implements Murmur v1 in 20 tasks across 7 phases:

1. **Project Foundation** (Tasks 1-3): pyproject.toml, TransformerIO, Transformer base class
2. **Graph Loading** (Tasks 4-7): YAML loading, registry, validation, cycle detection
3. **Graph Executor** (Tasks 8-11): Topological sort, execution, artifacts, caching
4. **Claude Integration** (Task 12): Subprocess wrapper
5. **Transformers** (Tasks 13-16): NewsFetcher, BriefPlanner, ScriptGenerator, PiperSynthesizer
6. **CLI** (Tasks 17-18): List commands, generate command
7. **Integration** (Tasks 19-20): End-to-end test, final wiring

Each task follows TDD: write failing test, implement, verify, commit.
