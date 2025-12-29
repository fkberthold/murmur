# src/murmur/transformers/story_deduplicator.py
import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude
from murmur.history import StoryHistory, ReportedStory


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "dedupe.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class StoryDeduplicator(Transformer):
    """Filters news items against story history to prevent duplicates."""

    name = "story-deduplicator"
    inputs = ["news_items", "history_path"]
    outputs = ["filtered_news", "story_context", "items_to_report"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        # Implementation in next task
        raise NotImplementedError("Coming in next task")
