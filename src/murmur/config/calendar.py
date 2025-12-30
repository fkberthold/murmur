"""Calendar configuration schema."""

from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Calendar:
    """A Google Calendar to monitor."""
    name: str
    id: str
    type: str = "personal"
    enabled: bool = True
    timezone: str = ""


@dataclass
class EventRule:
    """A rule for filtering events."""
    pattern: str
    rule: str  # always_skip, always_mention, canceled_only
    calendar: str = ""
    priority: str = "medium"


@dataclass
class CalendarSettings:
    """Calendar monitoring settings."""
    display_timezone: str = "America/New_York"
    include_all_day: bool = True
    include_tentative: bool = True
    include_declined: bool = False
    max_today_events: int = 10
    max_tomorrow_events: int = 5


@dataclass
class CalendarConfig:
    """Complete Calendar configuration."""
    calendars: list[Calendar] = field(default_factory=list)
    event_rules: list[EventRule] = field(default_factory=list)
    notable_patterns: list[str] = field(default_factory=list)
    settings: CalendarSettings = field(default_factory=CalendarSettings)


def load_calendar_config(path: Path) -> CalendarConfig:
    """Load Calendar configuration from YAML file."""
    if not path.exists():
        return CalendarConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    calendars = [
        Calendar(**cal) for cal in data.get("calendars", [])
    ]

    event_rules = [
        EventRule(**rule) for rule in data.get("event_rules", [])
    ]

    notable_patterns = data.get("notable_patterns", [])

    settings_data = data.get("settings", {})
    settings = CalendarSettings(
        display_timezone=settings_data.get("display_timezone", "America/New_York"),
        include_all_day=settings_data.get("include_all_day", True),
        include_tentative=settings_data.get("include_tentative", True),
        include_declined=settings_data.get("include_declined", False),
        max_today_events=settings_data.get("max_today_events", 10),
        max_tomorrow_events=settings_data.get("max_tomorrow_events", 5),
    )

    return CalendarConfig(
        calendars=calendars,
        event_rules=event_rules,
        notable_patterns=notable_patterns,
        settings=settings,
    )
