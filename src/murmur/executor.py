import json
from datetime import datetime
from pathlib import Path
from typing import Any
from murmur.core import TransformerIO
from murmur.registry import TransformerRegistry
from murmur.graph import _build_dependency_graph, validate_graph


def topological_sort(deps: dict[str, set[str]]) -> list[str]:
    """
    Return nodes in topological order (dependencies before dependents).
    Assumes no cycles (validate_graph checks this).
    Uses Kahn's algorithm.
    """
    # Build reverse dependency map (who depends on whom)
    reverse_deps: dict[str, set[str]] = {node: set() for node in deps}
    for node, dependencies in deps.items():
        for dep in dependencies:
            if dep in reverse_deps:
                reverse_deps[dep].add(node)

    # Calculate in-degree (number of dependencies for each node)
    in_degree = {node: len(dependencies) for node, dependencies in deps.items()}

    # Start with nodes that have no dependencies
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

    def _save_artifact(self, node_name: str, data: dict) -> None:
        """Save node output to artifact directory."""
        if self.artifact_dir is None:
            return

        self.artifact_dir.mkdir(parents=True, exist_ok=True)
        artifact_path = self.artifact_dir / f"{self.run_id}_{node_name}.json"
        with open(artifact_path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    def _load_cached_artifact(self, node_name: str) -> dict | None:
        """Load cached node output if it exists."""
        if self.artifact_dir is None:
            return None

        artifact_path = self.artifact_dir / f"{self.run_id}_{node_name}.json"
        if not artifact_path.exists():
            return None

        with open(artifact_path) as f:
            return json.load(f)

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
