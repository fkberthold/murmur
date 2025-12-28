# tests/murmur/test_history.py
from datetime import datetime
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
