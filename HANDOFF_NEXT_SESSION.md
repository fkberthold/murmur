# Murmur Handoff - Next Session

## Current State

**v1 is complete.** **v2a (Story Continuity) is complete.**

The full pipeline now includes:
- News gathering via Claude web search
- **Story deduplication against 7-day rolling history**
- **Development detection for ongoing stories**
- Narrative planning (with story context awareness)
- TTS-ready script generation
- Piper audio synthesis (Amy female voice)

**Branch:** `feature/v1-implementation` in worktree `.worktrees/v1-impl`

**Tests:** 51 passing (including 3 v2a integration tests)

## What Works

```bash
# Run with TTS (uses full-v2a graph via default profile)
cd /home/frank/repos/murmur/.worktrees/v1-impl
devbox run -- python -m murmur.cli generate

# Run v2a graph explicitly
devbox run -- python -m murmur.cli generate --graph full-v2a

# Run v1 graph (no story continuity)
devbox run -- python -m murmur.cli generate --graph full

# Run without TTS (faster for testing)
devbox run -- python -m murmur.cli generate --graph no-tts

# Use cached stages
devbox run -- python -m murmur.cli generate --cached gather,plan,generate --run <run_id>

# Dry run (validate only)
devbox run -- python -m murmur.cli generate --dry-run

# List available components
devbox run -- python -m murmur.cli list transformers
devbox run -- python -m murmur.cli list graphs
```

## Key Files

**Core:**
- `src/murmur/` - Core package
- `config/graphs/full-v2a.yaml` - v2a pipeline with story continuity
- `config/graphs/full.yaml` - v1 pipeline (no deduplication)
- `config/profiles/default.yaml` - Default profile (uses full-v2a)
- `prompts/` - Claude prompt templates

**v2a Story Continuity:**
- `src/murmur/history.py` - ReportedStory and StoryHistory dataclasses
- `src/murmur/transformers/story_deduplicator.py` - Claude-based duplicate detection
- `src/murmur/transformers/history_updater.py` - Persists reported stories
- `src/murmur/transformers/brief_planner_v2.py` - Context-aware planning
- `prompts/dedupe.md` - Deduplication prompt
- `prompts/plan_v2.md` - Planning prompt with story context
- `data/history/default.json` - Story history (created on first run)

**Voice:**
- `models/piper/en_US-amy-medium.onnx` - Voice model
- `bin/piper/` - Bundled Piper CLI

## v2a Architecture

```
gather → dedupe → plan → generate → history → synthesize
              ↓                         ↑
         [history.json] ←───────────────┘
```

- **StoryDeduplicator**: Loads history, asks Claude to classify each news item
  - `skip`: Same story, no new info
  - `include_as_development`: Update to existing story
  - `include_as_new`: Fresh story
- **BriefPlannerV2**: Receives story context, enables "Continuing our coverage..." framing
- **HistoryUpdater**: Records what was reported, updates developments

## Next Steps: v2b and v2c

Design document at `docs/plans/2024-12-28-murmur-v2-design.md`

### v2b: Slack Integration
**Goal:** Add Slack channel activity to briefings.

Prerequisite: Solve MCP credential passing to Claude subprocess.

### v2c: GitHub Integration
**Goal:** Add repository activity to briefings.

Reuses MCP pattern from v2b.

## Notes

- Piper works via bundled CLI in `bin/piper/` (Python library had compatibility issues)
- Claude sometimes wraps JSON in markdown code blocks - `extract_json()` helper handles this
- Artifacts saved to `data/generation/` with timestamp prefix
- Story history persists to `data/history/default.json` (auto-expires after 7 days)
- Audio syncs to phone via `~/Working/daily_brief/_claude/data/output/todays_brief.mp3`
