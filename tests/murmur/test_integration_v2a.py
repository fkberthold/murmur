# tests/murmur/test_integration_v2a.py
"""Integration tests for v2a story continuity."""
import json
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch
from murmur.history import StoryHistory, ReportedStory
from murmur.transformers import create_registry
from murmur.executor import GraphExecutor
import yaml


def test_full_v2a_graph_skips_duplicates(tmp_path):
    """Full v2a pipeline should skip duplicate stories."""
    # Setup: Create history with existing story
    history_path = tmp_path / "history.json"
    history = StoryHistory()
    history.add(ReportedStory(
        id="existing",
        url="https://example.com/old",
        title="Micron Beats Q4 Earnings",
        summary="Micron reported earnings above expectations.",
        topic="Tech",
        story_key="micron-q4-2024-earnings",
        reported_at=datetime.now() - timedelta(days=1),
    ))
    history.save(history_path)

    # Load graph
    graph_path = Path(__file__).parent.parent.parent / "config" / "graphs" / "full-v2a.yaml"

    # Skip if graph doesn't exist yet
    if not graph_path.exists():
        return

    with open(graph_path) as f:
        graph = yaml.safe_load(f)

    # Mock responses
    gather_response = json.dumps({
        "items": [
            {"headline": "New AI Model", "topic": "AI", "summary": "A new model."},
            {"headline": "Micron Stock Rises", "topic": "Tech", "summary": "Micron stock up."},
        ],
        "gathered_at": datetime.now().isoformat(),
    })

    dedupe_response = json.dumps({
        "items": [
            {"candidate_index": 0, "story_key": "new-ai-model", "action": "include_as_new", "reason": "New"},
            {"candidate_index": 1, "story_key": "micron-q4-2024-earnings", "action": "skip", "skip_reason": "Same story"},
        ]
    })

    plan_response = json.dumps({
        "sections": [{"title": "AI", "items": ["New AI Model"]}],
        "total_items": 1,
    })

    script_response = "Today in AI news, a new model was released."

    # Track which calls we've made
    call_count = {"gather": 0, "dedupe": 0, "plan": 0, "script": 0}

    def mock_gather(*args, **kwargs):
        call_count["gather"] += 1
        return gather_response

    def mock_dedupe(*args, **kwargs):
        call_count["dedupe"] += 1
        return dedupe_response

    def mock_plan(*args, **kwargs):
        call_count["plan"] += 1
        return plan_response

    def mock_script(*args, **kwargs):
        call_count["script"] += 1
        return script_response

    with patch("murmur.transformers.news_fetcher.run_claude", side_effect=mock_gather):
        with patch("murmur.transformers.story_deduplicator.run_claude", side_effect=mock_dedupe):
            with patch("murmur.transformers.brief_planner_v2.run_claude", side_effect=mock_plan):
                with patch("murmur.transformers.script_generator.run_claude", side_effect=mock_script):
                    registry = create_registry()

                    # Remove synthesize node for test (no TTS needed)
                    graph["nodes"] = [n for n in graph["nodes"] if n["name"] != "synthesize"]

                    executor = GraphExecutor(graph, registry, artifact_dir=tmp_path / "artifacts")

                    config = {
                        "news_topics": [{"name": "Tech", "query": "tech news"}],
                        "history_path": str(history_path),
                        "narrator_style": "warm-professional",
                        "target_duration": 5,
                    }

                    result = executor.execute(config)

                    # Verify only 1 item made it through (the AI story)
                    assert len(result.data["dedupe"]["filtered_news"]["items"]) == 1
                    assert result.data["dedupe"]["filtered_news"]["items"][0]["headline"] == "New AI Model"

                    # Verify story context was populated
                    assert len(result.data["dedupe"]["story_context"]) == 1
                    assert result.data["dedupe"]["story_context"][0]["story_key"] == "new-ai-model"
                    assert result.data["dedupe"]["story_context"][0]["type"] == "new"

                    # Verify items_to_report only has the new story
                    assert len(result.data["dedupe"]["items_to_report"]) == 1
                    assert result.data["dedupe"]["items_to_report"][0]["story_key"] == "new-ai-model"

                    # Verify all nodes executed
                    assert "gather" in result.data
                    assert "dedupe" in result.data
                    assert "plan" in result.data
                    assert "generate" in result.data
                    assert "history" in result.data

                    # Verify all Claude calls were made
                    assert call_count["gather"] == 1
                    assert call_count["dedupe"] == 1
                    assert call_count["plan"] == 1
                    assert call_count["script"] == 1


