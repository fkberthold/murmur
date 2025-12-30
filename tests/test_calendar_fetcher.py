"""Tests for Calendar fetcher transformer."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml


def test_calendar_fetcher_generates_prompt():
    """Calendar fetcher should generate proper gathering prompt."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO

    config_data = {
        "calendars": [
            {"name": "Personal", "id": "personal@gmail.com", "type": "personal", "enabled": True},
        ],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "No events"}'

            result = fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            assert mock_claude.called
            prompt = mock_claude.call_args[0][0]

            # Prompt should include calendar info
            assert "Personal" in prompt
            assert "personal@gmail.com" in prompt
    finally:
        config_path.unlink()


def test_calendar_fetcher_uses_mcp_tools():
    """Calendar fetcher should use MCP Google Calendar tools."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher

    fetcher = CalendarFetcher()

    assert "mcp:google-calendar" in fetcher.input_effects


def test_calendar_fetcher_output_structure():
    """Calendar fetcher should output calendar key."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher

    fetcher = CalendarFetcher()
    assert "calendar" in fetcher.outputs


def test_calendar_fetcher_outputs_data_source():
    """Calendar fetcher should output a DataSource object."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO, DataSource

    config_data = {
        "calendars": [{"name": "Personal", "id": "personal@gmail.com", "enabled": True}],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "Free day"}'

            result = fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            assert "calendar" in result.data
            source = result.data["calendar"]
            assert isinstance(source, DataSource)
            assert source.name == "calendar"
            assert "today_events" in source.data
            assert source.prompt_fragment_path == Path("prompts/sources/calendar.md")
    finally:
        config_path.unlink()


def test_calendar_fetcher_formats_event_rules():
    """Calendar fetcher should format event rules in prompt."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO

    config_data = {
        "calendars": [{"name": "Work", "id": "work@company.com", "enabled": True}],
        "event_rules": [
            {"pattern": "^Home$", "rule": "always_skip", "calendar": "Work"},
            {"pattern": "Interview", "rule": "always_mention"},
        ],
        "notable_patterns": ["flight", "doctor"],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "No events"}'

            fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            prompt = mock_claude.call_args[0][0]

            # Should include event rules
            assert "always_skip" in prompt
            assert "^Home$" in prompt
            assert "Interview" in prompt

            # Should include notable patterns
            assert "flight" in prompt
            assert "doctor" in prompt
    finally:
        config_path.unlink()
