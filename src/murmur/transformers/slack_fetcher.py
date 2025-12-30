"""Slack data fetcher using MCP tools."""

import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO, DataSource
from murmur.claude import run_claude
from murmur.config.slack import load_slack_config


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "slack_gather.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class SlackFetcher(Transformer):
    """Fetches Slack messages using MCP Slack tools."""

    name = "slack-fetcher"
    inputs = ["slack_config_path", "mcp_config_path"]
    outputs = ["slack"]
    input_effects = ["mcp:slack"]
    output_effects = []

    # MCP tools this transformer uses
    MCP_TOOLS = [
        "mcp__slack__channels_list",
        "mcp__slack__conversations_history",
        "mcp__slack__conversations_search_messages",
    ]

    def process(self, input: TransformerIO) -> TransformerIO:
        config_path = Path(input.data.get("slack_config_path", "config/slack.yaml"))
        mcp_config_path = input.data.get("mcp_config_path")

        config = load_slack_config(config_path)

        # Format config for prompt
        channels_text = self._format_channels(config.channels)
        colleagues_text = self._format_colleagues(config.colleagues)
        projects_text = self._format_projects(config.projects)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{channels}}", channels_text)
        prompt = prompt.replace("{{colleagues}}", colleagues_text)
        prompt = prompt.replace("{{projects}}", projects_text)
        prompt = prompt.replace("{{lookback_hours}}", str(config.settings.lookback_hours))
        prompt = prompt.replace("{{include_threads}}", str(config.settings.include_threads).lower())

        # Call Claude with MCP tools
        response = self._run_claude(
            prompt,
            mcp_config_path=mcp_config_path,
        )

        # Parse JSON response
        json_str = extract_json(response)
        slack_data = json.loads(json_str)

        # Return as DataSource
        source = DataSource(
            name="slack",
            data=slack_data,
            prompt_fragment_path=Path("prompts/sources/slack.md"),
        )

        return TransformerIO(data={"slack": source})

    def _run_claude(self, prompt: str, mcp_config_path: str | None = None) -> str:
        """Run Claude with MCP tools enabled."""
        mcp_config = Path(mcp_config_path) if mcp_config_path else None
        return run_claude(
            prompt,
            allowed_tools=self.MCP_TOOLS,
            mcp_config=mcp_config,
        )

    def _format_channels(self, channels: list) -> str:
        if not channels:
            return "(No channels configured)"
        lines = []
        for ch in channels:
            id_str = f"(ID: {ch.id})" if ch.id else "(ID unknown)"
            lines.append(f"- #{ch.name} {id_str} - priority: {ch.priority}")
        return "\n".join(lines)

    def _format_colleagues(self, colleagues: list) -> str:
        if not colleagues:
            return "(No key people configured)"
        lines = []
        for col in colleagues:
            id_str = f"(ID: {col.slack_id})" if col.slack_id else ""
            lines.append(f"- {col.name} {id_str}")
        return "\n".join(lines)

    def _format_projects(self, projects: list) -> str:
        if not projects:
            return "(No projects configured)"
        lines = []
        for proj in projects:
            keywords = ", ".join(proj.keywords) if proj.keywords else "no keywords"
            lines.append(f"- {proj.name}: {keywords}")
        return "\n".join(lines)