def test_v2a_graph_includes_development(tmp_path):
    """V2a pipeline should include stories marked as developments."""
    # Setup: Create history with existing story
    history_path = tmp_path / "history.json"
    history = StoryHistory()
    history.add(ReportedStory(
        id="existing",
        url="https://example.com/old",
        title="OpenAI Announces GPT-5",
        summary="OpenAI revealed plans for GPT-5.",
        topic="AI",
        story_key="openai-gpt5-announcement",
        reported_at=datetime.now() - timedelta(days=2),
    ))
    history.save(history_path)

    # Load graph
    graph_path = Path(__file__).parent.parent.parent / "config" / "graphs" / "full-v2a.yaml"

    if not graph_path.exists():
        return

    with open(graph_path) as f:
        graph = yaml.safe_load(f)

    # Mock responses - this time the Micron story is a development
    gather_response = json.dumps({
        "items": [
            {"headline": "GPT-5 Release Date Confirmed", "topic": "AI", "summary": "OpenAI confirms Q1 release."},
        ],
        "gathered_at": datetime.now().isoformat(),
    })

    dedupe_response = json.dumps({
        "items": [
            {
                "candidate_index": 0,
                "story_key": "openai-gpt5-announcement",
                "action": "include_as_development",
                "development_note": "Release date confirmed for Q1",
                "existing_story_id": "existing",
            },
        ]
    })

    plan_response = json.dumps({
        "sections": [{"title": "AI", "items": ["GPT-5 Release Date Confirmed"]}],
        "total_items": 1,
    })

    script_response = "An update on a story we've been following: GPT-5 now has a release date."

    with patch("murmur.transformers.news_fetcher.run_claude", return_value=gather_response):
        with patch("murmur.transformers.story_deduplicator.run_claude", return_value=dedupe_response):
            with patch("murmur.transformers.brief_planner_v2.run_claude", return_value=plan_response):
                with patch("murmur.transformers.script_generator.run_claude", return_value=script_response):
                    registry = create_registry()

                    # Remove synthesize node
                    graph["nodes"] = [n for n in graph["nodes"] if n["name"] != "synthesize"]

                    executor = GraphExecutor(graph, registry, artifact_dir=tmp_path / "artifacts")

                    config = {
                        "news_topics": [{"name": "AI", "query": "AI news"}],
                        "history_path": str(history_path),
                        "narrator_style": "warm-professional",
                        "target_duration": 5,
                    }

                    result = executor.execute(config)

                    # Verify the development was included
                    assert len(result.data["dedupe"]["filtered_news"]["items"]) == 1

                    # Verify story context shows it's a development
                    assert len(result.data["dedupe"]["story_context"]) == 1
                    assert result.data["dedupe"]["story_context"][0]["type"] == "development"
                    assert "Release date confirmed" in result.data["dedupe"]["story_context"][0]["note"]


def test_v2a_empty_history(tmp_path):
    """V2a pipeline should work with no prior history."""
    history_path = tmp_path / "history.json"
    # Don't create history file - should handle missing file

    graph_path = Path(__file__).parent.parent.parent / "config" / "graphs" / "full-v2a.yaml"

    if not graph_path.exists():
        return

    with open(graph_path) as f:
        graph = yaml.safe_load(f)

    gather_response = json.dumps({
        "items": [
            {"headline": "Breaking News", "topic": "Tech", "summary": "Something happened."},
        ],
        "gathered_at": datetime.now().isoformat(),
    })

    # All items are new when history is empty
    dedupe_response = json.dumps({
        "items": [
            {"candidate_index": 0, "story_key": "breaking-news-tech", "action": "include_as_new", "reason": "New story"},
        ]
    })

    plan_response = json.dumps({
        "sections": [{"title": "Tech", "items": ["Breaking News"]}],
        "total_items": 1,
    })

    script_response = "Here's what's happening in tech today."

    with patch("murmur.transformers.news_fetcher.run_claude", return_value=gather_response):
        with patch("murmur.transformers.story_deduplicator.run_claude", return_value=dedupe_response):
            with patch("murmur.transformers.brief_planner_v2.run_claude", return_value=plan_response):
                with patch("murmur.transformers.script_generator.run_claude", return_value=script_response):
                    registry = create_registry()

                    graph["nodes"] = [n for n in graph["nodes"] if n["name"] != "synthesize"]

                    executor = GraphExecutor(graph, registry, artifact_dir=tmp_path / "artifacts")

                    config = {
                        "news_topics": [{"name": "Tech", "query": "tech news"}],
                        "history_path": str(history_path),
                        "narrator_style": "warm-professional",
                        "target_duration": 5,
                    }

                    result = executor.execute(config)

                    # Verify story made it through
                    assert len(result.data["dedupe"]["filtered_news"]["items"]) == 1
                    assert result.data["dedupe"]["filtered_news"]["items"][0]["headline"] == "Breaking News"

                    # Verify history was updated
                    assert result.data["history"]["updated_count"]["new"] == 1
