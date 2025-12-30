# v2b Slack Integration Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add Slack as a data source to Murmur briefings, solving MCP credential passing for all future MCP sources.

**Architecture:**
- Create `.mcp.json` configuration file for MCP server definitions
- Modify `claude.py` to support MCP tools via `--mcp-config` flag
- Add `slack-fetcher` transformer that uses MCP Slack tools
- Update planner prompt to integrate Slack context

**Tech Stack:** Python, Claude CLI with MCP, Docker-based Slack MCP server, YAML config

---

## Prerequisites

Before starting, ensure you have:
- Docker installed and running
- Slack workspace access with ability to create apps
- A Slack User Token (xoxp-*) with appropriate scopes

---

## Task 1: Create MCP Configuration File

**Files:**
- Create: `.mcp.json`
- Create: `.env.example` (update)

**Step 1: Create MCP config file**

Create `.mcp.json` in project root:

```json
{
  "mcpServers": {
    "slack": {
      "type": "stdio",
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "SLACK_MCP_XOXP_TOKEN",
        "ghcr.io/korotovsky/slack-mcp-server",
        "mcp-server", "-t", "stdio"
      ],
      "env": {
        "SLACK_MCP_XOXP_TOKEN": "${SLACK_USER_TOKEN}"
      }
    }
  }
}
```

**Step 2: Update .env.example**

Add to existing `.env.example` or create if missing:

```bash
# Slack MCP Integration
SLACK_USER_TOKEN=xoxp-your-user-token-here
```

**Step 3: Add .env to .gitignore if not present**

Check `.gitignore` includes `.env` (it should already).

**Step 4: Commit**

```bash
git add .mcp.json .env.example
git commit -m "feat(v2b): add MCP configuration for Slack server"
```

---

## Task 2: Update Claude Runner for MCP Support

**Files:**
- Modify: `src/murmur/claude.py`
- Create: `tests/test_claude.py`

**Step 1: Write the failing test**

Create `tests/test_claude.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_run_claude_with_mcp_config():
    """MCP config path should be passed to claude CLI."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        mcp_config = Path("/tmp/test.mcp.json")
        run_claude("test prompt", mcp_config=mcp_config)

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--mcp-config" in cmd
        assert str(mcp_config) in cmd


def test_run_claude_without_mcp_config():
    """When no MCP config, --mcp-config should not be in command."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        run_claude("test prompt")

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--mcp-config" not in cmd


def test_run_claude_with_mcp_tools():
    """MCP tools should be included in allowedTools."""
    from murmur.claude import run_claude

    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="test output",
            stderr=""
        )

        run_claude(
            "test prompt",
            allowed_tools=["mcp__slack__channels_list", "mcp__slack__conversations_history"],
            mcp_config=Path("/tmp/test.mcp.json")
        )

        call_args = mock_run.call_args
        cmd = call_args[0][0]

        assert "--allowedTools" in cmd
        idx = cmd.index("--allowedTools")
        tools_arg = cmd[idx + 1]
        assert "mcp__slack__channels_list" in tools_arg
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_claude.py -v
```

Expected: FAIL with signature mismatch or missing parameter

**Step 3: Update claude.py to support MCP config**

```python
import subprocess
from pathlib import Path


class ClaudeError(Exception):
    """Raised when Claude subprocess fails."""
    pass


def run_claude(
    prompt: str,
    allowed_tools: list[str] | None = None,
    cwd: Path | None = None,
    timeout: int = 600,
    mcp_config: Path | None = None,
) -> str:
    """
    Run Claude CLI in headless mode and return response.

    Args:
        prompt: The prompt to send to Claude
        allowed_tools: Optional list of tools to allow (e.g., ["WebSearch", "mcp__slack__channels_list"])
        cwd: Working directory for subprocess
        timeout: Timeout in seconds (default 10 minutes)
        mcp_config: Path to MCP configuration file (e.g., .mcp.json)

    Returns:
        Claude's response text

    Raises:
        ClaudeError: If subprocess fails
    """
    cmd = [
        "claude",
        "--print",
        "--dangerously-skip-permissions",
        "--no-session-persistence",
        "--setting-sources", "",  # Don't load user/project settings (avoids skills)
    ]

    # Add MCP config if provided
    if mcp_config:
        cmd.extend(["--mcp-config", str(mcp_config)])

    if allowed_tools:
        cmd.extend(["--allowedTools", ",".join(allowed_tools)])
    else:
        # No tools needed - just generate text
        cmd.extend(["--tools", ""])

    result = subprocess.run(
        cmd,
        input=prompt,
        capture_output=True,
        text=True,
        cwd=cwd,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise ClaudeError(result.stderr or f"Claude exited with code {result.returncode}")

    return result.stdout
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_claude.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/claude.py tests/test_claude.py
git commit -m "feat(v2b): add MCP config support to Claude runner"
```

