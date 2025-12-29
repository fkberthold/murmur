# tests/murmur/transformers/test_brief_planner_v2.py
import json
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.brief_planner_v2 import BriefPlannerV2


def test_brief_planner_v2_has_correct_metadata():
    """BriefPlannerV2 should accept story_context input."""
    planner = BriefPlannerV2()

    assert planner.name == "brief-planner-v2"
    assert "gathered_data" in planner.inputs
    assert "story_context" in planner.inputs
    assert "plan" in planner.outputs


def test_brief_planner_v2_includes_story_context():
    """BriefPlannerV2 should pass story context to prompt."""
    mock_response = json.dumps({
        "sections": [{"title": "Test", "items": ["Item 1"]}],
        "total_items": 1,
    })

    with patch("murmur.transformers.brief_planner_v2.run_claude", return_value=mock_response) as mock_claude:
        planner = BriefPlannerV2()
        input_io = TransformerIO(data={
            "gathered_data": {"items": [{"headline": "Test"}]},
            "story_context": [{"story_key": "test-story", "type": "development", "note": "Update"}],
        })

        planner.process(input_io)

        # Verify prompt includes story context
        call_args = mock_claude.call_args
        prompt = call_args[0][0]
        assert "development" in prompt.lower() or "continuing" in prompt.lower()
