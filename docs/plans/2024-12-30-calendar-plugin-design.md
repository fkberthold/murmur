# Calendar Plugin Design

## Overview

Add Google Calendar as a data source using the same plugin pattern as Slack. Fetches today's remaining events and tomorrow's notable events via MCP tools.

## Components

| Component | File | Reference |
|-----------|------|-----------|
| Config schema | `src/murmur/config/calendar.py` | `slack.py` |
| Transformer | `src/murmur/transformers/calendar_fetcher.py` | `slack_fetcher.py` |
| Gather prompt | `prompts/calendar_gather.md` | `slack_gather.md` |
| Planner fragment | `prompts/sources/calendar.md` | `sources/slack.md` |
| User config | `config/calendar.yaml` | `slack.yaml` |
| Tests | `tests/murmur/test_calendar_fetcher.py` | `test_slack_fetcher.py` |

## Config Schema

```python
@dataclass
class Calendar:
    name: str           # "Personal", "Work", "Family"
    id: str             # Google Calendar ID
    type: str = "personal"  # "personal" | "work"
    enabled: bool = True
    timezone: str = ""  # Source timezone if different from display

@dataclass
class EventRule:
    pattern: str        # Regex pattern for event title
    rule: str           # "always_skip" | "always_mention" | "canceled_only"
    calendar: str = ""  # Optional: limit to specific calendar
    priority: str = "medium"

@dataclass
class CalendarSettings:
    display_timezone: str = "America/New_York"
    include_all_day: bool = True
    include_tentative: bool = True
    include_declined: bool = False
    max_today_events: int = 10
    max_tomorrow_events: int = 5

@dataclass
class CalendarConfig:
    calendars: list[Calendar]
    event_rules: list[EventRule]
    notable_patterns: list[str]  # ["flight", "doctor", "interview", ...]
    settings: CalendarSettings
```

## Data Flow

```
calendar.yaml → CalendarFetcher → MCP tools → JSON → DataSource → Planner
```

## MCP Tools

- `mcp__google-calendar__list-events` - fetch events from calendars
- `mcp__google-calendar__get-current-time` - get current time in timezone

Timezone conversion handled by passing `display_timezone` to MCP's `timeZone` parameter.

## Gather Prompt Template

Variables:
- `{{calendars}}` - list with IDs and timezones
- `{{event_rules}}` - formatted skip/mention rules
- `{{notable_patterns}}` - keywords like "flight", "doctor"
- `{{display_timezone}}` - target timezone
- `{{today_start}}`, `{{today_end}}`, `{{tomorrow_start}}`, `{{tomorrow_end}}`

Output JSON:
```json
{
  "today_events": [
    {
      "calendar_name": "Work",
      "title": "Team Standup",
      "start_time": "2024-12-30T10:00:00",
      "end_time": "2024-12-30T10:30:00",
      "is_all_day": false,
      "location": null,
      "status": "confirmed",
      "is_recurring": true,
      "attendee_count": 5
    }
  ],
  "tomorrow_notable": [...],
  "canceled_events": [...],
  "summary": "3 meetings remaining today, dentist appointment tomorrow"
}
```

## Planner Fragment

```markdown
## Calendar Events

The following events are from the user's Google Calendar.

{{data}}

When calendar data is present:
- Lead with today's remaining schedule if significant
- Mention notable tomorrow events (appointments, travel, deadlines)
- Skip routine recurring meetings unless canceled
- Use natural time references ("this afternoon", "tomorrow morning")
- Note scheduling conflicts or busy periods
```

## Graph Integration

Add to `config/graphs/full-v2b.yaml`:
```yaml
- name: calendar
  transformer: calendar-fetcher
  inputs:
    calendar_config_path: $config.calendar_config_path
    mcp_config_path: $config.mcp_config_path
```

Add `$calendar.calendar` to planner's `data_sources` list.

## Event Rules

| Rule | Behavior |
|------|----------|
| `always_skip` | Never include in briefing |
| `always_mention` | Always include regardless of routine detection |
| `canceled_only` | Only mention if the event was canceled |

## Notable Event Detection

Events containing keywords from `notable_patterns` are always considered notable for tomorrow's lookahead. Examples: flight, doctor, interview, deadline, presentation.

Routine events (daily standups, recurring 1:1s) are filtered out of tomorrow's notable list unless they match `always_mention` or `canceled_only` rules.
