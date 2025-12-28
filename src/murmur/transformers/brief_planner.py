import json
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "plan.md"


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

        # Parse JSON response
        plan = json.loads(response)

        return TransformerIO(data={"plan": plan})
