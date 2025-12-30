import pytest
from unittest.mock import patch, MagicMock


def test_planner_accepts_slack_input():
    """Planner should accept optional slack_data input."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Check slack_data is in inputs
    assert "slack_data" in planner.inputs


def test_planner_includes_slack_in_prompt():
    """Planner should include Slack data in prompt when provided."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch.object(planner, '_format_slack_data') as mock_format:
        mock_format.return_value = "## Slack Highlights\n- Important message"

        with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
            mock_claude.return_value = '{"sections": []}'

            slack_data = {
                "messages": [{"text": "test", "author": "Alice"}],
                "summary": "Test summary"
            }

            planner.process(TransformerIO(data={
                "gathered_data": {"items": []},
                "story_context": [],
                "slack_data": slack_data,
            }))

            # Check prompt includes Slack section
            prompt = mock_claude.call_args[0][0]
            assert "Slack" in prompt or "slack" in prompt.lower()


def test_format_slack_data_with_messages():
    """_format_slack_data should format messages properly."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    slack_data = {
        "summary": "Team discussed deployment plans",
        "messages": [
            {
                "text": "Let's deploy tomorrow",
                "author": "Alice",
                "channel_name": "engineering",
                "importance": "high"
            },
            {
                "text": "Sounds good to me",
                "author": "Bob",
                "channel_name": "engineering",
                "importance": "medium"
            }
        ],
        "mentions": [
            {
                "text": "Hey Frank, can you review the PR?",
                "author": "Carol"
            }
        ]
    }

    result = planner._format_slack_data(slack_data)

    assert "Team discussed deployment plans" in result
    assert "Alice" in result
    assert "Let's deploy tomorrow" in result
    assert "#engineering" in result
    assert "high" in result
    assert "Carol" in result


def test_format_slack_data_empty():
    """_format_slack_data should handle empty data gracefully."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Empty dict - treated as no data
    result = planner._format_slack_data({})
    assert "No Slack data" in result

    # None
    result = planner._format_slack_data(None)
    assert "No Slack data" in result

    # Dict with empty lists - no significant activity
    result = planner._format_slack_data({"messages": [], "mentions": []})
    assert "No significant Slack activity" in result


def test_planner_works_without_slack_data():
    """Planner should work when slack_data is not provided (backward compatibility)."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0, "estimated_duration_minutes": 1}'

        # No slack_data provided - should not raise
        result = planner.process(TransformerIO(data={
            "gathered_data": {"items": []},
            "story_context": [],
        }))

        assert "plan" in result.data
