# Handoff: v2c Plugin Architecture Refactor

## Current Status

**v2b Slack Integration**: Complete (all 9 tasks done, 67 tests passing, 63 commits ahead of origin)

**v2c Plugin Architecture**: Plan written, ready for execution

## Next Session Task

Execute the v2c plan using subagent-driven development:

```
/subagent-driven-development docs/plans/2024-12-29-v2c-plugin-architecture.md
```

## What v2c Does

Refactors the planner to be source-agnostic so adding new data sources doesn't require planner changes:

**The Problem:** Currently, adding Slack required:
- Adding `slack_data` input to planner
- Adding `_format_slack_data()` method to planner
- Adding `{{slack_highlights}}` to `prompts/plan_v2.md`

Every new source (GitHub, email, calendar) would need similar changes.

**The Solution:**
1. Each fetcher outputs a `DataSource` object (name + data + prompt_fragment_path)
2. Planner accepts a generic `data_sources` list instead of source-specific inputs
3. Prompt is assembled dynamically from source fragments in `prompts/sources/`
4. Source-specific guidance lives with the source, not in the planner

**Adding a new source becomes:**
1. Create fetcher transformer (outputs DataSource)
2. Create prompt fragment (`prompts/sources/X.md`)
3. Register transformer
4. Wire into graph

**No changes needed to:**
- Planner code
- Core prompt templates
- Other transformers

## Plan Summary (11 Tasks)

| Task | Description |
|------|-------------|
| 1 | Add `DataSource` dataclass to `core.py` |
| 2 | Create source prompt fragments (`prompts/sources/news.md`, `slack.md`) |
| 3 | Update Slack fetcher to output `DataSource` |
| 4 | Update deduplicator to wrap news in `DataSource` |
| 5 | Refactor planner to accept generic `data_sources` list |
| 6 | Update graph configurations |
| 7 | Update script generator to handle `DataSource` |
| 8 | Remove old source-specific code |
| 9 | Fix test breakages |
| 10 | Create plugin development documentation |
| 11 | Update Slack setup docs |

## Key Files

- **Plan**: `docs/plans/2024-12-29-v2c-plugin-architecture.md`
- **Core change**: Add `DataSource` to `src/murmur/core.py`
- **Planner refactor**: `src/murmur/transformers/brief_planner_v2.py`
- **New prompt dir**: `prompts/sources/`
- **New docs**: `docs/plugin-development.md`

## Current State

```
Branch: main
Tests: 67 passing
Commits ahead of origin: 64 (including v2c plan commit)
```

All v2b commits + v2c plan are on main.