---

## Task 3: Create Slack Configuration Schema

**Files:**
- Create: `src/murmur/config/slack.py`
- Create: `config/slack.yaml`
- Create: `tests/test_slack_config.py`

**Step 1: Write the failing test**

Create `tests/test_slack_config.py`:

```python
import pytest
from pathlib import Path
import tempfile
import yaml


def test_load_slack_config():
    """Load Slack config from YAML file."""
    from murmur.config.slack import load_slack_config, SlackConfig

    config_data = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
            {"name": "random", "id": "C456", "priority": "low"},
        ],
        "colleagues": [
            {"name": "Alice", "slack_id": "U123"},
        ],
        "projects": [
            {"name": "Project X", "keywords": ["projectx", "px"]},
        ],
        "settings": {
            "lookback_hours": 24,
            "include_threads": True,
        }
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        config = load_slack_config(config_path)

        assert isinstance(config, SlackConfig)
        assert len(config.channels) == 2
        assert config.channels[0].name == "general"
        assert config.channels[0].priority == "high"
        assert len(config.colleagues) == 1
        assert config.colleagues[0].name == "Alice"
        assert config.settings.lookback_hours == 24
    finally:
        config_path.unlink()


def test_slack_config_defaults():
    """Empty config should use sensible defaults."""
    from murmur.config.slack import load_slack_config

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump({}, f)
        config_path = Path(f.name)

    try:
        config = load_slack_config(config_path)

        assert config.channels == []
        assert config.settings.lookback_hours == 24
        assert config.settings.include_threads == True
    finally:
        config_path.unlink()
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_slack_config.py -v
```

Expected: FAIL with ModuleNotFoundError

**Step 3: Create config module**

Create `src/murmur/config/__init__.py`:

```python
"""Configuration modules for Murmur."""
```

Create `src/murmur/config/slack.py`:

```python
"""Slack configuration schema."""

from dataclasses import dataclass, field
from pathlib import Path
import yaml


@dataclass
class SlackChannel:
    """A Slack channel to monitor."""
    name: str
    id: str = ""
    priority: str = "medium"


@dataclass
class SlackColleague:
    """A colleague whose messages are prioritized."""
    name: str
    slack_id: str = ""


@dataclass
class SlackProject:
    """A project to watch for keyword mentions."""
    name: str
    keywords: list[str] = field(default_factory=list)


@dataclass
class SlackSettings:
    """Slack monitoring settings."""
    lookback_hours: int = 24
    include_threads: bool = True
    min_message_length: int = 10


@dataclass
class SlackConfig:
    """Complete Slack configuration."""
    channels: list[SlackChannel] = field(default_factory=list)
    colleagues: list[SlackColleague] = field(default_factory=list)
    projects: list[SlackProject] = field(default_factory=list)
    settings: SlackSettings = field(default_factory=SlackSettings)


def load_slack_config(path: Path) -> SlackConfig:
    """Load Slack configuration from YAML file."""
    if not path.exists():
        return SlackConfig()

    with open(path) as f:
        data = yaml.safe_load(f) or {}

    channels = [
        SlackChannel(**ch) for ch in data.get("channels", [])
    ]

    colleagues = [
        SlackColleague(**col) for col in data.get("colleagues", [])
    ]

    projects = [
        SlackProject(**proj) for proj in data.get("projects", [])
    ]

    settings_data = data.get("settings", {})
    settings = SlackSettings(
        lookback_hours=settings_data.get("lookback_hours", 24),
        include_threads=settings_data.get("include_threads", True),
        min_message_length=settings_data.get("min_message_length", 10),
    )

    return SlackConfig(
        channels=channels,
        colleagues=colleagues,
        projects=projects,
        settings=settings,
    )
```

