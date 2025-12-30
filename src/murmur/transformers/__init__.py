# src/murmur/transformers/__init__.py
from murmur.registry import TransformerRegistry
from murmur.transformers.news_fetcher import NewsFetcher
from murmur.transformers.brief_planner import BriefPlanner
from murmur.transformers.brief_planner_v2 import BriefPlannerV2
from murmur.transformers.script_generator import ScriptGenerator
from murmur.transformers.piper_synthesizer import PiperSynthesizer
from murmur.transformers.story_deduplicator import StoryDeduplicator
from murmur.transformers.history_updater import HistoryUpdater
from murmur.transformers.slack_fetcher import SlackFetcher
from murmur.transformers.calendar_fetcher import CalendarFetcher


def create_registry() -> TransformerRegistry:
    """Create and populate the transformer registry."""
    registry = TransformerRegistry()
    registry.register(NewsFetcher)
    registry.register(BriefPlanner)
    registry.register(BriefPlannerV2)
    registry.register(ScriptGenerator)
    registry.register(PiperSynthesizer)
    registry.register(StoryDeduplicator)
    registry.register(HistoryUpdater)
    registry.register(SlackFetcher)
    registry.register(CalendarFetcher)
    return registry
