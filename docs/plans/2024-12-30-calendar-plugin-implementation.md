# Calendar Plugin Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Google Calendar as a data source, fetching today's remaining events and tomorrow's notable events via MCP tools.

**Architecture:** Follows the established Slack plugin pattern - config schema, transformer, gather prompt, planner fragment. The CalendarFetcher calls Claude with MCP tools to fetch events, applies event rules, and outputs a DataSource for the planner.

**Tech Stack:** Python dataclasses, YAML config, MCP google-calendar tools, pytest

---

## Task 1: Config Schema

**Files:**
- Create: `src/murmur/config/calendar.py`
- Test: `tests/murmur/config/test_calendar_config.py`

**Step 1: Write the failing test**

Create `tests/murmur/config/test_calendar_config.py`:

```python
"""Tests for Calendar configuration schema."""

import pytest
from pathlib import Path
import tempfile
import yaml


def test_load_calendar_config():
    """Load Calendar config from YAML file."""
    from murmur.config.calendar import load_calendar_config, CalendarConfig

    config_data = {
        "calendars": [
            {"name": "Personal", "id": "personal@gmail.com", "type": "personal", "enabled": True},
            {"name": "Work", "id": "work@company.com", "type": "work", "timezone": "America/Los_Angeles"},
        ],
        "event_rules": [
            {"pattern": "^Home$", "rule": "always_skip", "calendar": "Work"},
            {"pattern": "Interview", "rule": "always_mention", "priority": "high"},
        ],
        "notable_patterns": ["flight", "doctor", "interview"],
        "settings": {
            "display_timezone": "America/New_York",
            "include_all_day": True,
            "max_today_events": 10,
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_calendar_config(config_path)

        assert isinstance(config, CalendarConfig)
        assert len(config.calendars) == 2
        assert config.calendars[0].name == "Personal"
        assert config.calendars[1].timezone == "America/Los_Angeles"
        assert len(config.event_rules) == 2
        assert config.event_rules[0].rule == "always_skip"
        assert config.notable_patterns == ["flight", "doctor", "interview"]
        assert config.settings.display_timezone == "America/New_York"
    finally:
        config_path.unlink()


def test_calendar_config_defaults():
    """Empty config should use sensible defaults."""
    from murmur.config.calendar import load_calendar_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({}, f)
        config_path = Path(f.name)

    try:
        config = load_calendar_config(config_path)

        assert config.calendars == []
        assert config.event_rules == []
        assert config.notable_patterns == []
        assert config.settings.display_timezone == "America/New_York"
        assert config.settings.include_all_day == True
        assert config.settings.max_today_events == 10
    finally:
        config_path.unlink()


def test_calendar_config_missing_file():
    """Missing config file should return empty config."""
    from murmur.config.calendar import load_calendar_config

    config = load_calendar_config(Path("/nonexistent/config.yaml"))

    assert config.calendars == []
    assert config.settings.display_timezone == "America/New_York"
```

**Step 2: Run test to verify it fails**

Run: `devbox run -- pytest tests/murmur/config/test_calendar_config.py -v`
Expected: FAIL with "No module named 'murmur.config.calendar'"

**Step 3: Write minimal implementation**

Create `src/murmur/config/calendar.py`:

