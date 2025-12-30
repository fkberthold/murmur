# src/murmur/transformers/story_deduplicator.py
import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO, DataSource
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
    outputs = ["news", "story_context", "items_to_report"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        news_items = input.data.get("news_items", {})
        history_path = Path(input.data.get("history_path", "data/history.json"))

        # Load existing history
        history = StoryHistory.load(history_path)
        history.prune()  # Remove expired stories

        # Format history for prompt
        history_text = self._format_history(history)
        candidates_text = json.dumps(news_items.get("items", []), indent=2)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{history}}", history_text)
        prompt = prompt.replace("{{candidates}}", candidates_text)

        # Call Claude for deduplication
        response = run_claude(prompt, allowed_tools=[])

        # Parse response
        json_str = extract_json(response)
        dedup_result = json.loads(json_str)

        # Filter items based on Claude's decisions
        original_items = news_items.get("items", [])
        filtered_items = []
        story_context = []
        items_to_report = []

        for item in dedup_result.get("items", []):
            idx = item["candidate_index"]
            action = item["action"]
            story_key = item["story_key"]

            if action == "include_as_new":
                filtered_items.append(original_items[idx])
                story_context.append({
                    "story_key": story_key,
                    "type": "new",
                })
                items_to_report.append({
                    "item": original_items[idx],
                    "story_key": story_key,
                    "action": "new",
                })
            elif action == "include_as_development":
                filtered_items.append(original_items[idx])
                story_context.append({
                    "story_key": story_key,
                    "type": "development",
                    "note": item.get("development_note", ""),
                    "existing_story_id": item.get("existing_story_id"),
                })
                items_to_report.append({
                    "item": original_items[idx],
                    "story_key": story_key,
                    "action": "development",
                    "note": item.get("development_note", ""),
                })
            # Skip items with action="skip"

        # Wrap news in DataSource
        filtered_news = {"items": filtered_items, "gathered_at": news_items.get("gathered_at")}
        news_source = DataSource(
            name="news",
            data=filtered_news,
            prompt_fragment_path=Path("prompts/sources/news.md"),
        )

        return TransformerIO(data={
            "news": news_source,
            "story_context": story_context,
            "items_to_report": items_to_report,
        })

    def _format_history(self, history: StoryHistory) -> str:
        """Format history for the prompt."""
        if not history.stories:
            return "(No previous stories)"

        lines = []
        for key, story in history.stories.items():
            lines.append(f"- **{story.title}** (key: `{key}`)")
            lines.append(f"  - First reported: {story.reported_at.strftime('%Y-%m-%d')}")
            lines.append(f"  - Summary: {story.summary}")
            if story.developments:
                lines.append(f"  - Developments: {', '.join(story.developments)}")
        return "\n".join(lines)
