# Murmur Handoff - Post Calendar Plugin

## Current State

**v1, v2a (Story Continuity), v2b (Slack), v2c (Plugin Architecture), and Calendar Plugin are complete.**

All commits pushed to `origin/main`.

**Tests:** 83 passing (`devbox run test`)

## What Was Done This Session

1. **Designed Calendar Plugin** following Slack pattern (brainstorming skill)
2. **Created implementation plan** with 9 TDD tasks
3. **Implemented all 9 tasks** using subagent-driven development:
   - Task 1: Config schema (`src/murmur/config/calendar.py`)
   - Task 2: User config (`config/calendar.yaml`)
   - Task 3: Gather prompt (`prompts/calendar_gather.md`)
   - Task 4: Planner fragment (`prompts/sources/calendar.md`)
   - Task 5: CalendarFetcher transformer
   - Task 6: Registry registration
   - Task 7: v2c graph with calendar node
   - Task 8: Integration tests
   - Task 9: This handoff update

## Calendar Plugin Architecture

| Component | Path |
|-----------|------|
| Config schema | `src/murmur/config/calendar.py` |
| Transformer | `src/murmur/transformers/calendar_fetcher.py` |
| Gather prompt | `prompts/calendar_gather.md` |
| Planner fragment | `prompts/sources/calendar.md` |
| User config | `config/calendar.yaml` |
| Graph | `config/graphs/full-v2c.yaml` |

## MCP Authentication

**Google Calendar MCP needs re-authentication** (tokens expire every 7 days in testing mode).

To re-authenticate:
```bash
GOOGLE_OAUTH_CREDENTIALS=~/.config/google-calendar-mcp/gcp-oauth.keys.json npx @cocal/google-calendar-mcp auth
```

Then restart Claude Code to pick up new tokens.

## Testing the Calendar Plugin

```bash
# Run with calendar (v2c graph)
devbox run -- python -m murmur.cli generate --graph full-v2c

# Or update work profile to use v2c by default
# (change graph: full-v2b to graph: full-v2c in config/profiles/work.yaml)
```

## Next Steps

Potential improvements:
1. **End-to-end test** - Run full pipeline with calendar once MCP auth is refreshed
2. **Timezone handling** - Currently uses local time; could use timezone-aware datetimes
3. **Error handling** - Add try/catch around JSON parsing for better error messages
4. **Shared utilities** - Extract `extract_json()` to common module (used by both Slack and Calendar fetchers)

## Commands

```bash
devbox run test                                    # Run tests (83 passing)
devbox run -- python -m murmur.cli generate       # Generate with default profile
devbox run -- python -m murmur.cli list graphs    # List available graphs
devbox run -- python -m murmur.cli list transformers  # List transformers
```

## Key Files

- `docs/plans/2024-12-30-calendar-plugin-design.md` - Design document
- `docs/plans/2024-12-30-calendar-plugin-implementation.md` - Implementation plan
- `src/murmur/transformers/calendar_fetcher.py` - Main transformer
- `config/graphs/full-v2c.yaml` - Graph with all data sources
