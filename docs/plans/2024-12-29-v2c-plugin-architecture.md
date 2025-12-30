# Plugin-Friendly Data Source Architecture

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Refactor the planner to be source-agnostic so new data sources can be added without modifying planner code.

**Architecture:**
- Each data source (fetcher) outputs a standardized `DataSource` structure containing raw data plus a prompt fragment path
- The planner dynamically assembles its prompt from whatever sources are wired in
- Source-specific prompt fragments live in `prompts/sources/` and describe how to interpret that source's data
- Adding a new source = add fetcher + prompt fragment, wire in graph. No planner changes.

**Tech Stack:** Python dataclasses, YAML graphs, Markdown prompts

---

## Prerequisites

Before starting, understand:
- Current `BriefPlannerV2` has hardcoded `slack_data` input and `_format_slack_data()` method
- Current `plan_v2.md` has hardcoded `{{slack_highlights}}` placeholder
- Goal: Make these generic so planner doesn't know about specific sources

---

## Task 1: Define DataSource Protocol

**Files:**
- Create: `src/murmur/core.py` (add DataSource dataclass)
- Create: `tests/murmur/test_data_source.py`

**Step 1: Write the failing test**

Create `tests/murmur/test_data_source.py`:

```python
import pytest
from pathlib import Path


def test_data_source_structure():
    """DataSource should have name, data, and prompt_fragment_path."""
    from murmur.core import DataSource

    source = DataSource(
        name="test-source",
        data={"items": [1, 2, 3]},
        prompt_fragment_path=Path("prompts/sources/test.md"),
    )

    assert source.name == "test-source"
    assert source.data == {"items": [1, 2, 3]}
    assert source.prompt_fragment_path == Path("prompts/sources/test.md")


def test_data_source_optional_prompt():
    """DataSource prompt_fragment_path should be optional."""
    from murmur.core import DataSource

    source = DataSource(
        name="simple-source",
        data={"value": 42},
    )

    assert source.name == "simple-source"
    assert source.prompt_fragment_path is None
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/murmur/test_data_source.py -v
```

Expected: FAIL with `ImportError: cannot import name 'DataSource'`

**Step 3: Add DataSource to core.py**

Modify `src/murmur/core.py`, add after TransformerIO:

```python
@dataclass
class DataSource:
    """
    Standardized output from data source fetchers.

    Enables plugin-style architecture where:
    - Fetchers output DataSource objects
    - Planner consumes them generically without source-specific code
    - Each source provides its own prompt fragment describing how to use its data

    Attributes:
        name: Identifier for this source (e.g., "slack", "news", "github")
        data: Raw structured data from the source
        prompt_fragment_path: Path to markdown file describing how to interpret this data
    """
    name: str
    data: dict = field(default_factory=dict)
    prompt_fragment_path: Path | None = None
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/murmur/test_data_source.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/core.py tests/murmur/test_data_source.py
git commit -m "feat(v2c): add DataSource protocol for plugin architecture"
```

---

## Task 2: Create Source Prompt Fragments

**Files:**
- Create: `prompts/sources/news.md`
- Create: `prompts/sources/slack.md`

**Step 1: Create news prompt fragment**

Create `prompts/sources/news.md`:

```markdown
## News Items

The following news items were gathered from web searches on topics of interest.

{{data}}

When planning the briefing:
- Select the most important and relevant items (aim for 5-8 total across all sources)
- Group related items together
- Consider recency and impact
- Note connections between stories
```

**Step 2: Create slack prompt fragment**

Create `prompts/sources/slack.md`:

```markdown
## Slack Highlights

The following messages and activity are from the user's workplace Slack.

{{data}}

When Slack data is present:
- Consider mentioning notable team discussions
- Reference decisions that affect the user
- Note any direct messages or mentions
- Weave workplace context naturally into the briefing
- Keep colleague names but avoid sensitive details
```

**Step 3: Commit**

```bash
git add prompts/sources/
git commit -m "feat(v2c): add source-specific prompt fragments"
```

---

## Task 3: Update Slack Fetcher to Output DataSource

**Files:**
- Modify: `src/murmur/transformers/slack_fetcher.py`
- Modify: `tests/test_slack_fetcher.py`

**Step 1: Write the failing test**

