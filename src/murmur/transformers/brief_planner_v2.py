# src/murmur/transformers/brief_planner_v2.py
import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "plan_v2.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class BriefPlannerV2(Transformer):
    """Plans the narrative structure with story continuity awareness."""

    name = "brief-planner-v2"
    inputs = ["gathered_data", "story_context", "slack_data"]
    outputs = ["plan"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        gathered_data = input.data.get("gathered_data", {})
        story_context = input.data.get("story_context", [])
        slack_data = input.data.get("slack_data")  # Optional

        # Format inputs for prompt
        gathered_text = json.dumps(gathered_data, indent=2)
        context_text = self._format_story_context(story_context)
        slack_text = self._format_slack_data(slack_data) if slack_data else "(No Slack data available)"

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{story_context}}", context_text)
        prompt = prompt.replace("{{gathered_data}}", gathered_text)
        prompt = prompt.replace("{{slack_highlights}}", slack_text)

        # Call Claude
        response = run_claude(prompt, allowed_tools=[])

        # Parse JSON response
        json_str = extract_json(response)
        plan = json.loads(json_str)

        return TransformerIO(data={"plan": plan})

    def _format_story_context(self, story_context: list) -> str:
        """Format story context for the prompt."""
        if not story_context:
            return "(All items are new - no prior coverage)"

        lines = []
        for ctx in story_context:
            story_key = ctx.get("story_key", "unknown")
            story_type = ctx.get("type", "new")

            if story_type == "development":
                note = ctx.get("note", "")
                lines.append(f"- `{story_key}`: **DEVELOPMENT** - {note}")
            else:
                lines.append(f"- `{story_key}`: New story")

        return "\n".join(lines)

    def _format_slack_data(self, slack_data) -> str:
        """Format Slack data for the planning prompt."""
        # Handle DataSource wrapper (temporary bridge until planner rewrite)
        if hasattr(slack_data, 'data'):
            slack_data = slack_data.data

        if not slack_data:
            return "(No Slack data)"

        lines = []

        # Add summary if present
        if summary := slack_data.get("summary"):
            lines.append(f"**Summary:** {summary}")
            lines.append("")

        # Add important messages
        messages = slack_data.get("messages", [])
        if messages:
            lines.append("**Key Messages:**")
            for msg in messages[:5]:  # Limit to top 5
                author = msg.get("author", "Unknown")
                text = msg.get("text", "")[:200]  # Truncate long messages
                channel = msg.get("channel_name", "")
                importance = msg.get("importance", "medium")
                lines.append(f"- [{importance}] #{channel} - {author}: {text}")

        # Add mentions
        mentions = slack_data.get("mentions", [])
        if mentions:
            lines.append("")
            lines.append("**Project Mentions:**")
            for mention in mentions[:3]:
                author = mention.get("author", "Unknown")
                text = mention.get("text", "")[:150]
                lines.append(f"- {author}: {text}")

        return "\n".join(lines) if lines else "(No significant Slack activity)"