**Step 4: Create example slack.yaml**

Create `config/slack.yaml`:

```yaml
# Slack Configuration
# Define channels, projects, and colleagues to monitor

channels:
  # Add your channels here
  # - name: "general"
  #   id: "C123456789"  # Get from channel details in Slack
  #   priority: high    # high, medium, low

colleagues:
  # People whose messages are always interesting
  # - name: "Alice"
  #   slack_id: "U123456789"

projects:
  # Keywords to search for
  # - name: "Project X"
  #   keywords: ["projectx", "project-x"]

settings:
  lookback_hours: 24
  include_threads: true
  min_message_length: 10
```

**Step 5: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_slack_config.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/config/ config/slack.yaml tests/test_slack_config.py
git commit -m "feat(v2b): add Slack configuration schema and loader"
```

---

## Task 4: Create Slack Fetcher Transformer

**Files:**
- Create: `src/murmur/transformers/slack_fetcher.py`
- Create: `prompts/slack_gather.md`
- Modify: `src/murmur/registry.py`
- Create: `tests/test_slack_fetcher.py`

**Step 1: Write the failing test**

Create `tests/test_slack_fetcher.py`:

```python
import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import yaml


def test_slack_fetcher_generates_prompt():
    """Slack fetcher should generate proper gathering prompt."""
    from murmur.transformers.slack_fetcher import SlackFetcher
    from murmur.core import TransformerIO

    # Create temp config
    config_data = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
        ],
        "settings": {"lookback_hours": 24}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = SlackFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"messages": [], "mentions": []}'

            result = fetcher.process(TransformerIO(data={
                "slack_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            # Check Claude was called
            assert mock_claude.called
            prompt = mock_claude.call_args[0][0]

            # Prompt should include channel info
            assert "general" in prompt
            assert "C123" in prompt
    finally:
        config_path.unlink()


def test_slack_fetcher_uses_mcp_tools():
    """Slack fetcher should use MCP Slack tools."""
    from murmur.transformers.slack_fetcher import SlackFetcher

    fetcher = SlackFetcher()

    # Check declared effects
    assert "mcp:slack" in fetcher.input_effects


def test_slack_fetcher_output_structure():
    """Slack fetcher should output slack_data key."""
    from murmur.transformers.slack_fetcher import SlackFetcher

    fetcher = SlackFetcher()
    assert "slack_data" in fetcher.outputs
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_slack_fetcher.py -v
```

Expected: FAIL with ModuleNotFoundError

**Step 3: Create the slack gather prompt**

Create `prompts/slack_gather.md`:

```markdown
You are gathering Slack data for a daily briefing. Use the Slack MCP tools to fetch relevant messages.

## Channels to Monitor

{{channels}}

## Key People

{{colleagues}}

## Projects to Track

{{projects}}

## Settings

- Lookback: {{lookback_hours}} hours
- Include thread replies: {{include_threads}}

## Instructions

1. Use `mcp__slack__channels_list` to verify channel IDs if needed
2. Use `mcp__slack__conversations_history` for each priority channel
3. Use `mcp__slack__conversations_search_messages` to find project keyword mentions
4. Focus on:
   - Important announcements
   - Decisions being made
   - Questions needing attention
   - Messages from key colleagues
   - Threads with significant discussion

## Output Format

Return JSON:

```json
{
  "messages": [
    {
      "channel_name": "string",
      "channel_id": "string",
      "author": "string",
      "text": "string",
      "timestamp": "ISO datetime",
      "thread_reply_count": 0,
      "importance": "high|medium|low"
    }
  ],
  "mentions": [
    // Messages mentioning tracked projects/keywords
  ],
  "summary": "Brief summary of what's happening in Slack"
}
```

Return ONLY the JSON, no other text.
```

**Step 4: Create the slack fetcher transformer**

Create `src/murmur/transformers/slack_fetcher.py`:

```python
"""Slack data fetcher using MCP tools."""

import json
import re
from pathlib import Path
from murmur.core import Transformer, TransformerIO
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
    outputs = ["slack_data"]
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

        return TransformerIO(data={"slack_data": slack_data})

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
```

**Step 5: Register the transformer**

Update `src/murmur/registry.py` to import and register:

```python
from murmur.transformers.slack_fetcher import SlackFetcher

# In the register_defaults method or wherever transformers are registered:
registry.register(SlackFetcher())
```

**Step 6: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_slack_fetcher.py -v
```

Expected: PASS

**Step 7: Commit**

```bash
git add src/murmur/transformers/slack_fetcher.py prompts/slack_gather.md src/murmur/registry.py tests/test_slack_fetcher.py
git commit -m "feat(v2b): add Slack fetcher transformer with MCP integration"
```

---

## Task 5: Update Brief Planner to Handle Slack Data

**Files:**
- Modify: `src/murmur/transformers/brief_planner_v2.py`
- Modify: `prompts/plan_v2.md`
- Create: `tests/test_planner_with_slack.py`

**Step 1: Write the failing test**

Create `tests/test_planner_with_slack.py`:

```python
import pytest
from unittest.mock import patch, MagicMock


def test_planner_accepts_slack_input():
    """Planner should accept optional slack_data input."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Check slack_data is in inputs
    assert "slack_data" in planner.inputs


def test_planner_includes_slack_in_prompt():
    """Planner should include Slack data in prompt when provided."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch.object(planner, '_format_slack_data') as mock_format:
        mock_format.return_value = "## Slack Highlights\n- Important message"

        with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
            mock_claude.return_value = '{"sections": []}'

            slack_data = {
                "messages": [{"text": "test", "author": "Alice"}],
                "summary": "Test summary"
            }

            planner.process(TransformerIO(data={
                "gathered_data": {"items": []},
                "story_context": [],
                "slack_data": slack_data,
            }))

            # Check prompt includes Slack section
            prompt = mock_claude.call_args[0][0]
            assert "Slack" in prompt or "slack" in prompt.lower()
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_planner_with_slack.py -v
```

Expected: FAIL because slack_data not in inputs

**Step 3: Update the planner transformer**

Modify `src/murmur/transformers/brief_planner_v2.py`:

```python
# Update inputs list
inputs = ["gathered_data", "story_context", "slack_data"]  # Add slack_data

# Update process method to handle slack_data
def process(self, input: TransformerIO) -> TransformerIO:
    gathered_data = input.data.get("gathered_data", {})
    story_context = input.data.get("story_context", [])
    slack_data = input.data.get("slack_data")  # Optional

    # Format inputs for prompt
    gathered_text = json.dumps(gathered_data, indent=2)
    context_text = self._format_story_context(story_context)
    slack_text = self._format_slack_data(slack_data) if slack_data else ""

    # Load and fill prompt template
    prompt_template = PROMPT_PATH.read_text()
    prompt = prompt_template.replace("{{story_context}}", context_text)
    prompt = prompt_template.replace("{{gathered_data}}", gathered_text)
    prompt = prompt.replace("{{slack_highlights}}", slack_text)

    # ... rest of method

def _format_slack_data(self, slack_data: dict) -> str:
    """Format Slack data for the planning prompt."""
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
```

**Step 4: Update the planner prompt**

Modify `prompts/plan_v2.md` to add Slack section:

Add after the Story Context section:

```markdown
## Slack Highlights

{{slack_highlights}}

When Slack data is present:
- Consider mentioning notable team discussions
- Reference decisions that affect the user
- Note any direct messages or mentions
- Weave workplace context naturally into the briefing
```

**Step 5: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_planner_with_slack.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/transformers/brief_planner_v2.py prompts/plan_v2.md tests/test_planner_with_slack.py
git commit -m "feat(v2b): integrate Slack data into brief planner"
```

---

## Task 6: Create v2b Graph Configuration

**Files:**
- Create: `config/graphs/full-v2b.yaml`
- Modify: `config/profiles/default.yaml` (optional - can keep v2a as default)

**Step 1: Create the v2b graph**

Create `config/graphs/full-v2b.yaml`:

```yaml
name: full-v2b

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

  - name: dedupe
    transformer: story-deduplicator
    inputs:
      news_items: $gather.gathered_data
      history_path: $config.history_path

  - name: plan
    transformer: brief-planner-v2
    inputs:
      gathered_data: $dedupe.filtered_news
      story_context: $dedupe.story_context
      slack_data: $slack.slack_data

  - name: generate
    transformer: script-generator
    inputs:
      plan: $plan.plan
      gathered_data: $dedupe.filtered_news
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

**Step 2: Create a Slack-enabled profile**

Create `config/profiles/work.yaml`:

```yaml
name: work
graph: full-v2b
config:
  news_topics_file: news_topics.yaml
  slack_config_path: config/slack.yaml
  mcp_config_path: .mcp.json
  piper_model: en_US-amy-medium
  sentence_silence: 0.3
  narrator_style: warm-professional
  target_duration: 5
  history_path: data/history/work.json
```

**Step 3: Commit**

```bash
git add config/graphs/full-v2b.yaml config/profiles/work.yaml
git commit -m "feat(v2b): add v2b graph and work profile with Slack integration"
```

---

## Task 7: Update Script Generator for Multi-Source Data

**Files:**
- Modify: `src/murmur/transformers/script_generator.py`
- Modify: `prompts/generate.md`

**Step 1: Update script generator to note multi-source context**

The script generator already receives data through the planner's output. The main change is updating the generation prompt to acknowledge that data may come from multiple sources.

Modify `prompts/generate.md`:

Add after the Original News Data section:

```markdown
## Data Sources

The briefing plan may include content from multiple sources:
- **News**: Web search results on topics of interest
- **Slack**: Workplace messages and discussions (if configured)

When Slack content is included in the plan:
- Weave workplace context naturally ("Speaking of work...")
- Keep colleague names but avoid sensitive details
- Focus on decisions, announcements, and interesting discussions
- Transition smoothly between news and workplace topics
```

**Step 2: Commit**

```bash
git add prompts/generate.md
git commit -m "feat(v2b): update script generator prompt for multi-source data"
```

---

## Task 8: Integration Test

**Files:**
- Create: `tests/integration/test_v2b_pipeline.py`

**Step 1: Create integration test**

Create `tests/integration/test_v2b_pipeline.py`:

```python
"""Integration test for v2b pipeline with Slack."""

import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
import yaml
import tempfile


@pytest.fixture
def mock_slack_config(tmp_path):
    """Create a temporary Slack config."""
    config = {
        "channels": [
            {"name": "general", "id": "C123", "priority": "high"},
        ],
        "settings": {"lookback_hours": 24}
    }
    config_path = tmp_path / "slack.yaml"
    with open(config_path, 'w') as f:
        yaml.dump(config, f)
    return config_path


@pytest.fixture
def mock_mcp_config(tmp_path):
    """Create a temporary MCP config."""
    config = {
        "mcpServers": {
            "slack": {
                "type": "stdio",
                "command": "echo",
                "args": ["test"]
            }
        }
    }
    config_path = tmp_path / ".mcp.json"
    with open(config_path, 'w') as f:
        import json
        json.dump(config, f)
    return config_path


def test_v2b_graph_loads(mock_slack_config, mock_mcp_config):
    """v2b graph should load and validate."""
    from murmur.graph import load_graph, validate_graph
    from murmur.registry import TransformerRegistry

    graph_path = Path("config/graphs/full-v2b.yaml")
    if not graph_path.exists():
        pytest.skip("v2b graph not yet created")

    graph = load_graph(graph_path)
    registry = TransformerRegistry()
    registry.register_defaults()

    # Should not raise
    validate_graph(graph, registry)


def test_slack_fetcher_in_registry():
    """Slack fetcher should be registered."""
    from murmur.registry import TransformerRegistry

    registry = TransformerRegistry()
    registry.register_defaults()

    fetcher = registry.get("slack-fetcher")
    assert fetcher is not None
    assert fetcher.name == "slack-fetcher"


def test_planner_handles_missing_slack():
    """Planner should work without Slack data."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0}'

        # No slack_data provided
        result = planner.process(TransformerIO(data={
            "gathered_data": {"items": []},
            "story_context": [],
        }))

        assert result.data.get("plan") is not None
```

**Step 2: Run integration tests**

```bash
.venv/bin/pytest tests/integration/test_v2b_pipeline.py -v
```

Expected: PASS (with skips for unimplemented parts)

**Step 3: Commit**

```bash
git add tests/integration/test_v2b_pipeline.py
git commit -m "test(v2b): add integration tests for Slack pipeline"
```

---

## Task 9: Documentation

**Files:**
- Modify: `README.md` or create `docs/slack-setup.md`

**Step 1: Document Slack setup**

Create `docs/slack-setup.md`:

```markdown
# Slack Integration Setup

Murmur can integrate Slack messages into your daily briefings using the MCP (Model Context Protocol) Slack server.

## Prerequisites

1. Docker installed and running
2. A Slack workspace where you can create apps
3. A Slack User Token (xoxp-*)

## Getting a Slack Token

1. Go to https://api.slack.com/apps
2. Create a new app (or use existing)
3. Under "OAuth & Permissions", add these scopes:
   - `channels:history`
   - `channels:read`
   - `search:read`
   - `users:read`
4. Install the app to your workspace
5. Copy the "User OAuth Token" (starts with `xoxp-`)

## Configuration

1. Create `.env` file with your token:

```bash
SLACK_USER_TOKEN=xoxp-your-token-here
```

2. Configure channels in `config/slack.yaml`:

```yaml
channels:
  - name: "general"
    id: "C123456789"  # Get from channel details
    priority: high

colleagues:
  - name: "Alice"
    slack_id: "U123456789"

settings:
  lookback_hours: 24
  include_threads: true
```

3. Use the `work` profile to include Slack:

```bash
murmur generate --profile work
```

## Finding Channel and User IDs

- **Channel ID**: Right-click channel name → "Copy link" → ID is at end of URL
- **User ID**: Click profile → "More" → "Copy member ID"

## Troubleshooting

### Docker not running
Ensure Docker Desktop is running before generating briefs.

### Token errors
Verify your token starts with `xoxp-` and has the required scopes.

### No messages found
Check that lookback_hours covers the time range you expect.
```

**Step 2: Commit**

```bash
git add docs/slack-setup.md
git commit -m "docs(v2b): add Slack integration setup guide"
```

---

## Summary

After completing all tasks, you will have:

1. **MCP Configuration** (`.mcp.json`) - Defines the Slack MCP server
2. **Updated Claude Runner** - Supports `--mcp-config` flag
3. **Slack Config Schema** - Pydantic models for `slack.yaml`
4. **Slack Fetcher Transformer** - Uses MCP tools to gather Slack data
5. **Updated Planner** - Integrates Slack highlights into briefing plans
6. **v2b Graph** - Full pipeline with Slack integration
7. **Work Profile** - Pre-configured for Slack-enabled briefings
8. **Documentation** - Setup guide for Slack integration

## Testing the Full Pipeline

```bash
# 1. Set up environment
cp .env.example .env
# Edit .env with your SLACK_USER_TOKEN

# 2. Configure Slack channels
# Edit config/slack.yaml with your channels

# 3. Run with Slack integration
murmur generate --profile work

# 4. Check output
ls output/
```

## Next Steps (v2c)

The v2c phase will add GitHub integration following the same pattern:
- Create `github-fetcher` transformer
- Add GitHub MCP server to `.mcp.json`
- Create `config/github.yaml` schema
- Update planner to include commits/PRs
