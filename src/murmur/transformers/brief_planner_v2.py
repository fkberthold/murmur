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
    inputs = ["gathered_data", "story_context"]
    outputs = ["plan"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        gathered_data = input.data.get("gathered_data", {})
        story_context = input.data.get("story_context", [])

        # Format inputs for prompt
        gathered_text = json.dumps(gathered_data, indent=2)
        context_text = self._format_story_context(story_context)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{story_context}}", context_text)
        prompt = prompt.replace("{{gathered_data}}", gathered_text)

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
