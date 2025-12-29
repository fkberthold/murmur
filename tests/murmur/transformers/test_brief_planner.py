import json
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.brief_planner import BriefPlanner


def test_brief_planner_has_correct_metadata():
    """BriefPlanner should declare correct inputs/outputs/effects."""
    planner = BriefPlanner()
    assert planner.name == "brief-planner"
    assert planner.inputs == ["gathered_data"]
    assert planner.outputs == ["plan"]
    assert "llm" in planner.input_effects


def test_brief_planner_calls_claude():
    """BriefPlanner should call Claude with gathered data and return plan."""
    mock_response = json.dumps({
        "sections": [
            {
                "title": "AI Developments",
                "items": ["New AI breakthrough"],
                "connection": "Recent advances in AI",
                "transition_to_next": "Speaking of technology..."
            }
        ],
        "total_items": 1,
        "estimated_duration_minutes": 3
    })

    with patch("murmur.transformers.brief_planner.run_claude", return_value=mock_response):
        planner = BriefPlanner()
        input_io = TransformerIO(data={
            "gathered_data": {
                "items": [{"headline": "New AI breakthrough", "summary": "..."}]
            }
        })

        result = planner.process(input_io)

        assert "plan" in result.data
        assert len(result.data["plan"]["sections"]) == 1
