# Slack Integration Setup

Murmur can integrate Slack messages into your daily briefings using the MCP (Model Context Protocol) Slack server.

## Prerequisites

1. Docker installed and running
2. A Slack workspace where you can create apps
3. A Slack User Token (xoxp-*)

## Getting a Slack Token

1. Go to https://api.slack.com/apps
2. Create a new app (or use existing)
3. Under "OAuth & Permissions", add these scopes:
   - `channels:history`
   - `channels:read`
   - `search:read`
   - `users:read`
4. Install the app to your workspace
5. Copy the "User OAuth Token" (starts with `xoxp-`)

## Configuration

1. Create `.env` file with your token:

```bash
SLACK_USER_TOKEN=xoxp-your-token-here
```

2. Configure channels in `config/slack.yaml`:

```yaml
channels:
  - name: "general"
    id: "C123456789"  # Get from channel details
    priority: high

colleagues:
  - name: "Alice"
    slack_id: "U123456789"

settings:
  lookback_hours: 24
  include_threads: true
```

3. Use the `work` profile to include Slack:

```bash
murmur generate --profile work
```

## Finding Channel and User IDs

- **Channel ID**: Right-click channel name -> "Copy link" -> ID is at end of URL
- **User ID**: Click profile -> "More" -> "Copy member ID"

## Troubleshooting

### Docker not running
Ensure Docker Desktop is running before generating briefs.

### Token errors
Verify your token starts with `xoxp-` and has the required scopes.

### No messages found
Check that lookback_hours covers the time range you expect.
