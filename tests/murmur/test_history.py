# tests/murmur/test_history.py
from datetime import datetime
from murmur.history import ReportedStory


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
