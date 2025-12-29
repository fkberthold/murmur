# Murmur v2 Design Document

> **For Claude:** This is a design document. Each phase (v2a, v2b, v2c) should use superpowers:writing-plans to create its implementation plan when ready.

**Goal:** Extend Murmur with story continuity tracking and additional data sources

**Key Insight:** "Change matters, repeats don't."

---

## Phased Approach

### v2a: Story Continuity (Core Feature)
**The main pain point.** No repeated stories unless there's meaningful progress.

### v2b: Slack Integration
**First MCP data source.** Solves MCP credential passing once, adds high-signal work context.

### v2c: GitHub Integration
**Second MCP data source.** Reuses MCP pattern from v2b, adds repository activity.

---

# v2a: Story Continuity

## Problem

The user doesn't want to hear the same story twice unless there's meaningful progress:

**Avoid:**
- Exact duplicates (same article)
- Stale updates ("Micron beat earnings" repeated)
- Rehashed summaries (different article, same facts)

**Allow (and encourage):**
- Story progression (hurricane approaching → landfall → damage → recovery)
- Genuine developments (new facts)
- Related but distinct stories (different company's earnings)

## Data Model

```python
@dataclass
class ReportedStory:
    """A story that was previously reported."""
    id: str                          # UUID
    url: str | None                  # Source URL
    title: str                       # Headline
    summary: str                     # What we told the user
    topic: str                       # Category (AI, Tech, etc.)
    story_key: str                   # Semantic key for grouping
    reported_at: datetime            # When first reported
    last_mentioned_at: datetime      # Most recent mention
    mention_count: int               # Times mentioned
    developments: list[str]          # Chronological updates

@dataclass
class StoryHistory:
    """Rolling history of reported stories."""
    stories: dict[str, ReportedStory]  # story_key -> story
    max_age_days: int = 7              # Forget after 7 days
```

## Story Key Examples

Claude generates semantic keys for grouping:
- `hurricane-milton-2024` - All Hurricane Milton coverage
- `micron-q4-2024-earnings` - Micron's Q4 earnings
- `trump-national-guard-chicago` - National Guard saga

## Deduplication Flow

```
Gather News
    ↓
Load History (7-day window)
    ↓
For each item:
├── Generate story_key (Claude)
├── Check against history
│   ├── No match → include_as_new
│   └── Match found
│       ├── No new info → skip
│       └── Has development → include_as_development
    ↓
Plan & Generate (with development context)
    ↓
Update History (record what was reported)
```

## Deduplication Prompt

```markdown
## Story Continuity Check

Previously Reported (last 7 days):
{{history}}

New Candidates:
{{candidates}}

For each candidate:
1. Assign a story_key (semantic identifier)
2. Check for match in history
3. If matched: Is there meaningful NEW information?
4. If not matched: It's new

Output:
{
  "items": [
    {
      "candidate_index": 0,
      "story_key": "hurricane-milton-florida-2024",
      "action": "include_as_development",
      "existing_story_id": "abc123",
      "development_note": "Recovery efforts, 3 days after landfall"
    },
    {
      "candidate_index": 1,
      "story_key": "micron-q4-2024-earnings",
      "action": "skip",
      "skip_reason": "No new information"
    }
  ]
}
```

## v2a Graph

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
      news: $dedupe.filtered_news
      story_context: $dedupe.story_context

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
      reported_items: $dedupe.items_to_report
      history_path: $config.history_path

  - name: synthesize
    transformer: piper-synthesizer
    inputs:
      script: $generate.script
      piper_model: $config.piper_model
      output_dir: $config.output_dir
```

## v2a Implementation Tasks

1. **Story data models** - `ReportedStory`, `StoryHistory` in `src/murmur/history.py`
2. **History persistence** - JSON file per profile, 7-day rolling window
3. **Deduplicator transformer** - Claude-based key generation + change detection
4. **Updated planner** - Handle `story_context` for development annotations
5. **History updater transformer** - Record reported items after generation
6. **Integration tests** - Deduplication edge cases, story progression

---

# v2b: Slack Integration

## Prerequisite: MCP Credential Passing

Before adding MCP data sources, we need to solve how to pass credentials to Claude subprocess. Options:
- Environment variables (prototype approach)
- MCP config file path
- Inline in prompt (not recommended for secrets)

**Decision needed at implementation time.**

## Slack Transformer

**Configuration** (`config/slack.yaml`):
```yaml
channels:
  - name: engineering
    id: C23456789
    priority: high

colleagues:
  - name: Alice
    slack_id: U12345678

projects:
  - name: Project Alpha
    keywords: [alpha, project-alpha]

settings:
  lookback_hours: 24
  include_threads: true
```

**Transformer**: `slack-fetcher`
- **Inputs**: `slack_config`
- **Outputs**: `slack_data`
- **Effects**: `mcp:slack`

## v2b Graph Additions

```yaml
  - name: slack
    transformer: slack-fetcher
    inputs:
      slack_config: $config.slack

  - name: plan
    transformer: brief-planner-v2
    inputs:
      news: $dedupe.filtered_news
      story_context: $dedupe.story_context
      slack: $slack.slack_data  # NEW
```

## v2b Implementation Tasks

1. **MCP credential mechanism** - Solve once, reuse for all MCP sources
2. **Slack config schema** - Channels, colleagues, projects
3. **Slack fetcher transformer** - Uses `mcp:slack` tools
4. **Updated planner prompt** - Integrate Slack highlights
5. **Updated script generator** - Handle multi-source data

---

# v2c: GitHub Integration

## GitHub Transformer

**Configuration** (`config/github.yaml`):
```yaml
repos:
  - owner: anthropics
    repo: claude-code
    branches: [main]
    priority: high

settings:
  lookback_hours: 24
  include_merge_commits: false
  notable_file_patterns:
    - "pyproject.toml"
    - "package.json"
```

**Transformer**: `github-fetcher`
- **Inputs**: `github_config`
- **Outputs**: `github_data`
- **Effects**: `mcp:github`

## v2c Graph Additions

```yaml
  - name: github
    transformer: github-fetcher
    inputs:
      github_config: $config.github

  - name: plan
    transformer: brief-planner-v2
    inputs:
      news: $dedupe.filtered_news
      story_context: $dedupe.story_context
      slack: $slack.slack_data
      github: $github.github_data  # NEW
```

## v2c Implementation Tasks

1. **GitHub config schema** - Repos, branches, patterns
2. **GitHub fetcher transformer** - Uses `mcp:github` tools
3. **Updated planner prompt** - Integrate commits/PRs
4. **Final integration tests**

---

## Open Questions

1. **MCP Credentials**: Environment variables? Config file? (Solve in v2b)

2. **Story Key Stability**: How to ensure consistent keys across runs?
   - Examples in prompt
   - Embedding similarity fallback

3. **History Location**: Per-profile or global?
   - Recommend: per-profile (`data/{profile}/history/`)

---

## Success Criteria

**v2a:**
- No repeated stories without new information
- Developments explicitly noted ("Continuing our coverage...")
- History persists and rolls off after 7 days

**v2b:**
- Slack messages integrated into briefings
- MCP credential pattern established

**v2c:**
- GitHub activity integrated into briefings
- All v1 tests still pass
