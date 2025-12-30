"""Google Calendar data fetcher using MCP tools."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from murmur.core import Transformer, TransformerIO, DataSource
from murmur.claude import run_claude
from murmur.config.calendar import load_calendar_config


PROMPT_PATH = Path(__file__).parent.parent.parent.parent / "prompts" / "calendar_gather.md"


def extract_json(text: str) -> str:
    """Extract JSON from text, handling markdown code blocks."""
    match = re.search(r'```(?:json)?\s*([\s\S]*?)```', text)
    if match:
        return match.group(1).strip()
    return text.strip()


class CalendarFetcher(Transformer):
    """Fetches Google Calendar events using MCP tools."""

    name = "calendar-fetcher"
    inputs = ["calendar_config_path", "mcp_config_path"]
    outputs = ["calendar"]
    input_effects = ["mcp:google-calendar"]
    output_effects = []

    MCP_TOOLS = [
        "mcp__google-calendar__list-events",
        "mcp__google-calendar__get-current-time",
    ]

    def process(self, input: TransformerIO) -> TransformerIO:
        config_path = Path(input.data.get("calendar_config_path", "config/calendar.yaml"))
        mcp_config_path = input.data.get("mcp_config_path")

        config = load_calendar_config(config_path)

        # Calculate time windows
        now = datetime.now()
        today_end = now.replace(hour=23, minute=59, second=59)
        tomorrow_start = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow_end = tomorrow_start.replace(hour=23, minute=59, second=59)

        # Format config for prompt
        calendars_text = self._format_calendars(config.calendars)
        rules_text = self._format_event_rules(config.event_rules)
        patterns_text = self._format_notable_patterns(config.notable_patterns)

        # Load and fill prompt template
        prompt_template = PROMPT_PATH.read_text()
        prompt = prompt_template.replace("{{calendars}}", calendars_text)
        prompt = prompt.replace("{{event_rules}}", rules_text)
        prompt = prompt.replace("{{notable_patterns}}", patterns_text)
        prompt = prompt.replace("{{display_timezone}}", config.settings.display_timezone)
        prompt = prompt.replace("{{today_start}}", now.strftime("%Y-%m-%dT%H:%M:%S"))
        prompt = prompt.replace("{{today_end}}", today_end.strftime("%Y-%m-%dT%H:%M:%S"))
        prompt = prompt.replace("{{tomorrow_start}}", tomorrow_start.strftime("%Y-%m-%dT%H:%M:%S"))
        prompt = prompt.replace("{{tomorrow_end}}", tomorrow_end.strftime("%Y-%m-%dT%H:%M:%S"))
        prompt = prompt.replace("{{include_all_day}}", str(config.settings.include_all_day).lower())
        prompt = prompt.replace("{{include_tentative}}", str(config.settings.include_tentative).lower())
        prompt = prompt.replace("{{max_today_events}}", str(config.settings.max_today_events))
        prompt = prompt.replace("{{max_tomorrow_events}}", str(config.settings.max_tomorrow_events))

        # Call Claude with MCP tools
        response = self._run_claude(
            prompt,
            mcp_config_path=mcp_config_path,
        )

        # Parse JSON response
        json_str = extract_json(response)
        calendar_data = json.loads(json_str)

        # Return as DataSource
        source = DataSource(
            name="calendar",
            data=calendar_data,
            prompt_fragment_path=Path("prompts/sources/calendar.md"),
        )

        return TransformerIO(data={"calendar": source})

    def _run_claude(self, prompt: str, mcp_config_path: str | None = None) -> str:
        """Run Claude with MCP tools enabled."""
        mcp_config = Path(mcp_config_path) if mcp_config_path else None
        return run_claude(
            prompt,
            allowed_tools=self.MCP_TOOLS,
            mcp_config=mcp_config,
        )

    def _format_calendars(self, calendars: list) -> str:
        if not calendars:
            return "(No calendars configured)"
        lines = []
        for cal in calendars:
            if not cal.enabled:
                continue
            tz_note = f", timezone: {cal.timezone}" if cal.timezone else ""
            lines.append(f"- **{cal.name}** (ID: `{cal.id}`, type: {cal.type}{tz_note})")
        return "\n".join(lines) if lines else "(No calendars enabled)"

    def _format_event_rules(self, rules: list) -> str:
        if not rules:
            return "No specific event rules configured."

        rules_by_type: dict[str, list[str]] = {
            "always_skip": [],
            "always_mention": [],
            "canceled_only": [],
        }

        for rule in rules:
            calendar_note = f" (in {rule.calendar})" if rule.calendar else ""
            rule_list = rules_by_type.get(rule.rule)
            if rule_list is not None:
                rule_list.append(f'  - Pattern: "{rule.pattern}"{calendar_note}')

        sections = []

        if rules_by_type["always_skip"]:
            sections.append("**Events to SKIP entirely:**")
            sections.extend(rules_by_type["always_skip"])

        if rules_by_type["always_mention"]:
            sections.append("\n**Events to ALWAYS include:**")
            sections.extend(rules_by_type["always_mention"])

        if rules_by_type["canceled_only"]:
            sections.append("\n**Events to include ONLY if canceled:**")
            sections.extend(rules_by_type["canceled_only"])

        return "\n".join(sections) if sections else "No specific event rules configured."

    def _format_notable_patterns(self, patterns: list) -> str:
        if not patterns:
            return "Use your judgment for what counts as notable."
        quoted = ", ".join(f'"{p}"' for p in patterns)
        return f"Events containing these keywords are always notable: {quoted}"
