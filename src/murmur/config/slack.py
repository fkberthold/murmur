"""Slack configuration schema."""

from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class SlackChannel:
    """A Slack channel to monitor."""
    name: str
    id: str = ""
    priority: str = "medium"


@dataclass
class SlackColleague:
    """A colleague whose messages are prioritized."""
    name: str
    slack_id: str = ""
    priority: str = "medium"


@dataclass
class SlackProject:
    """A project to watch for keyword mentions."""
    name: str
    keywords: list[str] = field(default_factory=list)
    priority: str = "medium"


@dataclass
class SlackSettings:
    """Slack monitoring settings."""
    lookback_hours: int = 24
    include_threads: bool = True
    include_reactions: bool = False
    min_message_length: int = 10


@dataclass
class SlackConfig:
    """Complete Slack configuration."""
    channels: list[SlackChannel] = field(default_factory=list)
    colleagues: list[SlackColleague] = field(default_factory=list)
    projects: list[SlackProject] = field(default_factory=list)
    settings: SlackSettings = field(default_factory=SlackSettings)


def load_slack_config(path: Path) -> SlackConfig:
    """Load Slack configuration from YAML file."""
    if not path.exists():
        return SlackConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    channels = [
        SlackChannel(**ch) for ch in data.get("channels", [])
    ]

    colleagues = [
        SlackColleague(**col) for col in data.get("colleagues", [])
    ]

    projects = [
        SlackProject(**proj) for proj in data.get("projects", [])
    ]

    settings_data = data.get("settings", {})
    settings = SlackSettings(
        lookback_hours=settings_data.get("lookback_hours", 24),
        include_threads=settings_data.get("include_threads", True),
        include_reactions=settings_data.get("include_reactions", False),
        min_message_length=settings_data.get("min_message_length", 10),
    )

    return SlackConfig(
        channels=channels,
        colleagues=colleagues,
        projects=projects,
        settings=settings,
    )