Update `tests/test_slack_fetcher.py`, add new test:

```python
def test_slack_fetcher_outputs_data_source():
    """Slack fetcher should output a DataSource object."""
    from murmur.transformers.slack_fetcher import SlackFetcher
    from murmur.core import TransformerIO, DataSource
    from pathlib import Path
    import tempfile
    import yaml

    config_data = {
        "channels": [{"name": "general", "id": "C123", "priority": "high"}],
        "settings": {"lookback_hours": 24}
    }

    with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
        yaml.dump(config_data, f)
        config_path = Path(f.name)

    try:
        fetcher = SlackFetcher()

        with patch.object(fetcher, '_run_claude') as mock_claude:
            mock_claude.return_value = '{"messages": [], "summary": "No activity"}'

            result = fetcher.process(TransformerIO(data={
                "slack_config_path": str(config_path),
                "mcp_config_path": "/tmp/mcp.json",
            }))

            # Should output a DataSource
            assert "slack" in result.data
            source = result.data["slack"]
            assert isinstance(source, DataSource)
            assert source.name == "slack"
            assert "messages" in source.data
            assert source.prompt_fragment_path == Path("prompts/sources/slack.md")
    finally:
        config_path.unlink()
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/test_slack_fetcher.py::test_slack_fetcher_outputs_data_source -v
```

Expected: FAIL (outputs `slack_data` dict, not `DataSource`)

**Step 3: Update slack_fetcher.py**

Modify `src/murmur/transformers/slack_fetcher.py`:

1. Add import at top:
```python
from murmur.core import Transformer, TransformerIO, DataSource
```

2. Update outputs:
```python
outputs = ["slack"]  # Changed from "slack_data"
```

3. Update return in process():
```python
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
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/test_slack_fetcher.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/transformers/slack_fetcher.py tests/test_slack_fetcher.py
git commit -m "feat(v2c): update Slack fetcher to output DataSource"
```

---

## Task 4: Update News Pipeline to Output DataSource

**Files:**
- Modify: `src/murmur/transformers/story_deduplicator.py`
- Modify: `tests/murmur/transformers/test_story_deduplicator.py`

The news data goes through the deduplicator, so that's where we add the DataSource wrapping.

**Step 1: Write the failing test**

Add to `tests/murmur/transformers/test_story_deduplicator.py`:

```python
def test_deduplicator_outputs_news_data_source():
    """Deduplicator should output news as DataSource."""
    from murmur.transformers.story_deduplicator import StoryDeduplicator
    from murmur.core import TransformerIO, DataSource

    deduplicator = StoryDeduplicator()

    result = deduplicator.process(TransformerIO(data={
        "news_items": {"items": [{"headline": "Test", "story_key": "test-1"}]},
        "history_path": "/tmp/nonexistent.json",
    }))

    # Should output a DataSource
    assert "news" in result.data
    source = result.data["news"]
    assert isinstance(source, DataSource)
    assert source.name == "news"
    assert source.prompt_fragment_path == Path("prompts/sources/news.md")
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/murmur/transformers/test_story_deduplicator.py::test_deduplicator_outputs_news_data_source -v
```

Expected: FAIL (outputs `filtered_news` dict, not `DataSource`)

**Step 3: Update story_deduplicator.py**

Modify `src/murmur/transformers/story_deduplicator.py`:

1. Add import:
```python
from murmur.core import Transformer, TransformerIO, DataSource
```

2. Update outputs:
```python
outputs = ["news", "story_context", "items_to_report"]  # Changed filtered_news to news
```

3. Update return to wrap in DataSource:
```python
        # Wrap news in DataSource
        news_source = DataSource(
            name="news",
            data=filtered_news,
            prompt_fragment_path=Path("prompts/sources/news.md"),
        )

        return TransformerIO(data={
            "news": news_source,
            "story_context": story_context,
            "items_to_report": items_to_report,
        })
```

**Step 4: Run test to verify it passes**

```bash
.venv/bin/pytest tests/murmur/transformers/test_story_deduplicator.py -v
```

Expected: PASS

**Step 5: Commit**

```bash
git add src/murmur/transformers/story_deduplicator.py tests/murmur/transformers/test_story_deduplicator.py
git commit -m "feat(v2c): update deduplicator to output news as DataSource"
```

