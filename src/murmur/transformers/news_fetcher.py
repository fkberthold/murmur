import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.claude import run_claude


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "gather.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    # Try to find JSON in markdown code block
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    # Otherwise return as-is
    return text.strip()


class NewsFetcher(Transformer):
    """Fetches news using Claude's web search capability."""

    name = "news-fetcher"
    inputs = ["topics"]
    outputs = ["gathered_data"]
    input_effects = ["llm"]
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        topics = input.data.get("topics", [])

        # Format topics for prompt
        topics_text = "\n".join(
            f"- **{t['name']}** (priority: {t.get('priority', 'medium')}): {t['query']}"
            for t in topics
        )

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{topics}}", topics_text)

        # Call Claude with web search
        response = run_claude(prompt, allowed_tools=["WebSearch"])

        # Parse JSON response (handle markdown code blocks)
        json_str = extract_json(response)
        gathered_data = json.loads(json_str)

        return TransformerIO(data={"gathered_data": gathered_data})
