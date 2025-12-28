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
