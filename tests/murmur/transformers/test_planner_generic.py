import pytest
from unittest.mock import patch
from pathlib import Path


def test_planner_accepts_data_sources_list():
    """Planner should accept a list of DataSource objects."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2

    planner = BriefPlannerV2()

    # Should have generic 'data_sources' input, not source-specific inputs
    assert "data_sources" in planner.inputs
    assert "slack_data" not in planner.inputs
    assert "gathered_data" not in planner.inputs


def test_planner_assembles_prompt_from_sources():
    """Planner should dynamically build prompt from DataSource fragments."""
    from murmur.transformers.brief_planner_v2 import BriefPlannerV2
    from murmur.core import TransformerIO, DataSource

    planner = BriefPlannerV2()

    # Create test sources
    news_source = DataSource(
        name="news",
        data={"items": [{"headline": "Test News"}]},
        prompt_fragment_path=Path("prompts/sources/news.md"),
    )
    slack_source = DataSource(
        name="slack",
        data={"messages": [{"text": "Hello team"}]},
        prompt_fragment_path=Path("prompts/sources/slack.md"),
    )

    with patch('murmur.transformers.brief_planner_v2.run_claude') as mock_claude:
        mock_claude.return_value = '{"sections": [], "total_items": 0}'

        planner.process(TransformerIO(data={
            "data_sources": [news_source, slack_source],
            "story_context": [],
        }))

        # Check prompt was built with both sources
        prompt = mock_claude.call_args[0][0]
        assert "News Items" in prompt  # From news.md fragment
        assert "Slack Highlights" in prompt  # From slack.md fragment
        assert "Test News" in prompt  # Data was included
        assert "Hello team" in prompt  # Data was included
