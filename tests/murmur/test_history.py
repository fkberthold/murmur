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
