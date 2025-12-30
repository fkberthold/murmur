# Murmur Handoff - Calendar Plugin

## Current State

**v1, v2a (Story Continuity), v2b (Slack), and v2c (Plugin Architecture) are complete.**

All 79 commits pushed to `origin/main`.

**Tests:** 73 passing (`devbox run test`)

## What Was Done This Session

1. **Executed v2c plugin architecture plan** (11 tasks) - Made planner source-agnostic with DataSource protocol
2. **Fixed Slack integration issues**:
   - Graph validation for list inputs (`data_sources: [$a, $b]`)
   - DataSource JSON serialization (`to_dict()`/`from_dict()`)
   - devbox.json script format fix
   - Slack MCP prompt - added explicit `limit` parameter instruction
3. **Updated Slack config** from prototype with real channel IDs
4. **Full pipeline test** - Generated script now includes Slack data (21 messages found)

## Next Task: Calendar Plugin

Add Google Calendar as a data source using the same plugin pattern as Slack.

### Architecture (Follow Slack Pattern)

| Component | Path | Reference |
|-----------|------|-----------|
| Config schema | `src/murmur/config/calendar.py` | `slack.py` |
| Transformer | `src/murmur/transformers/calendar_fetcher.py` | `slack_fetcher.py` |
| Gather prompt | `prompts/calendar_gather.md` | `slack_gather.md` |
| Planner fragment | `prompts/sources/calendar.md` | `sources/slack.md` |
| User config | `config/calendar.yaml` | `slack.yaml` |
| Tests | `tests/test_calendar_fetcher.py` | `test_slack_fetcher.py` |

### MCP Tools Available

```
mcp__google-calendar__list-calendars
mcp__google-calendar__list-events
mcp__google-calendar__get-event
mcp__google-calendar__get-current-time
```

**Note:** MCP auth may need refresh - got "token expired" error when testing.

### Prototype Reference

Full implementation at `~/Working/daily_brief/_claude/src/data_sources/calendar.py`:
- Multiple calendars (personal, work, family)
- Event rules (always_skip, always_mention, canceled_only)
- Notable event detection for tomorrow
- Timezone conversion
- Today's remaining + tomorrow's notable events

Config example: `~/Working/daily_brief/_claude/config/calendar_config.yaml`

### Graph Integration

Add to `config/graphs/no-tts-v2b.yaml`:
```yaml
- name: calendar
  transformer: calendar-fetcher
  inputs:
    calendar_config_path: $config.calendar_config_path
    mcp_config_path: $config.mcp_config_path
```

Add `$calendar.calendar` to planner's `data_sources` list.

## Commands

```bash
devbox run test                                    # Run tests
devbox run -- python scripts/run_full_pipeline.py # Full generation
```

## Key Files

- `src/murmur/transformers/slack_fetcher.py` - Pattern to follow
- `src/murmur/config/slack.py` - Config pattern
- `prompts/slack_gather.md` - Prompt pattern
- `docs/plans/2024-12-29-v2c-plugin-architecture.md` - Plugin design

## Open Questions

1. Start with simple config or full event rules from prototype?
2. Timezone handling needed? (prototype converts to display_timezone)
