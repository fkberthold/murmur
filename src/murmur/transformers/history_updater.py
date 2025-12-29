# src/murmur/transformers/history_updater.py
import uuid
from datetime import datetime
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.history import StoryHistory, ReportedStory


class HistoryUpdater(Transformer):
    """Updates story history after a briefing is generated."""

    name = "history-updater"
    inputs = ["items_to_report", "history_path"]
    outputs = ["updated_count"]
    input_effects = []
    output_effects = ["filesystem"]

    def process(self, input: TransformerIO) -> TransformerIO:
        items_to_report = input.data.get("items_to_report", [])
        history_path = Path(input.data.get("history_path", "data/history.json"))

        # Load existing history
        history = StoryHistory.load(history_path)
        now = datetime.now()

        new_count = 0
        update_count = 0

        for item_data in items_to_report:
            item = item_data["item"]
            story_key = item_data["story_key"]
            action = item_data["action"]

            if action == "new":
                story = ReportedStory(
                    id=str(uuid.uuid4()),
                    url=item.get("url"),
                    title=item.get("headline", ""),
                    summary=item.get("summary", ""),
                    topic=item.get("topic", ""),
                    story_key=story_key,
                    reported_at=now,
                )
                history.add(story)
                new_count += 1

            elif action == "development":
                existing = history.get(story_key)
                if existing:
                    note = item_data.get("note", item.get("headline", ""))
                    existing.add_development(note, now)
                    update_count += 1

        # Save updated history
        history.save(history_path)

        return TransformerIO(data={
            "updated_count": {"new": new_count, "developments": update_count}
        })