```python
"""Calendar configuration schema."""

from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class Calendar:
    """A Google Calendar to monitor."""
    name: str
    id: str
    type: str = "personal"
    enabled: bool = True
    timezone: str = ""


@dataclass
class EventRule:
    """A rule for filtering events."""
    pattern: str
    rule: str  # always_skip, always_mention, canceled_only
    calendar: str = ""
    priority: str = "medium"


@dataclass
class CalendarSettings:
    """Calendar monitoring settings."""
    display_timezone: str = "America/New_York"
    include_all_day: bool = True
    include_tentative: bool = True
    include_declined: bool = False
    max_today_events: int = 10
    max_tomorrow_events: int = 5


@dataclass
class CalendarConfig:
    """Complete Calendar configuration."""
    calendars: list[Calendar] = field(default_factory=list)
    event_rules: list[EventRule] = field(default_factory=list)
    notable_patterns: list[str] = field(default_factory=list)
    settings: CalendarSettings = field(default_factory=CalendarSettings)


def load_calendar_config(path: Path) -> CalendarConfig:
    """Load Calendar configuration from YAML file."""
    if not path.exists():
        return CalendarConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    calendars = [
        Calendar(**cal) for cal in data.get("calendars", [])
    ]

    event_rules = [
        EventRule(**rule) for rule in data.get("event_rules", [])
    ]

    notable_patterns = data.get("notable_patterns", [])

    settings_data = data.get("settings", {})
    settings = CalendarSettings(
        display_timezone=settings_data.get("display_timezone", "America/New_York"),
        include_all_day=settings_data.get("include_all_day", True),
        include_tentative=settings_data.get("include_tentative", True),
        include_declined=settings_data.get("include_declined", False),
        max_today_events=settings_data.get("max_today_events", 10),
        max_tomorrow_events=settings_data.get("max_tomorrow_events", 5),
    )

    return CalendarConfig(
        calendars=calendars,
        event_rules=event_rules,
        notable_patterns=notable_patterns,
        settings=settings,
    )
```

**Step 4: Run test to verify it passes**

Run: `devbox run -- pytest tests/murmur/config/test_calendar_config.py -v`
Expected: PASS (3 tests)

**Step 5: Commit**

```bash
git add src/murmur/config/calendar.py tests/murmur/config/test_calendar_config.py
git commit -m "feat(calendar): add config schema with calendars, rules, patterns"
```

---

## Task 2: User Config File

**Files:**
- Create: `config/calendar.yaml`

**Step 1: Create user config**

Copy from prototype at `~/Working/daily_brief/_claude/config/calendar_config.yaml` to `config/calendar.yaml`:

```yaml
# Google Calendar Configuration
# Define calendars to monitor and event filtering rules

calendars:
  - name: "Personal"
    id: "fkberthold@gmail.com"
    type: personal
    enabled: true

  - name: "Work"
    id: "frank@crossnokaye.com"
    type: work
    enabled: true
    timezone: America/Los_Angeles

  - name: "Family"
    id: "family16459435491078377737@group.calendar.google.com"
    type: personal
    enabled: true

event_rules:
  - pattern: "^Home$"
    rule: always_skip
    calendar: Work

  - pattern: "^Deep Work$"
    rule: always_skip
    calendar: Work

  - pattern: "Standup"
    rule: canceled_only
    calendar: Work

  - pattern: "Interview"
    rule: always_mention
    priority: high

  - pattern: "On-Call"
    rule: always_mention
    priority: high

notable_patterns:
  - "flight"
  - "dentist"
  - "doctor"
  - "vacation"
  - "PTO"
  - "birthday"
  - "interview"
  - "presentation"
  - "launch"
  - "deadline"
  - "appointment"
  - "travel"
  - "conference"

settings:
  include_all_day: true
  include_declined: false
  include_tentative: true
  max_today_events: 10
  max_tomorrow_events: 5
  display_timezone: America/New_York
```

**Step 2: Commit**

```bash
git add config/calendar.yaml
git commit -m "config: add calendar.yaml with user's calendars and rules"
```

---

## Task 3: Gather Prompt Template

**Files:**
- Create: `prompts/calendar_gather.md`

**Step 1: Create gather prompt**

