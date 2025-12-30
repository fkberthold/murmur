"""Integration test for calendar in pipeline."""

import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
import yaml


def test_calendar_in_planner_data_sources():
    """Calendar DataSource should work with planner."""
    from murmur.core import DataSource

    # Create a calendar DataSource like the fetcher would
    calendar_source = DataSource(
        name="calendar",
        data={
            "today_events": [
                {
                    "calendar_name": "Work",
                    "title": "Team Standup",
                    "start_time": "2024-12-30T10:00:00",
                    "end_time": "2024-12-30T10:30:00",
                    "is_all_day": False,
                    "status": "confirmed",
                }
            ],
            "tomorrow_notable": [
                {
                    "calendar_name": "Personal",
                    "title": "Dentist Appointment",
                    "start_time": "2024-12-31T14:00:00",
                    "end_time": "2024-12-31T15:00:00",
                    "is_all_day": False,
                    "status": "confirmed",
                }
            ],
            "summary": "1 meeting today, dentist tomorrow"
        },
        prompt_fragment_path=Path("prompts/sources/calendar.md"),
    )

    # Verify DataSource structure
    assert calendar_source.name == "calendar"
    assert len(calendar_source.data["today_events"]) == 1
    assert len(calendar_source.data["tomorrow_notable"]) == 1
    assert calendar_source.prompt_fragment_path.exists()


def test_v2c_graph_loads():
    """The v2c graph with calendar should load successfully."""
    from murmur.graph import load_graph

    graph = load_graph(Path("config/graphs/full-v2c.yaml"))

    assert graph["name"] == "full-v2c"

    # Find calendar node
    calendar_node = None
    for node in graph["nodes"]:
        if node["name"] == "calendar":
            calendar_node = node
            break

    assert calendar_node is not None
    assert calendar_node["transformer"] == "calendar-fetcher"
    assert "calendar_config_path" in calendar_node["inputs"]
