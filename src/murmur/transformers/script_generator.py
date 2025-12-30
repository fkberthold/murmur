import json
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "generate.md"

NARRATOR_STYLES = {
    "warm-professional": """
You are a warm but professional assistant, like an NPR morning host.
- Friendly and approachable, but not overly casual
- Clear and informative without being dry
- Occasionally show personality through word choice
- Use "you" to address the listener directly
""",
}


class ScriptGenerator(Transformer):
    """Generates TTS-ready script from a briefing plan."""

    name = "script-generator"
    inputs = ["plan", "gathered_data", "narrator_style", "target_duration"]
    outputs = ["script"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        plan = input.data.get("plan", {})
        gathered_data = input.data.get("gathered_data", {})
        narrator_style = input.data.get("narrator_style", "warm-professional")
        target_duration = input.data.get("target_duration", 5)

        # Handle DataSource wrapper (temporary bridge until planner rewrite)
        if hasattr(gathered_data, 'data'):
            gathered_data = gathered_data.data

        # Get narrator style description
        style_text = NARRATOR_STYLES.get(narrator_style, NARRATOR_STYLES["warm-professional"])

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = (
            prompt_template
            .replace("{{narrator_style}}", style_text)
            .replace("{{plan}}", json.dumps(plan, indent=2))
            .replace("{{gathered_data}}", json.dumps(gathered_data, indent=2))
            .replace("{{target_duration}}", str(target_duration))
        )

        # Call Claude (no tools needed for generation)
        response = run_claude(prompt, allowed_tools=[])

        return TransformerIO(data={"script": response.strip()})
