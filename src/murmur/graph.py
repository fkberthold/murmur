from pathlib import Path
from typing import TYPE_CHECKING
import yaml

if TYPE_CHECKING:
    from murmur.registry import TransformerRegistry


class GraphValidationError(Exception):
    """Raised when graph validation fails."""
    pass


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

    # Check for circular dependencies
    deps = _build_dependency_graph(graph)
    cycle = _detect_cycle(deps)
    if cycle:
        cycle_str = " -> ".join(cycle)
        raise GraphValidationError(f"Circular dependency detected: {cycle_str}")
