import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path


def test_planner_accepts_data_sources_input():
    """Planner should accept data_sources input for all source types."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Check data_sources is in inputs (generic interface)
    assert "data_sources" in planner.inputs
    assert "story_context" in planner.inputs


def test_planner_includes_slack_source_in_prompt():
    """Planner should include Slack data when passed as a DataSource."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO, DataSource

    planner = BriefPlannerV2()

    slack_source = DataSource(
        name="slack",
        data={
            "messages": [{"text": "test", "author": "Alice"}],
            "summary": "Test summary"
        },
        prompt_fragment_path=Path("prompts/sources/slack.md"),
    )

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": []}'

        planner.process(TransformerIO(data={
            "data_sources": [slack_source],
            "story_context": [],
        }))

        # Check prompt includes Slack section
        prompt = mock_claude.call_args[0][0]
        assert "Slack" in prompt or "slack" in prompt.lower()
        assert "Test summary" in prompt or "test" in prompt


def test_render_source_with_slack_data():
    """_render_source should format Slack data using its prompt fragment."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import DataSource

    planner = BriefPlannerV2()

    slack_source = DataSource(
        name="slack",
        data={
            "summary": "Team discussed deployment plans",
            "messages": [
                {
                    "text": "Let's deploy tomorrow",
                    "author": "Alice",
                    "channel_name": "engineering",
                    "importance": "high"
                }
            ],
            "mentions": [
                {
                    "text": "Hey Frank, can you review the PR?",
                    "author": "Carol"
                }
            ]
        },
        prompt_fragment_path=Path("prompts/sources/slack.md"),
    )

    result = planner._render_source(slack_source)

    # Check fragment header is present
    assert "Slack Highlights" in result
    # Check data is included
    assert "Team discussed deployment plans" in result
    assert "Alice" in result
    assert "Let's deploy tomorrow" in result
    assert "Carol" in result


def test_render_source_fallback_for_missing_fragment():
    """_render_source should use fallback format when fragment is missing."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import DataSource

    planner = BriefPlannerV2()

    # Source without a prompt fragment path
    custom_source = DataSource(
        name="custom",
        data={"key": "value"},
        prompt_fragment_path=None,
    )

    result = planner._render_source(custom_source)

    # Should use fallback format with capitalized name
    assert "## Custom" in result
    assert "value" in result


def test_planner_works_without_data_sources():
    """Planner should work when data_sources is empty."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO

    planner = BriefPlannerV2()

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0, "estimated_duration_minutes": 1}'

        # Empty data_sources list - should not raise
        result = planner.process(TransformerIO(data={
            "data_sources": [],
            "story_context": [],
        }))

        assert "plan" in result.data

        # Prompt should indicate no data sources
        prompt = mock_claude.call_args[0][0]
        assert "No data sources available" in prompt