```markdown
You are gathering Google Calendar events for a daily briefing. Use the Google Calendar MCP tools to fetch relevant events.

## Calendars to Check

{{calendars}}

## Time Windows

Fetch events for TWO time windows:

**Today's remaining events:**
- From: {{today_start}}
- To: {{today_end}}
- Purpose: Show what's left on today's schedule

**Tomorrow's events:**
- From: {{tomorrow_start}}
- To: {{tomorrow_end}}
- Purpose: Identify notable events to mention in advance

Use timezone: {{display_timezone}}

## Event Rules

{{event_rules}}

## Notable Event Detection (for tomorrow)

{{notable_patterns}}

For tomorrow's events, distinguish between:
- **Notable events**: Appointments, travel, special occasions, interviews, presentations
- **Routine events**: Daily standups, recurring 1:1s, regular team meetings

## Settings

- Include all-day events: {{include_all_day}}
- Include tentative events: {{include_tentative}}
- Max today events: {{max_today_events}}
- Max tomorrow notable: {{max_tomorrow_events}}

## Instructions

1. Use `mcp__google-calendar__list-events` for each enabled calendar
   - Pass the calendar ID and time range
   - Use timeZone parameter set to {{display_timezone}}
2. For today: include all events from now until end of day
3. For tomorrow: filter to only notable events (non-routine)
4. Apply event rules:
   - Skip events matching "always_skip" patterns
   - Always include events matching "always_mention" patterns
   - For "canceled_only" patterns, only include if status is "cancelled"
5. Include canceled events that match canceled_only rules

## Output Format

Return JSON:

```json
{
  "today_events": [
    {
      "calendar_name": "string",
      "calendar_type": "personal|work",
      "title": "string",
      "start_time": "ISO datetime",
      "end_time": "ISO datetime",
      "is_all_day": boolean,
      "location": "string or null",
      "status": "confirmed|tentative|cancelled",
      "is_recurring": boolean,
      "attendee_count": number
    }
  ],
  "tomorrow_notable": [
    // Same structure, but only non-routine events for tomorrow
  ],
  "canceled_events": [
    // Events that were canceled (matching canceled_only rules)
  ],
  "summary": "Brief summary of schedule highlights"
}
```

Return ONLY the JSON, no other text.
```

**Step 2: Commit**

```bash
git add prompts/calendar_gather.md
git commit -m "feat(calendar): add gather prompt template for MCP tools"
```

---

## Task 4: Planner Source Fragment

**Files:**
- Create: `prompts/sources/calendar.md`

**Step 1: Create planner fragment**

```markdown
## Calendar Events

The following events are from the user's Google Calendar.

{{data}}

When calendar data is present:
- Lead with today's remaining schedule if there are significant events
- Mention notable tomorrow events (appointments, travel, deadlines)
- Skip routine recurring meetings unless they were canceled
- Use natural time references ("this afternoon at 3", "tomorrow morning")
- Note scheduling conflicts or unusually busy periods
- For canceled events, briefly mention the cancellation
```

**Step 2: Commit**

```bash
git add prompts/sources/calendar.md
git commit -m "feat(calendar): add planner source fragment"
```

---

## Task 5: Calendar Fetcher Transformer

**Files:**
- Create: `src/murmur/transformers/calendar_fetcher.py`
- Test: `tests/test_calendar_fetcher.py`

**Step 1: Write the failing tests**

Create `tests/test_calendar_fetcher.py`:

