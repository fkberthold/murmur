import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "plan.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class BriefPlanner(Transformer):
    """Plans the narrative structure of a briefing."""

    name = "brief-planner"
    inputs = ["gathered_data"]
    outputs = ["plan"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        gathered_data = input.data.get("gathered_data", {})

        # Format gathered data for prompt
        gathered_text = json.dumps(gathered_data, indent=2)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{gathered_data}}", gathered_text)

        # Call Claude (no tools needed for planning)
        response = run_claude(prompt, allowed_tools=[])

        # Parse JSON response (handle markdown code blocks)
        json_str = extract_json(response)
        plan = json.loads(json_str)

        return TransformerIO(data={"plan": plan})