---

## Task 5: Refactor Planner to Accept Generic Data Sources

**Files:**
- Modify: `src/murmur/transformers/brief_planner_v2.py`
- Modify: `prompts/plan_v2.md`
- Create: `tests/murmur/transformers/test_planner_generic.py`

**Step 1: Write the failing test**

Create `tests/murmur/transformers/test_planner_generic.py`:

```python
import pytest
from unittest.mock import patch
from pathlib import Path


def test_planner_accepts_data_sources_list():
    """Planner should accept a list of DataSource objects."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Should have generic 'data_sources' input, not source-specific inputs
    assert "data_sources" in planner.inputs
    assert "slack_data" not in planner.inputs
    assert "gathered_data" not in planner.inputs


def test_planner_assembles_prompt_from_sources():
    """Planner should dynamically build prompt from DataSource fragments."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO, DataSource

    planner = BriefPlannerV2()

    # Create test sources
    news_source = DataSource(
        name="news",
        data={"items": [{"headline": "Test News"}]},
        prompt_fragment_path=Path("prompts/sources/news.md"),
    )
    slack_source = DataSource(
        name="slack",
        data={"messages": [{"text": "Hello team"}]},
        prompt_fragment_path=Path("prompts/sources/slack.md"),
    )

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0}'

        planner.process(TransformerIO(data={
            "data_sources": [news_source, slack_source],
            "story_context": [],
        }))

        # Check prompt was built with both sources
        prompt = mock_claude.call_args[0][0]
        assert "News Items" in prompt  # From news.md fragment
        assert "Slack Highlights" in prompt  # From slack.md fragment
        assert "Test News" in prompt  # Data was included
        assert "Hello team" in prompt  # Data was included
```

**Step 2: Run test to verify it fails**

```bash
.venv/bin/pytest tests/murmur/transformers/test_planner_generic.py -v
```

Expected: FAIL (planner still has source-specific inputs)

**Step 3: Update plan_v2.md prompt template**

Replace `prompts/plan_v2.md` with:

```markdown
You are a briefing planner. Your job is to select and organize items into a coherent narrative for a spoken briefing.

## Story Context

{{story_context}}

Items marked as "development" are updates to stories the user has heard before. When including these:
- Briefly acknowledge the prior coverage ("Continuing our coverage of...")
- Focus on what's NEW, not rehashing old facts
- Reference the development note for guidance

Items marked as "new" are being reported for the first time.

## Data Sources

{{data_sources}}

## Instructions

1. Select the most important and relevant items (aim for 5-8 items total)
2. Group related items together
3. Order them for natural flow (e.g., most important first, or thematic grouping)
4. Note any connections between items
5. Suggest transitions between sections
6. For developments, note how to acknowledge prior coverage
7. Weave content from different sources naturally

## Output Format

Return a JSON object with this structure:

```json
{
  "sections": [
    {
      "title": "Section name",
      "items": ["headline1", "headline2"],
      "source": "news|slack|etc",
      "connection": "How these items relate",
      "transition_to_next": "Suggested transition phrase",
      "story_type": "new|development",
      "development_framing": "Optional: how to frame continuing coverage"
    }
  ],
  "total_items": 5,
  "estimated_duration_minutes": 8
}
```

Return ONLY the JSON object, no other text.
```

**Step 4: Update brief_planner_v2.py**

Replace `src/murmur/transformers/brief_planner_v2.py` with:

```python
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
```

**Step 5: Run test to verify it passes**

```bash
.venv/bin/pytest tests/murmur/transformers/test_planner_generic.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add src/murmur/transformers/brief_planner_v2.py prompts/plan_v2.md tests/murmur/transformers/test_planner_generic.py
git commit -m "feat(v2c): refactor planner to accept generic data sources"
```

---

## Task 6: Update Graph Configurations

**Files:**
- Modify: `config/graphs/full-v2a.yaml`
- Modify: `config/graphs/full-v2b.yaml`

**Step 1: Update full-v2a.yaml**

Replace `config/graphs/full-v2a.yaml`:

