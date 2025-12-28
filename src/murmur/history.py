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


@dataclass
class StoryHistory:
    """Rolling history of reported stories."""
    stories: dict[str, ReportedStory] = field(default_factory=dict)
    max_age_days: int = 7

    def add(self, story: ReportedStory) -> None:
        """Add or update a story in the history."""
        self.stories[story.story_key] = story

    def get(self, story_key: str) -> ReportedStory | None:
        """Get a story by its key."""
        return self.stories.get(story_key)

    def has(self, story_key: str) -> bool:
        """Check if a story key exists in history."""
        return story_key in self.stories
