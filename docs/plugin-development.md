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
    registry.register(MyFetcher)
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