```yaml
name: full-v2a

nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics

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

**Step 2: Update full-v2b.yaml**

Replace `config/graphs/full-v2b.yaml`:

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
      data_sources:
        - $dedupe.news
        - $slack.slack
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

**Step 3: Commit**

```bash
git add config/graphs/full-v2a.yaml config/graphs/full-v2b.yaml
git commit -m "feat(v2c): update graphs to use data_sources list"
```

---

## Task 7: Update Script Generator for DataSource

**Files:**
- Modify: `src/murmur/transformers/script_generator.py`

The script generator receives `gathered_data` which is now a `DataSource`. Update it to extract the data.

**Step 1: Update script_generator.py**

In `src/murmur/transformers/script_generator.py`, update the process method to handle DataSource:

```python
def process(self, input: TransformerIO) -> TransformerIO:
    plan = input.data.get("plan", {})
    gathered_data = input.data.get("gathered_data", {})

    # Handle DataSource wrapper
    if hasattr(gathered_data, 'data'):
        gathered_data = gathered_data.data

    # ... rest of method unchanged
```

**Step 2: Commit**

```bash
git add src/murmur/transformers/script_generator.py
git commit -m "feat(v2c): update script generator to handle DataSource"
```

---

## Task 8: Remove Old Source-Specific Code

**Files:**
- Modify: `prompts/generate.md` (remove source-specific section)
- Delete: Old tests that reference removed inputs

**Step 1: Update prompts/generate.md**

Remove the "Data Sources" section that was added for Slack (lines 15-25). The source-specific guidance now lives in the source prompt fragments.

**Step 2: Update or remove old tests**

Remove tests that reference old planner inputs (`slack_data`, `gathered_data`):
- `tests/test_planner_with_slack.py` - remove or refactor

**Step 3: Commit**

```bash
git add prompts/generate.md
git rm tests/test_planner_with_slack.py
git commit -m "refactor(v2c): remove source-specific planner code"
```

---

## Task 9: Run Full Test Suite and Fix Breakages

**Step 1: Run all tests**

```bash
.venv/bin/pytest -v
```

**Step 2: Fix any failures**

Update tests that reference old output keys (`filtered_news` → `news`, `slack_data` → `slack`).

**Step 3: Commit fixes**

```bash
git add -A
git commit -m "fix(v2c): update tests for new DataSource outputs"
```

---

## Task 10: Document Plugin Development Pattern

**Files:**
- Create: `docs/plugin-development.md`

**Step 1: Create plugin development guide**

Create `docs/plugin-development.md`:

```markdown
# Developing Data Source Plugins for Murmur

Murmur uses a plugin-friendly architecture for data sources. Each source provides its own data and describes how it should be interpreted, without requiring changes to the core planner.

## Architecture Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│ News Fetcher│     │Slack Fetcher│     │Future Source│
└──────┬──────┘     └──────┬──────┘     └──────┬──────┘
       │                   │                   │
       ▼                   ▼                   ▼
   DataSource          DataSource          DataSource
       │                   │                   │
       └───────────────────┴───────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │Brief Planner │  (source-agnostic)
                    └──────────────┘
```

## What is a DataSource?

A `DataSource` is a standardized container that all fetchers output:

```python
from murmur.core import DataSource

source = DataSource(
    name="my-source",                           # Unique identifier
    data={"items": [...]},                      # Raw structured data
    prompt_fragment_path=Path("prompts/sources/my-source.md"),  # How to interpret
)
```

## Creating a New Data Source

### Step 1: Create the Fetcher Transformer

```python
# src/murmur/transformers/my_fetcher.py
from murmur.core import Transformer, TransformerIO, DataSource
from pathlib import Path

class MyFetcher(Transformer):
    name = "my-fetcher"
    inputs = ["config_path"]  # Whatever config your source needs
    outputs = ["my_source"]   # Output key for the DataSource
    input_effects = ["http"]  # Side effects (llm, http, mcp:*, etc.)
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        # Fetch your data
        data = self._fetch_data(input.data.get("config_path"))

        # Return as DataSource
        source = DataSource(
            name="my-source",
            data=data,
            prompt_fragment_path=Path("prompts/sources/my-source.md"),
        )
        return TransformerIO(data={"my_source": source})
```

### Step 2: Create the Prompt Fragment

Create `prompts/sources/my-source.md`:

```markdown
## My Source Data

Description of what this data represents.

{{data}}

