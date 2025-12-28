# Murmur Handoff - Next Session

## Current State

**v1 is complete and working.** The full pipeline runs end-to-end:
- News gathering via Claude web search
- Narrative planning
- TTS-ready script generation
- Piper audio synthesis (Amy female voice)

**Branch:** `feature/v1-implementation` in worktree `.worktrees/v1-impl`

**Last test run:** Generated 6:26 audio briefing, copied to prototype sync directory.

## What Works

```bash
# Run with TTS
cd /home/frank/repos/murmur/.worktrees/v1-impl
devbox run -- python -m murmur.cli generate

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

- `src/murmur/` - Core package
- `config/graphs/full.yaml` - Main pipeline graph
- `config/profiles/default.yaml` - Default profile
- `prompts/` - Claude prompt templates
- `models/piper/en_US-amy-medium.onnx` - Voice model
- `bin/piper/` - Bundled Piper CLI

## Next Steps: v2

Design document at `docs/plans/2024-12-28-murmur-v2-design.md`

### v2a: Story Continuity (Priority)
**Goal:** No repeated stories unless there's meaningful progress.

Tasks:
1. Story data models (`ReportedStory`, `StoryHistory`)
2. History persistence (JSON, 7-day rolling window)
3. `story-deduplicator` transformer (Claude-based)
4. Updated planner for development annotations
5. `history-updater` transformer
6. Integration tests

### v2b: Slack Integration
**Goal:** Add Slack channel activity to briefings.

Prerequisite: Solve MCP credential passing to Claude subprocess.

### v2c: GitHub Integration
**Goal:** Add repository activity to briefings.

Reuses MCP pattern from v2b.

## To Start v2a

```bash
cd /home/frank/repos/murmur/.worktrees/v1-impl
# Read the design
cat docs/plans/2024-12-28-murmur-v2-design.md
# Then use superpowers:writing-plans to create implementation plan
```

## Notes

- Piper works via bundled CLI in `bin/piper/` (Python library had compatibility issues)
- Claude sometimes wraps JSON in markdown code blocks - `extract_json()` helper handles this
- Artifacts saved to `data/generation/` with timestamp prefix
- Audio syncs to phone via `~/Working/daily_brief/_claude/data/output/todays_brief.mp3`
