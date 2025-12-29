from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.script_generator import ScriptGenerator


def test_script_generator_has_correct_metadata():
    """ScriptGenerator should declare correct inputs/outputs/effects."""
    generator = ScriptGenerator()
    assert generator.name == "script-generator"
    assert "plan" in generator.inputs
    assert "gathered_data" in generator.inputs
    assert generator.outputs == ["script"]
    assert "llm" in generator.input_effects


def test_script_generator_calls_claude():
    """ScriptGenerator should call Claude and return script text."""
    mock_response = "Good morning! Here's your briefing for today. First up, exciting news in AI..."

    with patch("murmur.transformers.script_generator.run_claude", return_value=mock_response):
        generator = ScriptGenerator()
        input_io = TransformerIO(data={
            "plan": {"sections": [{"title": "AI", "items": ["headline"]}]},
            "gathered_data": {"items": []},
            "narrator_style": "warm-professional",
            "target_duration": 5
        })

        result = generator.process(input_io)

        assert "script" in result.data
        assert "Good morning" in result.data["script"]
