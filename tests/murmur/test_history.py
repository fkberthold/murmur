# tests/murmur/test_history.py
import json
from datetime import datetime
from pathlib import Path
from murmur.history import ReportedStory, StoryHistory


def test_reported_story_creation():
    """ReportedStory should store all required fields."""
    story = ReportedStory(
        id="abc123",
        url="https://example.com/article",
        title="Hurricane Milton Makes Landfall",
        summary="Hurricane Milton made landfall in Florida on Tuesday.",
        topic="Weather",
        story_key="hurricane-milton-florida-2024",
        reported_at=datetime(2024, 12, 28, 10, 0, 0),
    )

    assert story.id == "abc123"
    assert story.story_key == "hurricane-milton-florida-2024"
    assert story.mention_count == 1
    assert story.developments == []


def test_story_history_creation():
    """StoryHistory should manage a collection of stories."""
    history = StoryHistory()

    assert history.stories == {}
    assert history.max_age_days == 7


def test_story_history_add_story():
    """StoryHistory.add should store a story by its key."""
    history = StoryHistory()
    story = ReportedStory(
        id="abc123",
        url="https://example.com",
        title="Test Story",
        summary="A test story.",
        topic="Test",
        story_key="test-story-2024",
        reported_at=datetime.now(),
    )

    history.add(story)

    assert "test-story-2024" in history.stories
    assert history.stories["test-story-2024"].id == "abc123"


def test_story_history_prune_removes_old_stories():
    """StoryHistory.prune should remove stories older than max_age_days."""
    from datetime import timedelta

    history = StoryHistory(max_age_days=7)
    now = datetime.now()

    # Old story (8 days ago)
    old_story = ReportedStory(
        id="old",
        url=None,
        title="Old Story",
        summary="Old.",
        topic="Test",
        story_key="old-story",
        reported_at=now - timedelta(days=8),
    )

    # Recent story (2 days ago)
    recent_story = ReportedStory(
        id="recent",
        url=None,
        title="Recent Story",
        summary="Recent.",
        topic="Test",
        story_key="recent-story",
        reported_at=now - timedelta(days=2),
    )

    history.add(old_story)
    history.add(recent_story)

    history.prune(now)

    assert "old-story" not in history.stories
    assert "recent-story" in history.stories


def test_story_history_save_creates_json_file(tmp_path):
    """StoryHistory.save should write stories to JSON file."""
    history = StoryHistory()
    story = ReportedStory(
        id="abc123",
        url="https://example.com",
        title="Test Story",
        summary="A test.",
        topic="Test",
        story_key="test-story",
        reported_at=datetime(2024, 12, 28, 10, 0, 0),
    )
    history.add(story)

    file_path = tmp_path / "history.json"
    history.save(file_path)

    assert file_path.exists()
    data = json.loads(file_path.read_text())
    assert "stories" in data
    assert "test-story" in data["stories"]
    assert data["stories"]["test-story"]["title"] == "Test Story"


def test_story_history_load_restores_from_json(tmp_path):
    """StoryHistory.load should restore stories from JSON file."""
    file_path = tmp_path / "history.json"
    file_path.write_text(json.dumps({
        "max_age_days": 7,
        "stories": {
            "test-story": {
                "id": "abc123",
                "url": "https://example.com",
                "title": "Test Story",
                "summary": "A test.",
                "topic": "Test",
                "story_key": "test-story",
                "reported_at": "2024-12-28T10:00:00",
                "last_mentioned_at": "2024-12-28T10:00:00",
                "mention_count": 1,
                "developments": [],
            }
        }
    }))

    history = StoryHistory.load(file_path)

    assert "test-story" in history.stories
    assert history.stories["test-story"].title == "Test Story"
    assert history.stories["test-story"].reported_at == datetime(2024, 12, 28, 10, 0, 0)


def test_story_history_load_returns_empty_for_missing_file(tmp_path):
    """StoryHistory.load should return empty history if file doesn't exist."""
    file_path = tmp_path / "nonexistent.json"

    history = StoryHistory.load(file_path)

    assert history.stories == {}


def test_reported_story_add_development():
    """ReportedStory.add_development should append development and update timestamp."""
    from datetime import timedelta

    now = datetime.now()
    story = ReportedStory(
        id="abc123",
        url=None,
        title="Hurricane Milton",
        summary="Hurricane approaches Florida.",
        topic="Weather",
        story_key="hurricane-milton-2024",
        reported_at=now - timedelta(days=1),
    )

    later = now
    story.add_development("Made landfall in Tampa", later)

    assert len(story.developments) == 1
    assert "Made landfall" in story.developments[0]
    assert story.mention_count == 2
    assert story.last_mentioned_at == later