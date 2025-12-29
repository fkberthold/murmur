# tests/murmur/transformers/test_story_deduplicator.py
import json
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.story_deduplicator import StoryDeduplicator
from murmur.history import StoryHistory, ReportedStory


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


def test_story_deduplicator_filters_duplicates(tmp_path):
    """StoryDeduplicator should skip items that are duplicates."""
    # Setup history with an existing story
    history = StoryHistory()
    history.add(ReportedStory(
        id="existing",
        url="https://example.com/old",
        title="Micron Beats Earnings",
        summary="Micron reported Q4 earnings above expectations.",
        topic="Tech",
        story_key="micron-q4-2024-earnings",
        reported_at=datetime(2024, 12, 27, 10, 0, 0),
    ))
    history_path = tmp_path / "history.json"
    history.save(history_path)

    # Mock Claude response
    mock_response = json.dumps({
        "items": [
            {
                "candidate_index": 0,
                "story_key": "new-ai-breakthrough",
                "action": "include_as_new",
                "reason": "First time covering this story"
            },
            {
                "candidate_index": 1,
                "story_key": "micron-q4-2024-earnings",
                "action": "skip",
                "skip_reason": "Same information as yesterday"
            }
        ]
    })

    with patch("murmur.transformers.story_deduplicator.run_claude", return_value=mock_response):
        deduplicator = StoryDeduplicator()
        input_io = TransformerIO(data={
            "news_items": {
                "items": [
                    {"headline": "New AI Model Released", "topic": "AI"},
                    {"headline": "Micron Stock Up After Earnings", "topic": "Tech"},
                ]
            },
            "history_path": str(history_path),
        })

        result = deduplicator.process(input_io)

        # Should only include the new AI story
        assert len(result.data["filtered_news"]["items"]) == 1
        assert result.data["filtered_news"]["items"][0]["headline"] == "New AI Model Released"

        # story_context should have the new story key
        assert "new-ai-breakthrough" in str(result.data["story_context"])
