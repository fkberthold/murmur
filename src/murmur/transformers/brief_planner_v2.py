# src/murmur/transformers/brief_planner_v2.py
import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO, DataSource
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "plan_v2.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class BriefPlannerV2(Transformer):
    """Plans the narrative structure from multiple data sources."""

    name = "brief-planner-v2"
    inputs = ["data_sources", "story_context"]
    outputs = ["plan"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        data_sources: list[DataSource] = input.data.get("data_sources", [])
        story_context = input.data.get("story_context", [])

        # Format story context
        context_text = self._format_story_context(story_context)

        # Assemble data sources section dynamically
        sources_text = self._assemble_sources(data_sources)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{story_context}}", context_text)
        prompt = prompt.replace("{{data_sources}}", sources_text)

        # Call Claude
        response = run_claude(prompt, allowed_tools=[])

        # Parse JSON response
        json_str = extract_json(response)
        plan = json.loads(json_str)

        return TransformerIO(data={"plan": plan})

    def _assemble_sources(self, sources: list[DataSource]) -> str:
        """Assemble prompt content from all data sources."""
        if not sources:
            return "(No data sources available)"

        sections = []
        for source in sources:
            section = self._render_source(source)
            if section:
                sections.append(section)

        return "\n\n".join(sections) if sections else "(No data available)"

    def _render_source(self, source: DataSource) -> str:
        """Render a single data source using its prompt fragment."""
        # Load prompt fragment if available
        if source.prompt_fragment_path and source.prompt_fragment_path.exists():
            fragment_template = source.prompt_fragment_path.read_text()
        else:
            # Fallback: generic format
            fragment_template = f"## {source.name.title()}\n\n{{{{data}}}}"

        # Format data as JSON for the prompt
        data_text = json.dumps(source.data, indent=2)

        # Replace data placeholder
        return fragment_template.replace("{{data}}", data_text)

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
