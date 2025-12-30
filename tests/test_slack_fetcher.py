import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml


def test_slack_fetcher_generates_prompt():
    """Slack fetcher should generate proper gathering prompt."""
    from murmur.transformers.slack_fetcher import SlackFetcher
    from murmur.core import TransformerIO

    # Create temp config
    config_data = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
        ],
        "settings": {"lookback_hours": 24}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = SlackFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"messages": [], "mentions": []}'

            result = fetcher.process(TransformerIO(data={
                "slack_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            # Check Claude was called
            assert mock_claude.called
            prompt = mock_claude.call_args[0][0]

            # Prompt should include channel info
            assert "general" in prompt
            assert "C123" in prompt
    finally:
        config_path.unlink()


def test_slack_fetcher_uses_mcp_tools():
    """Slack fetcher should use MCP Slack tools."""
    from murmur.transformers.slack_fetcher import SlackFetcher

    fetcher = SlackFetcher()

    # Check declared effects
    assert "mcp:slack" in fetcher.input_effects


def test_slack_fetcher_output_structure():
    """Slack fetcher should output slack_data key."""
    from murmur.transformers.slack_fetcher import SlackFetcher

    fetcher = SlackFetcher()
    assert "slack_data" in fetcher.outputs