```python
"""Tests for Calendar fetcher transformer."""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml


def test_calendar_fetcher_generates_prompt():
    """Calendar fetcher should generate proper gathering prompt."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO

    config_data = {
        "calendars": [
            {"name": "Personal", "id": "personal@gmail.com", "type": "personal", "enabled": True},
        ],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "No events"}'

            result = fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            assert mock_claude.called
            prompt = mock_claude.call_args[0][0]

            # Prompt should include calendar info
            assert "Personal" in prompt
            assert "personal@gmail.com" in prompt
    finally:
        config_path.unlink()


def test_calendar_fetcher_uses_mcp_tools():
    """Calendar fetcher should use MCP Google Calendar tools."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher

    fetcher = CalendarFetcher()

    assert "mcp:google-calendar" in fetcher.input_effects


def test_calendar_fetcher_output_structure():
    """Calendar fetcher should output calendar key."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher

    fetcher = CalendarFetcher()
    assert "calendar" in fetcher.outputs


def test_calendar_fetcher_outputs_data_source():
    """Calendar fetcher should output a DataSource object."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO, DataSource

    config_data = {
        "calendars": [{"name": "Personal", "id": "personal@gmail.com", "enabled": True}],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "Free day"}'

            result = fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            assert "calendar" in result.data
            source = result.data["calendar"]
            assert isinstance(source, DataSource)
            assert source.name == "calendar"
            assert "today_events" in source.data
            assert source.prompt_fragment_path == Path("prompts/sources/calendar.md")
    finally:
        config_path.unlink()


def test_calendar_fetcher_formats_event_rules():
    """Calendar fetcher should format event rules in prompt."""
    from murmur.transformers.calendar_fetcher import CalendarFetcher
    from murmur.core import TransformerIO

    config_data = {
        "calendars": [{"name": "Work", "id": "work@company.com", "enabled": True}],
        "event_rules": [
            {"pattern": "^Home$", "rule": "always_skip", "calendar": "Work"},
            {"pattern": "Interview", "rule": "always_mention"},
        ],
        "notable_patterns": ["flight", "doctor"],
        "settings": {"display_timezone": "America/New_York"}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = CalendarFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"today_events": [], "tomorrow_notable": [], "summary": "No events"}'

            fetcher.process(TransformerIO(data={
                "calendar_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            prompt = mock_claude.call_args[0][0]

            # Should include event rules
            assert "always_skip" in prompt
            assert "^Home$" in prompt
            assert "Interview" in prompt

            # Should include notable patterns
            assert "flight" in prompt
            assert "doctor" in prompt
    finally:
        config_path.unlink()
```

**Step 2: Run tests to verify they fail**

Run: `devbox run -- pytest tests/test_calendar_fetcher.py -v`
Expected: FAIL with "No module named 'murmur.transformers.calendar_fetcher'"

**Step 3: Write implementation**

Create `src/murmur/transformers/calendar_fetcher.py`:

```python
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
```

**Step 4: Run tests to verify they pass**

Run: `devbox run -- pytest tests/test_calendar_fetcher.py -v`
Expected: PASS (5 tests)

**Step 5: Commit**

```bash
git add src/murmur/transformers/calendar_fetcher.py tests/test_calendar_fetcher.py
git commit -m "feat(calendar): add CalendarFetcher transformer"
```

---

## Task 6: Register Transformer

**Files:**
- Modify: `src/murmur/transformers/__init__.py`

**Step 1: Add import and registration**

Add to `src/murmur/transformers/__init__.py`:

After line 9 (`from murmur.transformers.slack_fetcher import SlackFetcher`), add:
```python
from murmur.transformers.calendar_fetcher import CalendarFetcher
```

In `create_registry()` function, after `registry.register(SlackFetcher)`, add:
```python
    registry.register(CalendarFetcher)
```

**Step 2: Run tests to verify registration works**

Run: `devbox run -- pytest tests/test_calendar_fetcher.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add src/murmur/transformers/__init__.py
git commit -m "feat(calendar): register CalendarFetcher in transformer registry"
```

---

## Task 7: Graph Integration

**Files:**
- Create: `config/graphs/full-v2c.yaml` (new graph with calendar)
- Modify: `config/profiles/work.yaml`

**Step 1: Create new graph with calendar**

Create `config/graphs/full-v2c.yaml`:

```yaml
name: full-v2c

nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics

  - name: slack
    transformer: slack-fetcher
    inputs:
      slack_config_path: $config.slack_config_path
      mcp_config_path: $config.mcp_config_path

  - name: calendar
    transformer: calendar-fetcher
    inputs:
      calendar_config_path: $config.calendar_config_path
      mcp_config_path: $config.mcp_config_path

  - name: dedupe
    transformer: story-deduplicator
    inputs:
      news_items: $gather.gathered_data
      history_path: $config.history_path

  - name: plan
    transformer: brief-planner-v2
    inputs:
      data_sources:
        - $dedupe.news
        - $slack.slack
        - $calendar.calendar
      story_context: $dedupe.story_context

  - name: generate
    transformer: script-generator
    inputs:
      plan: $plan.plan
      gathered_data: $dedupe.news
      narrator_style: $config.narrator_style
      target_duration: $config.target_duration

  - name: history
    transformer: history-updater
    inputs:
      items_to_report: $dedupe.items_to_report
      history_path: $config.history_path

  - name: synthesize
    transformer: piper-synthesizer
    inputs:
      script: $generate.script
      piper_model: $config.piper_model
      output_dir: $config.output_dir
      sentence_silence: $config.sentence_silence
```

