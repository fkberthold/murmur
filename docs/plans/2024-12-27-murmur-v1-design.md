# Murmur v1 Design

**Date:** 2024-12-27
**Status:** Approved

## Overview

Murmur is a personal intelligence briefing system that gathers news, plans a narrative, generates a TTS-ready script, and synthesizes audio via Piper.

## Pipeline Stages

```
Gather (news) → Plan (curate) → Generate (TTS-ready text) → Synthesize (Piper)
```

### Stage 1: Gather

Claude subprocess with web search. Given topics from `config/news_topics.yaml`, fetches current news. Output is structured JSON - high-density data meant for filtering, not listening.

- **Transformer:** `news-fetcher`
- **Input effects:** `llm`
- **Output:** `gathered_data`
- **Artifact:** `data/generation/YYYYMMDD_HHMMSS_gathered.json`

### Stage 2: Plan

Claude subprocess (no tools). Takes gathered data plus user context. Selects relevant stories, determines narrative order, identifies connections between items.

- **Transformer:** `brief-planner`
- **Input effects:** `llm`
- **Output:** `plan`
- **Artifact:** `data/generation/YYYYMMDD_HHMMSS_plan.md`

### Stage 3: Generate

Claude subprocess (no tools). Takes the plan and produces TTS-ready plain English. Optimized for listening - natural speech patterns, good punctuation for prosody, warm professional tone.

- **Transformer:** `script-generator`
- **Input effects:** `llm`
- **Output:** `script`
- **Artifact:** `data/generation/YYYYMMDD_HHMMSS_script.txt`

### Stage 4: Synthesize

Python calls Piper directly (no Claude). Converts script to audio using `--sentence_silence` for pacing.

- **Transformer:** `piper-synthesizer`
- **Input effects:** none
- **Output effects:** `tts`, `filesystem`
- **Output:** `audio`
- **Artifact:** `output/brief_YYYYMMDD_HHMMSS.mp3` + `output/latest.mp3` symlink

## Architecture

### Transformer Model

Each stage is a Transformer - a Python class with declared effects:

```python
class Transformer(ABC):
    name: str
    inputs: list[str]          # Required input keys
    outputs: list[str]         # Produced output keys
    input_effects: list[str]   # e.g., ["llm", "http"]
    output_effects: list[str]  # e.g., ["filesystem", "tts"]

    @abstractmethod
    def process(self, input: TransformerIO) -> TransformerIO:
        pass
```

**TransformerIO** is the universal data container:

```python
@dataclass
class TransformerIO:
    data: dict                    # Structured data
    artifacts: dict[str, Path]    # Produced files
```

### Graph Definition

Graphs are YAML files with explicit input/output wiring:

```yaml
# config/graphs/full.yaml
name: full-brief

nodes:
  - name: gather
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics

  - name: plan
    transformer: brief-planner
    inputs:
      news: $gather.gathered_data

  - name: generate
    transformer: script-generator
    inputs:
      plan: $plan.plan

  - name: synthesize
    transformer: piper-synthesizer
    inputs:
      script: $generate.script
```

**Key features:**
- Execution order derived from wiring (not declared)
- Validation at load time against transformer class declarations
- Config injection via `$config.key`
- Node output references via `$node.output_key`

### Profile

Profiles bundle graph selection with configuration values:

```yaml
# config/profiles/default.yaml
name: default
graph: full

config:
  news_topics: $file:news_topics.yaml
  piper_model: en_US-libritts_r-medium
  sentence_silence: 0.3
  narrator_style: warm-professional
```

Profile is just a config bag. The graph decides which values go where. No special cases.

## Project Structure

```
murmur/
├── src/murmur/
│   ├── __init__.py
│   ├── cli.py                 # Typer CLI
│   ├── core.py                # Transformer, TransformerIO
│   ├── executor.py            # GraphExecutor
│   ├── claude.py              # Claude subprocess wrapper
│   ├── transformers/
│   │   ├── __init__.py
│   │   ├── news_fetcher.py
│   │   ├── brief_planner.py
│   │   ├── script_generator.py
│   │   └── piper_synthesizer.py
│   └── lib/
│       └── piper.py           # Piper TTS wrapper
├── config/
│   ├── news_topics.yaml
│   ├── graphs/
│   │   ├── full.yaml
│   │   └── script_only.yaml
│   └── profiles/
│       └── default.yaml
├── prompts/
│   ├── gather.md
│   ├── plan.md
│   └── generate.md
├── data/
│   └── generation/            # Intermediate artifacts
├── output/                    # Final MP3 files
├── models/
│   └── piper/                 # Voice model files
└── pyproject.toml
```

## Configuration

### News Topics

```yaml
# config/news_topics.yaml
topics:
  - name: ai-developments
    query: "artificial intelligence breakthroughs"
    priority: high

  - name: tech-industry
    query: "technology industry news"
    priority: medium

  - name: science
    query: "scientific discoveries"
    priority: low
```

## CLI Interface

```bash
murmur generate                          # Default profile, full run
murmur generate --profile executive      # Specific profile
murmur generate --graph script_only      # Override graph
murmur generate --cached gather,plan     # Use cached outputs
murmur generate --cached gather --run 20241226_143022
murmur generate --dry-run                # Validate only

murmur list profiles
murmur list graphs
murmur list transformers
```

## Error Handling

**Graph validation errors** (caught before execution):
- Unknown transformer referenced
- Missing required input wiring
- Reference to non-existent output
- Circular dependencies
- Missing config values

**Runtime errors:**
- Claude subprocess failure (timeout, non-zero exit)
- Piper synthesis failure
- Missing cached artifacts when `--cached` specified

**Approach:**
- Fail fast with clear error messages
- Save partial artifacts on failure
- No automatic retries for v1

## Key Decisions

| Aspect | Decision |
|--------|----------|
| Orchestration | Python graph executor with YAML-defined graphs |
| Graph wiring | Input/output references, validated at load time |
| Claude usage | Subprocess via `claude --print` |
| Data source | News only (web search) |
| TTS | Piper (local, plain text, `--sentence_silence`) |
| Output | TTS-ready plain English, warm professional tone |
| Profile | Graph selection + config bag (no special cases) |
| Artifacts | Full intermediates saved per run |
| Caching | `--cached node,node --run <id>` |
| Errors | Fail fast, save partial artifacts, no auto-retry |

## Not in v1

- Petri net simulation
- RAG system
- Multiple data sources (Slack, GitHub, Calendar, Journal)
- Custom markup language
- Graph visualization
- Automatic retries

## Future Enhancements

- `murmur graph show <name>` - Generate PlantUML/DOT visualization
- Additional data sources as transformers
- Retry logic for flaky stages
- Parallel execution for independent nodes
