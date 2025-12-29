# tests/murmur/transformers/test_story_deduplicator.py
from murmur.transformers.story_deduplicator import StoryDeduplicator


def test_story_deduplicator_has_correct_metadata():
    """StoryDeduplicator should declare correct inputs/outputs/effects."""
    deduplicator = StoryDeduplicator()

    assert deduplicator.name == "story-deduplicator"
    assert "news_items" in deduplicator.inputs
    assert "history_path" in deduplicator.inputs
    assert "filtered_news" in deduplicator.outputs
    assert "story_context" in deduplicator.outputs
    assert "items_to_report" in deduplicator.outputs
    assert "llm" in deduplicator.input_effects