**Step 2: Update work profile**

Add to `config/profiles/work.yaml` after `mcp_config_path`:

```yaml
  calendar_config_path: config/calendar.yaml
```

And optionally change graph to `full-v2c` if you want calendar by default.

**Step 3: Commit**

```bash
git add config/graphs/full-v2c.yaml config/profiles/work.yaml
git commit -m "feat(calendar): add v2c graph with calendar integration"
```

---

## Task 8: Integration Test

**Files:**
- Create: `tests/integration/test_calendar_integration.py`

**Step 1: Write integration test**

```python
"""Integration test for calendar in pipeline."""

import pytest
from unittest.mock import patch
from pathlib import Path
import tempfile
import yaml


def test_calendar_in_planner_data_sources():
    """Calendar DataSource should work with planner."""
    from murmur.core import DataSource

    # Create a calendar DataSource like the fetcher would
    calendar_source = DataSource(
        name="calendar",
        data={
            "today_events": [
                {
                    "calendar_name": "Work",
                    "title": "Team Standup",
                    "start_time": "2024-12-30T10:00:00",
                    "end_time": "2024-12-30T10:30:00",
                    "is_all_day": False,
                    "status": "confirmed",
                }
            ],
            "tomorrow_notable": [
                {
                    "calendar_name": "Personal",
                    "title": "Dentist Appointment",
                    "start_time": "2024-12-31T14:00:00",
                    "end_time": "2024-12-31T15:00:00",
                    "is_all_day": False,
                    "status": "confirmed",
                }
            ],
            "summary": "1 meeting today, dentist tomorrow"
        },
        prompt_fragment_path=Path("prompts/sources/calendar.md"),
    )

    # Verify DataSource structure
    assert calendar_source.name == "calendar"
    assert len(calendar_source.data["today_events"]) == 1
    assert len(calendar_source.data["tomorrow_notable"]) == 1
    assert calendar_source.prompt_fragment_path.exists()


def test_v2c_graph_loads():
    """The v2c graph with calendar should load successfully."""
    from murmur.graph import load_graph

    graph = load_graph(Path("config/graphs/full-v2c.yaml"))

    assert graph.name == "full-v2c"

    # Find calendar node
    calendar_node = None
    for node in graph.nodes:
        if node.name == "calendar":
            calendar_node = node
            break

    assert calendar_node is not None
    assert calendar_node.transformer == "calendar-fetcher"
    assert "calendar_config_path" in calendar_node.inputs
```

**Step 2: Run integration test**

Run: `devbox run -- pytest tests/integration/test_calendar_integration.py -v`
Expected: PASS

**Step 3: Commit**

```bash
git add tests/integration/test_calendar_integration.py
git commit -m "test(calendar): add integration tests for calendar pipeline"
```

---

## Task 9: Update Handoff Document

**Files:**
- Modify: `HANDOFF_NEXT_SESSION.md`

**Step 1: Update handoff with completion status**

Update the handoff document to reflect calendar plugin completion and note any remaining work (like MCP auth testing).

**Step 2: Commit**

```bash
git add HANDOFF_NEXT_SESSION.md
git commit -m "docs: update handoff with calendar plugin completion"
```

---

## Summary

9 tasks total:
1. Config schema (dataclasses + loader)
2. User config file (calendar.yaml)
3. Gather prompt template
4. Planner source fragment
5. CalendarFetcher transformer
6. Register in transformer registry
7. Graph integration (v2c graph)
8. Integration tests
9. Update handoff

Each task follows TDD where applicable and commits incrementally.
