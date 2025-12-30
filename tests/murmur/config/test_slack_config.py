"""Tests for Slack configuration schema."""

import pytest
from pathlib import Path
import tempfile
import yaml


def test_load_slack_config():
    """Load Slack config from YAML file."""
    from murmur.config.slack import load_slack_config, SlackConfig

    config_data = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
            {"name": "random", "id": "C456", "priority": "low"},
        ],
        "colleagues": [
            {"name": "Alice", "slack_id": "U123"},
        ],
        "projects": [
            {"name": "Project X", "keywords": ["projectx", "px"]},
        ],
        "settings": {
            "lookback_hours": 24,
            "include_threads": True,
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_slack_config(config_path)

        assert isinstance(config, SlackConfig)
        assert len(config.channels) == 2
        assert config.channels[0].name == "general"
        assert config.channels[0].priority == "high"
        assert len(config.colleagues) == 1
        assert config.colleagues[0].name == "Alice"
        assert config.settings.lookback_hours == 24
    finally:
        config_path.unlink()


def test_slack_config_defaults():
    """Empty config should use sensible defaults."""
    from murmur.config.slack import load_slack_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({}, f)
        config_path = Path(f.name)

    try:
        config = load_slack_config(config_path)

        assert config.channels == []
        assert config.settings.lookback_hours == 24
        assert config.settings.include_threads == True
    finally:
        config_path.unlink()
