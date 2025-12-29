# tests/murmur/transformers/test_history_updater.py
import json
from datetime import datetime
from pathlib import Path
from murmur.core import TransformerIO
from murmur.transformers.history_updater import HistoryUpdater
from murmur.history import StoryHistory


def test_history_updater_has_correct_metadata():
    """HistoryUpdater should declare correct inputs/outputs/effects."""
    updater = HistoryUpdater()

    assert updater.name == "history-updater"
    assert "items_to_report" in updater.inputs
    assert "history_path" in updater.inputs
    assert "filesystem" in updater.output_effects


def test_history_updater_adds_new_stories(tmp_path):
    """HistoryUpdater should add new stories to history."""
    history_path = tmp_path / "history.json"

    updater = HistoryUpdater()
    input_io = TransformerIO(data={
        "items_to_report": [
            {
                "item": {
                    "headline": "New AI Model Released",
                    "summary": "OpenAI released a new model.",
                    "topic": "AI",
                    "url": "https://example.com/ai",
                },
                "story_key": "openai-new-model-2024",
                "action": "new",
            }
        ],
        "history_path": str(history_path),
    })

    result = updater.process(input_io)

    # Verify history was saved
    assert history_path.exists()
    history = StoryHistory.load(history_path)
    assert "openai-new-model-2024" in history.stories
    assert history.stories["openai-new-model-2024"].title == "New AI Model Released"
