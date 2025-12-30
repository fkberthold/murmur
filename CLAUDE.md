# CLAUDE.md

This file provides guidance to Claude Code when working with the Murmur codebase.

## Project Overview

Murmur is a personal intelligence briefing system that generates spoken audio briefings from multiple data sources (news, Slack, etc.). It uses a transformer-based graph architecture where each processing stage is a pluggable "transformer" with defined inputs/outputs.

## Development Environment

**This project uses devbox for environment management. Always use devbox commands.**

### Running Commands

```bash
# Always prefix Python commands with devbox run
devbox run -- python -m murmur.cli generate
devbox run -- python -m murmur.cli list transformers

# Or use defined scripts
devbox run test          # Run all tests
devbox run test-cov      # Run tests with coverage
devbox run install-tts   # Install TTS dependencies
```

### Running Tests

```bash
# Preferred: use devbox script
devbox run test

# Specific test file
devbox run -- pytest tests/murmur/test_core.py -v

# Integration tests only
devbox run -- pytest tests/integration/ -v
```

**Important:** Do NOT use `.venv/bin/pytest` directly. The devbox shell hook ensures proper environment setup including Nix packages (Python 3.11, ffmpeg).

### Virtual Environment

The `.venv` is auto-created by devbox shell hook. Do not manually create or activate it - devbox handles this.

## Architecture

### Core Concepts

- **Transformer**: Processing stage with defined `inputs`, `outputs`, and `effects`
- **TransformerIO**: Universal I/O container (`data` dict + `artifacts` dict)
- **DataSource**: Plugin-friendly output format (`name` + `data` + `prompt_fragment_path`)
- **Graph**: YAML-defined pipeline of transformers with input/output wiring
- **Profile**: Configuration that selects a graph and provides config values

### Key Directories

```
src/murmur/
├── cli.py              # Entry point
├── core.py             # TransformerIO, DataSource, Transformer base
├── executor.py         # Graph execution engine
├── graph.py            # Graph loading/validation
├── transformers/       # All transformer implementations
└── claude.py           # Claude API integration

config/
├── graphs/             # Graph definitions (YAML)
│   ├── full-v2a.yaml   # News + deduplication
│   └── full-v2b.yaml   # News + Slack + deduplication
├── profiles/           # Profile configurations
└── slack.yaml          # Slack channel config

prompts/
├── plan_v2.md          # Planner prompt template
├── generate.md         # Script generator prompt
└── sources/            # Per-source prompt fragments
    ├── news.md
    └── slack.md

tests/
├── murmur/             # Unit tests (mirrors src structure)
├── integration/        # Multi-transformer tests
└── fixtures/           # Test data
```

### Creating New Transformers

1. Create `src/murmur/transformers/my_transformer.py`:
```python
from murmur.core import Transformer, TransformerIO, DataSource

class MyTransformer(Transformer):
    name = "my-transformer"
    inputs = ["input_data"]
    outputs = ["output_data"]
    input_effects = ["llm"]  # Side effects: llm, http, mcp:*, filesystem, tts
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        data = input.data.get("input_data", {})
        # Process data...
        return TransformerIO(data={"output_data": result})
```

2. Register in `src/murmur/transformers/__init__.py`:
```python
from murmur.transformers.my_transformer import MyTransformer

def create_registry() -> TransformerRegistry:
    registry = TransformerRegistry()
    # ... existing registrations
    registry.register(MyTransformer())
    return registry
```

3. Wire into a graph in `config/graphs/`.

### DataSource Protocol (v2c Plugin Architecture)

Data sources output `DataSource` objects for generic consumption:

```python
from murmur.core import DataSource
from pathlib import Path

source = DataSource(
    name="my-source",
    data={"items": [...]},
    prompt_fragment_path=Path("prompts/sources/my-source.md"),
)
```

The planner dynamically assembles prompts from all sources' fragments.

## MCP Integration

Slack integration uses an MCP server. Configuration in `.mcp.json`.

**Required:** Set `SLACK_USER_TOKEN` in `.env` file:
```
SLACK_USER_TOKEN=xoxp-your-token-here
```

## Semantic Code Search

The codebase is indexed for semantic search. Use `mcp__claude-context__search_code` to find relevant code:

```
Query: "how does the planner handle multiple data sources"
Path: /home/frank/repos/murmur
```

To reindex after major changes:
```
mcp__claude-context__index_codebase with path=/home/frank/repos/murmur
```

## Common Tasks

### Generate a Briefing
```bash
devbox run -- python -m murmur.cli generate
devbox run -- python -m murmur.cli generate --graph full-v2b  # With Slack
devbox run -- python -m murmur.cli generate --dry-run         # Validate only
```

### Run Tests
```bash
devbox run test                                    # All tests
devbox run -- pytest tests/murmur/test_core.py -v # Specific file
devbox run -- pytest -k "test_planner" -v         # Pattern match
```

### List Resources
```bash
devbox run -- python -m murmur.cli list transformers
devbox run -- python -m murmur.cli list graphs
devbox run -- python -m murmur.cli list profiles
```

## Current Status

See `docs/HANDOFF_NEXT_SESSION.md` for the latest development status and next steps.