When this data is present in the briefing:
- Guidance for the LLM on how to use it
- What to prioritize
- How to weave it into the narrative
- Any privacy or sensitivity considerations
```

The `{{data}}` placeholder will be replaced with JSON-formatted data.

### Step 3: Register the Transformer

Add to `src/murmur/transformers/__init__.py`:

```python
from murmur.transformers.my_fetcher import MyFetcher

def create_registry() -> TransformerRegistry:
    registry = TransformerRegistry()
    # ... existing registrations
    registry.register(MyFetcher())
    return registry
```

### Step 4: Wire into a Graph

Create or modify a graph in `config/graphs/`:

```yaml
name: my-graph

nodes:
  - name: my_source
    transformer: my-fetcher
    inputs:
      config_path: $config.my_source_config

  - name: plan
    transformer: brief-planner-v2
    inputs:
      data_sources:
        - $my_source.my_source
      story_context: []
```

## Best Practices

### Data Structure

Return structured data that the LLM can reason about:

```python
# Good: Structured with clear semantics
{
    "items": [
        {"title": "...", "priority": "high", "timestamp": "..."},
    ],
    "summary": "Brief overview",
}

# Bad: Opaque or pre-formatted
{
    "formatted_text": "Here is a summary...",
}
```

### Prompt Fragment Guidelines

1. **Describe, don't format**: Tell the LLM what the data means, not how to format it
2. **Provide context**: What source is this? Why is it relevant?
3. **Give guidance**: How should this be prioritized? What's important?
4. **Note sensitivities**: Privacy considerations, what to avoid

### Effects Declaration

Accurately declare side effects:
- `"llm"` - Makes LLM API calls
- `"http"` - Makes HTTP requests
- `"mcp:service"` - Uses MCP tools from a specific service
- `"filesystem"` - Reads/writes files

## Testing Your Plugin

```python
def test_my_fetcher_outputs_data_source():
    from murmur.transformers.my_fetcher import MyFetcher
    from murmur.core import TransformerIO, DataSource

    fetcher = MyFetcher()
    result = fetcher.process(TransformerIO(data={...}))

    assert "my_source" in result.data
    source = result.data["my_source"]
    assert isinstance(source, DataSource)
    assert source.name == "my-source"
    assert source.prompt_fragment_path.exists()
```

## Example: Adding GitHub as a Data Source

See the pattern used for Slack integration:
- `src/murmur/transformers/slack_fetcher.py`
- `prompts/sources/slack.md`
- `config/graphs/full-v2b.yaml`

A GitHub source would follow the same pattern:
1. Create `github_fetcher.py` using GitHub MCP tools
2. Create `prompts/sources/github.md` with guidance on commits, PRs, issues
3. Wire `$github.github` into the planner's `data_sources` list
```

**Step 2: Commit**

```bash
git add docs/plugin-development.md
git commit -m "docs(v2c): add plugin development guide"
```

---

## Task 11: Update Slack Setup Documentation

**Files:**
- Modify: `docs/slack-setup.md`

**Step 1: Update docs/slack-setup.md**

Add a note about the plugin architecture:

```markdown
## Architecture Note

Slack is implemented as a data source plugin. The Slack fetcher outputs a `DataSource` object that the planner consumes generically. This means:

- The planner doesn't have Slack-specific code
- Slack-specific guidance lives in `prompts/sources/slack.md`
- Adding new sources (GitHub, email, etc.) follows the same pattern

See `docs/plugin-development.md` for details on creating new data sources.
```

**Step 2: Commit**

```bash
git add docs/slack-setup.md
git commit -m "docs(v2c): add architecture note to Slack setup"
```

---

## Summary

After completing all tasks, you will have:

1. **DataSource protocol** in `core.py` - standardized output format
2. **Source prompt fragments** in `prompts/sources/` - per-source LLM guidance
3. **Updated fetchers** - output DataSource objects
4. **Generic planner** - assembles prompt from any wired sources
5. **Updated graphs** - use `data_sources` list
6. **Plugin documentation** - guide for adding new sources

**Adding a new data source now requires:**
1. Create fetcher transformer (outputs DataSource)
2. Create prompt fragment (`prompts/sources/X.md`)
3. Register transformer
4. Wire into graph

**No changes needed to:**
- Planner code
- Core prompt templates
- Other transformers
