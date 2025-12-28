import json
from unittest.mock import patch
from murmur.core import TransformerIO
from murmur.transformers.news_fetcher import NewsFetcher


def test_news_fetcher_has_correct_metadata():
    """NewsFetcher should declare correct inputs/outputs/effects."""
    fetcher = NewsFetcher()
    assert fetcher.name == "news-fetcher"
    assert fetcher.inputs == ["topics"]
    assert fetcher.outputs == ["gathered_data"]
    assert "llm" in fetcher.input_effects


def test_news_fetcher_calls_claude():
    """NewsFetcher should call Claude with topics and return parsed JSON."""
    mock_response = json.dumps({
        "items": [
            {
                "topic": "AI",
                "headline": "New AI breakthrough",
                "source": "Tech News",
                "summary": "Researchers announced a new model.",
                "url": "https://example.com/ai"
            }
        ],
        "gathered_at": "2024-12-27T10:00:00Z"
    })

    with patch("murmur.transformers.news_fetcher.run_claude", return_value=mock_response):
        fetcher = NewsFetcher()
        input_io = TransformerIO(data={
            "topics": [
                {"name": "AI", "query": "artificial intelligence news", "priority": "high"}
            ]
        })

        result = fetcher.process(input_io)

        assert "gathered_data" in result.data
        assert len(result.data["gathered_data"]["items"]) == 1
        assert result.data["gathered_data"]["items"][0]["headline"] == "New AI breakthrough"
