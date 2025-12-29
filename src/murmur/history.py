# src/murmur/history.py
import json
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path


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

    def add_development(self, development: str, timestamp: datetime | None = None) -> None:
        """Record a new development for this story."""
        if timestamp is None:
            timestamp = datetime.now()
        self.developments.append(development)
        self.mention_count += 1
        self.last_mentioned_at = timestamp


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

    def prune(self, now: datetime | None = None) -> int:
        """Remove stories older than max_age_days. Returns count removed."""
        if now is None:
            now = datetime.now()

        cutoff = now - timedelta(days=self.max_age_days)
        expired_keys = [
            key for key, story in self.stories.items()
            if story.last_mentioned_at < cutoff
        ]

        for key in expired_keys:
            del self.stories[key]

        return len(expired_keys)

    def save(self, path: Path) -> None:
        """Save history to JSON file."""
        path.parent.mkdir(parents=True, exist_ok=True)

        data = {
            "max_age_days": self.max_age_days,
            "stories": {
                key: {
                    "id": story.id,
                    "url": story.url,
                    "title": story.title,
                    "summary": story.summary,
                    "topic": story.topic,
                    "story_key": story.story_key,
                    "reported_at": story.reported_at.isoformat(),
                    "last_mentioned_at": story.last_mentioned_at.isoformat(),
                    "mention_count": story.mention_count,
                    "developments": story.developments,
                }
                for key, story in self.stories.items()
            }
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, path: Path) -> "StoryHistory":
        """Load history from JSON file. Returns empty history if file doesn't exist."""
        if not path.exists():
            return cls()

        with open(path) as f:
            data = json.load(f)

        history = cls(max_age_days=data.get("max_age_days", 7))

        for key, story_data in data.get("stories", {}).items():
            story = ReportedStory(
                id=story_data["id"],
                url=story_data["url"],
                title=story_data["title"],
                summary=story_data["summary"],
                topic=story_data["topic"],
                story_key=story_data["story_key"],
                reported_at=datetime.fromisoformat(story_data["reported_at"]),
                last_mentioned_at=datetime.fromisoformat(story_data["last_mentioned_at"]),
                mention_count=story_data["mention_count"],
                developments=story_data["developments"],
            )
            history.stories[key] = story

        return history