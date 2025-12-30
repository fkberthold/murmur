"""Tests for Calendar configuration schema."""

import pytest
from pathlib import Path
import tempfile
import yaml


def test_load_calendar_config():
    """Load Calendar config from YAML file."""
    from murmur.config.calendar import load_calendar_config, CalendarConfig

    config_data = {
        "calendars": [
            {"name": "Personal", "id": "personal@gmail.com", "type": "personal", "enabled": True},
            {"name": "Work", "id": "work@company.com", "type": "work", "timezone": "America/Los_Angeles"},
        ],
        "event_rules": [
            {"pattern": "^Home$", "rule": "always_skip", "calendar": "Work"},
            {"pattern": "Interview", "rule": "always_mention", "priority": "high"},
        ],
        "notable_patterns": ["flight", "doctor", "interview"],
        "settings": {
            "display_timezone": "America/New_York",
            "include_all_day": True,
            "max_today_events": 10,
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_calendar_config(config_path)

        assert isinstance(config, CalendarConfig)
        assert len(config.calendars) == 2
        assert config.calendars[0].name == "Personal"
        assert config.calendars[1].timezone == "America/Los_Angeles"
        assert len(config.event_rules) == 2
        assert config.event_rules[0].rule == "always_skip"
        assert config.notable_patterns == ["flight", "doctor", "interview"]
        assert config.settings.display_timezone == "America/New_York"
    finally:
        config_path.unlink()


def test_calendar_config_defaults():
    """Empty config should use sensible defaults."""
    from murmur.config.calendar import load_calendar_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({}, f)
        config_path = Path(f.name)

    try:
        config = load_calendar_config(config_path)

        assert config.calendars == []
        assert config.event_rules == []
        assert config.notable_patterns == []
        assert config.settings.display_timezone == "America/New_York"
        assert config.settings.include_all_day == True
        assert config.settings.max_today_events == 10
    finally:
        config_path.unlink()


def test_calendar_config_missing_file():
    """Missing config file should return empty config."""
    from murmur.config.calendar import load_calendar_config

    config = load_calendar_config(Path("/nonexistent/config.yaml"))

    assert config.calendars == []
    assert config.settings.display_timezone == "America/New_York"
