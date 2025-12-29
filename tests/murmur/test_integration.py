"""
Integration test for full pipeline with mocked Claude and Piper.
"""
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from murmur.registry import TransformerRegistry
from murmur.executor import GraphExecutor
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer


def test_full_pipeline_mocked(tmp_path):
    """Full pipeline should execute with mocked external dependencies."""

    # Create graph
    graph = {
        "name": "test-full",
        "nodes": [
            {
                "name": "gather",
                "transformer": "news-fetcher",
                "inputs": {"topics": "$config.news_topics"},
            },
            {
                "name": "plan",
                "transformer": "brief-planner",
                "inputs": {"gathered_data": "$gather.gathered_data"},
            },
            {
                "name": "generate",
                "transformer": "script-generator",
                "inputs": {
                    "plan": "$plan.plan",
                    "gathered_data": "$gather.gathered_data",
                    "narrator_style": "$config.narrator_style",
                    "target_duration": "$config.target_duration",
                },
            },
            {
                "name": "synthesize",
                "transformer": "piper-synthesizer",
                "inputs": {
                    "script": "$generate.script",
                    "piper_model": "$config.piper_model",
                    "output_dir": "$config.output_dir",
                },
            },
        ],
    }

    # Build registry
    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)
    registry.register(ScriptGenerator)
    registry.register(PiperSynthesizer)

    # Config
    config = {
        "news_topics": [{"name": "AI", "query": "AI news", "priority": "high"}],
        "narrator_style": "warm-professional",
        "target_duration": 5,
        "piper_model": "en_US-libritts_r-medium",
        "output_dir": str(tmp_path / "output"),
    }

    # Mock responses
    gather_response = json.dumps({
        "items": [{"topic": "AI", "headline": "AI News", "summary": "Summary"}],
        "gathered_at": "2024-12-27T10:00:00Z",
    })
    plan_response = json.dumps({
        "sections": [{"title": "AI", "items": ["AI News"]}],
        "total_items": 1,
        "estimated_duration_minutes": 3,
    })
    generate_response = "Good morning! Here's your AI briefing. Exciting developments today."

    def mock_claude(prompt, allowed_tools=None):
        if "news researcher" in prompt.lower():
            return gather_response
        elif "briefing planner" in prompt.lower():
            return plan_response
        else:
            return generate_response

    output_audio = tmp_path / "output" / "brief_test.wav"
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    output_audio.write_bytes(b"fake audio")

    with patch("murmur.transformers.news_fetcher.run_claude", side_effect=mock_claude):
        with patch("murmur.transformers.brief_planner.run_claude", side_effect=mock_claude):
            with patch("murmur.transformers.script_generator.run_claude", side_effect=mock_claude):
                with patch("murmur.transformers.piper_synthesizer.synthesize_with_piper", return_value=output_audio):
                    executor = GraphExecutor(
                        graph,
                        registry,
                        artifact_dir=tmp_path / "artifacts",
                    )
                    result = executor.execute(config)

    # Verify all nodes executed
    assert "gather" in result.data
    assert "plan" in result.data
    assert "generate" in result.data
    assert "synthesize" in result.data

    # Verify artifacts
    assert "audio" in result.artifacts

    # Verify intermediate artifacts saved
    artifacts = list((tmp_path / "artifacts").glob("*.json"))
    assert len(artifacts) == 4  # One per node


def test_partial_pipeline_with_caching(tmp_path):
    """Pipeline should use cached nodes when specified."""

    graph = {
        "name": "test-cached",
        "nodes": [
            {
                "name": "gather",
                "transformer": "news-fetcher",
                "inputs": {"topics": "$config.news_topics"},
            },
            {
                "name": "plan",
                "transformer": "brief-planner",
                "inputs": {"gathered_data": "$gather.gathered_data"},
            },
        ],
    }

    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)

    config = {
        "news_topics": [{"name": "Tech", "query": "tech news", "priority": "high"}],
    }

    # Pre-create cached artifact for gather node
    run_id = "test_run_123"
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir(parents=True, exist_ok=True)
    cached_file = artifact_dir / f"{run_id}_gather.json"
    cached_data = {
        "gathered_data": {
            "items": [{"topic": "Tech", "headline": "Cached Tech News", "summary": "Cached summary"}],
            "gathered_at": "2024-12-27T09:00:00Z",
        }
    }
    cached_file.write_text(json.dumps(cached_data))

    plan_response = json.dumps({
        "sections": [{"title": "Tech", "items": ["Cached Tech News"]}],
        "total_items": 1,
        "estimated_duration_minutes": 2,
    })

    with patch("murmur.transformers.brief_planner.run_claude", return_value=plan_response):
        # Note: news_fetcher.run_claude should NOT be called since gather is cached
        executor = GraphExecutor(
            graph,
            registry,
            artifact_dir=artifact_dir,
            cached_nodes=["gather"],
            run_id=run_id,
        )
        result = executor.execute(config)

    # Verify cached data was used
    assert "gather" in result.data
    assert result.data["gather"]["gathered_data"]["items"][0]["headline"] == "Cached Tech News"

    # Verify plan was executed with cached data
    assert "plan" in result.data
    assert result.data["plan"]["plan"]["sections"][0]["items"][0] == "Cached Tech News"


def test_graph_with_config_defaults(tmp_path):
    """Pipeline should handle config defaults and missing optional inputs."""

    graph = {
        "name": "test-defaults",
        "nodes": [
            {
                "name": "generate",
                "transformer": "script-generator",
                "inputs": {
                    "plan": "$config.plan",
                    "gathered_data": "$config.gathered_data",
                    "narrator_style": "$config.narrator_style",
                    "target_duration": "$config.target_duration",
                },
            },
        ],
    }

    registry = TransformerRegistry()
    registry.register(ScriptGenerator)

    config = {
        "plan": {"sections": [{"title": "Test", "items": ["Item1"]}]},
        "gathered_data": {"items": []},
        "narrator_style": "warm-professional",
        "target_duration": 3,
    }

    script_response = "Good morning! Here is a brief update."

    with patch("murmur.transformers.script_generator.run_claude", return_value=script_response):
        executor = GraphExecutor(
            graph,
            registry,
            artifact_dir=tmp_path / "artifacts",
        )
        result = executor.execute(config)

    assert "generate" in result.data
    assert result.data["generate"]["script"] == script_response
