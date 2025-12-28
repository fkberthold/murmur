# Murmur v2 Design Document

> **For Claude:** This is a design document for the next iteration. Use superpowers:writing-plans to create the implementation plan when ready.

**Goal:** Extend Murmur with story continuity tracking and additional data sources (GitHub, Slack)

**Architecture:** Build on v1's transformer graph model, adding a history store and new data source transformers

**Tech Stack:** Python, YAML graphs, Claude (web search + MCP tools), Piper TTS

---

## Core Problem: Avoiding Repetition

The user doesn't want to hear the same story twice unless there's meaningful progress. This is nuanced:

### What to Avoid
- **Exact duplicates**: Same article reported again
- **Stale updates**: "Micron beat earnings" repeated without new info
- **Rehashed summaries**: Different article, same facts

### What to Allow (and Encourage)
- **Story progression**: Hurricane approaching → hits Florida → damage assessment → recovery updates
- **Developments**: Follow-up on a story with genuinely new information
- **Related but distinct**: New angle on a topic (e.g., different company's earnings, not the same one)

### The Key Insight
**Change matters, repeats don't.** The system should track ongoing stories and explicitly note when there's meaningful progression worth mentioning.

---

## Design: Story History Store

### Data Model

```python
@dataclass
class ReportedStory:
    """A story that was previously reported."""
    id: str                          # UUID
    url: str | None                  # Source URL (if available)
    title: str                       # Headline/title
    summary: str                     # What we told the user
    topic: str                       # Category (AI, Tech, etc.)
    story_key: str                   # Semantic key for grouping related stories
    reported_at: datetime            # When first reported
    last_mentioned_at: datetime      # Most recent mention
    mention_count: int               # How many times mentioned
    developments: list[str]          # Chronological list of updates

@dataclass
class StoryHistory:
    """Rolling history of reported stories."""
    stories: dict[str, ReportedStory]  # story_key -> story
    max_age_days: int = 7              # Forget stories older than this

    def find_similar(self, candidate: NewsItem) -> ReportedStory | None:
        """Find a previously reported story similar to this candidate."""
        ...

    def is_new_development(self, candidate: NewsItem, existing: ReportedStory) -> bool:
        """Determine if candidate represents meaningful progress on existing story."""
        ...

    def record(self, item: NewsItem, as_development_of: str | None = None):
        """Record that we reported this item."""
        ...
```

### Story Key Generation

The `story_key` groups related articles. Examples:
- `hurricane-milton-2024` - All articles about Hurricane Milton
- `micron-q4-2024-earnings` - Micron's Q4 earnings coverage
- `trump-national-guard-chicago` - Trump/Chicago National Guard saga

Claude generates the story_key during news gathering, considering:
- Named entities (companies, people, events)
- Temporal markers (quarters, dates, seasons)
- Core topic (what the story is fundamentally about)

### Deduplication Flow

```
┌─────────────────┐
│  Gather News    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ Load History    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ For each item:  │
│ - Generate key  │◄──── Claude assigns story_key
│ - Check history │
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌─────────────┐
│ New   │ │ Existing    │
│ Story │ │ Story Found │
└───┬───┘ └──────┬──────┘
    │            │
    │     ┌──────┴──────┐
    │     ▼             ▼
    │ ┌───────────┐ ┌────────────┐
    │ │ No Change │ │ Has Update │
    │ │ → Skip    │ │ → Include  │
    │ └───────────┘ │ as develop-│
    │               │ ment       │
    │               └─────┬──────┘
    │                     │
    ▼                     ▼
┌─────────────────────────────┐
│  Plan & Generate with      │
│  context about progression │
└─────────────────────────────┘
```

### Claude's Role in Deduplication

Claude handles the nuanced decisions:

1. **Key Assignment**: Given an article, what's its `story_key`?
2. **Change Detection**: Given a new article and existing story, is there meaningful new information?
3. **Context Injection**: When including a development, explain how it progresses the story

The prompt for the deduplication transformer:

```markdown
## Story Continuity Check

You're reviewing gathered news against previously reported stories.

### Previously Reported (last 7 days):
{{history}}

### New Candidates:
{{candidates}}

For each candidate:
1. Assign a story_key (semantic identifier for grouping)
2. Check if it matches a previously reported story
3. If matched: Is there meaningful NEW information?
   - Progress on an ongoing situation (hurricane damage → recovery)
   - New facts not previously covered
   - Significant development worth mentioning
4. If not matched: It's a new story

### Output Format:
{
  "items": [
    {
      "candidate_index": 0,
      "story_key": "hurricane-milton-florida-2024",
      "action": "include_as_development",
      "existing_story_id": "abc123",
      "development_note": "Now covering recovery efforts, 3 days after landfall",
      "include_reason": "Significant progression from initial landfall coverage"
    },
    {
      "candidate_index": 1,
      "story_key": "micron-q4-2024-earnings",
      "action": "skip",
      "existing_story_id": "def456",
      "skip_reason": "No new information beyond previously reported earnings beat"
    },
    {
      "candidate_index": 2,
      "story_key": "anthropic-claude-4-launch",
      "action": "include_as_new",
      "include_reason": "First coverage of this topic"
    }
  ]
}
```

---

## New Data Sources

### GitHub Transformer

Uses the GitHub MCP server to gather repository activity.

**Configuration** (`config/github_repos.yaml`):
```yaml
repos:
  - owner: anthropics
    repo: claude-code
    branches: [main]
    priority: high

  - owner: my-org
    repo: my-project
    branches: [main, develop]
    priority: high

settings:
  lookback_hours: 24
  include_merge_commits: false
  min_changes_threshold: 10
  notable_file_patterns:
    - "*.md"
    - "pyproject.toml"
    - "package.json"
```

**Transformer**: `github-fetcher`
- **Inputs**: `repos_config` (from config)
- **Outputs**: `github_data`
- **Effects**: `mcp:github`

**Output Schema**:
```json
{
  "commits": [
    {
      "repo": "owner/repo",
      "sha": "abc123",
      "author": "username",
      "message": "feat: add new feature",
      "timestamp": "2024-12-28T10:00:00Z",
      "files_changed": 5,
      "notable_files": ["pyproject.toml"]
    }
  ],
  "pull_requests": [
    {
      "repo": "owner/repo",
      "number": 123,
      "title": "Add new feature",
      "author": "username",
      "state": "merged",
      "merged_at": "2024-12-28T10:00:00Z"
    }
  ]
}
```

### Slack Transformer

Uses the Slack MCP server to gather channel activity.

**Configuration** (`config/slack_channels.yaml`):
```yaml
channels:
  - name: general
    id: C12345678
    priority: medium

  - name: engineering
    id: C23456789
    priority: high

colleagues:
  - name: Alice
    slack_id: U12345678

  - name: Bob
    slack_id: U23456789

projects:
  - name: Project Alpha
    keywords: [alpha, project-alpha]

settings:
  lookback_hours: 24
  include_threads: true
  min_message_length: 20
```

**Transformer**: `slack-fetcher`
- **Inputs**: `slack_config` (from config)
- **Outputs**: `slack_data`
- **Effects**: `mcp:slack`

**Output Schema**:
```json
{
  "messages": [
    {
      "channel": "#engineering",
      "author": "Alice",
      "text": "Deployed v2.0 to production",
      "timestamp": "2024-12-28T10:00:00Z",
      "thread_replies": 5,
      "reactions": ["rocket", "tada"]
    }
  ],
  "mentions": [
    {
      "channel": "#general",
      "author": "Bob",
      "text": "Hey @you, can you review this PR?",
      "timestamp": "2024-12-28T11:00:00Z"
    }
  ]
}
```

---

## Updated Graph

```yaml
name: full-v2

nodes:
  # Data gathering (parallel)
  - name: news
    transformer: news-fetcher
    inputs:
      topics: $config.news_topics

  - name: github
    transformer: github-fetcher
    inputs:
      repos_config: $config.github_repos

  - name: slack
    transformer: slack-fetcher
    inputs:
      slack_config: $config.slack_channels

  # Deduplication
  - name: dedupe
    transformer: story-deduplicator
    inputs:
      news_items: $news.gathered_data
      history_path: $config.history_path

  # Planning (now includes all sources)
  - name: plan
    transformer: brief-planner-v2
    inputs:
      news: $dedupe.filtered_news
      news_context: $dedupe.story_context  # Info about developments
      github: $github.github_data
      slack: $slack.slack_data

  # Generation
  - name: generate
    transformer: script-generator
    inputs:
      plan: $plan.plan
      all_data:
        news: $dedupe.filtered_news
        github: $github.github_data
        slack: $slack.slack_data
      narrator_style: $config.narrator_style
      target_duration: $config.target_duration

  # Update history (after generation succeeds)
  - name: history
    transformer: history-updater
    inputs:
      reported_items: $dedupe.items_to_report
      history_path: $config.history_path

  # Synthesis
  - name: synthesize
    transformer: piper-synthesizer
    inputs:
      script: $generate.script
      piper_model: $config.piper_model
      output_dir: $config.output_dir
```

---

## Implementation Phases

### Phase 1: Story History Store
1. Create `StoryHistory` data model
2. Create `ReportedStory` model with story_key
3. Implement JSON persistence (history file per day, rolling 7-day window)
4. Add history loading to executor

### Phase 2: Deduplication Transformer
1. Create `story-deduplicator` transformer
2. Implement Claude-based story key generation
3. Implement change detection prompt
4. Pass through new stories, filter stale repeats
5. Annotate developments with context

### Phase 3: GitHub Data Source
1. Create `github-fetcher` transformer
2. Add GitHub config schema
3. Implement MCP tool integration (via Claude)
4. Add to v2 graph

### Phase 4: Slack Data Source
1. Create `slack-fetcher` transformer
2. Add Slack config schema
3. Implement MCP tool integration (via Claude)
4. Add to v2 graph

### Phase 5: Updated Planner
1. Extend `brief-planner` to accept multiple data sources
2. Add logic for mixing news, GitHub, and Slack content
3. Handle story development annotations
4. Update planning prompt

### Phase 6: History Update
1. Create `history-updater` transformer
2. Record what was actually reported
3. Track developments on existing stories
4. Implement 7-day rolling cleanup

### Phase 7: Integration & Testing
1. End-to-end test with mocked sources
2. Test deduplication edge cases
3. Test story progression detection
4. Manual validation

---

## Open Questions

1. **MCP Configuration**: How do we pass MCP server credentials to Claude subprocess?
   - Environment variables?
   - MCP config file?

2. **Parallel Execution**: Can we run news, github, slack fetchers in parallel?
   - Need to check if executor supports this or if we need enhancement

3. **Story Key Stability**: How do we ensure story_key is consistent across runs?
   - May need to include examples in prompt
   - Could use embedding similarity as fallback

4. **History Storage Location**: Per-profile or global?
   - Probably per-profile for flexibility

---

## Success Criteria

1. No repeated stories without meaningful new information
2. Story developments are explicitly called out ("Continuing our coverage of...")
3. GitHub and Slack data integrated smoothly into briefings
4. History persists across runs and cleans up old entries
5. All existing v1 tests continue to pass
