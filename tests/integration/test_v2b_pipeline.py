"""Integration test for v2b pipeline with Slack."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import tempfile


@pytest.fixture
def mock_slack_config(tmp_path):
    """Create a temporary Slack config."""
    config = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
        ],
        "settings": {"lookback_hours": 24}
    }
    config_path = tmp_path / "slack.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    return config_path


@pytest.fixture
def mock_mcp_config(tmp_path):
    """Create a temporary MCP config."""
    config = {
        "mcpServers": {
            "slack": {
                "type": "stdio",
                "command": "echo",
                "args": ["test"]
            }
        }
    }
    config_path = tmp_path / ".mcp.json"
    with open(config_path, 'w') as f:
        import json
        json.dump(config, f)
    return config_path


def test_v2b_graph_loads(mock_slack_config, mock_mcp_config):
    """v2b graph should load and validate."""
    from murmur.graph import load_graph, validate_graph
    from murmur.transformers import create_registry

    graph_path = Path(__file__).parent.parent.parent / "config" / "graphs" / "full-v2b.yaml"
    if not graph_path.exists():
        pytest.skip("v2b graph not yet created")

    graph = load_graph(graph_path)
    registry = create_registry()

    # Should not raise
    validate_graph(graph, registry)


def test_slack_fetcher_in_registry():
    """Slack fetcher should be registered."""
    from murmur.transformers import create_registry

    registry = create_registry()

    fetcher = registry.get("slack-fetcher")
    assert fetcher is not None
    assert fetcher.name == "slack-fetcher"


def test_planner_handles_empty_data_sources():
    """Planner should work with empty data sources list."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0}'

        # Empty data_sources list
        result = planner.process(TransformerIO(data={
            "data_sources": [],
            "story_context": [],
        }))

        assert result.data.get("plan") is not None
