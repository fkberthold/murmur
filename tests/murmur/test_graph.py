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
