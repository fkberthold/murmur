from pathlib import Path
import yaml


def load_graph(path: Path) -> dict:
    """Load a graph definition from a YAML file."""
    with open(path) as f:
        return yaml.safe_load(f)
