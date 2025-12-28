# src/murmur/history.py
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ReportedStory:
    """A story that was previously reported."""
    id: str
    url: str | None
    title: str
    summary: str
    topic: str
    story_key: str
    reported_at: datetime
    last_mentioned_at: datetime | None = None
    mention_count: int = 1
    developments: list[str] = field(default_factory=list)

    def __post_init__(self):
        if self.last_mentioned_at is None:
            self.last_mentioned_at = self.reported_at
