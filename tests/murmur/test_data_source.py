import pytest
from pathlib import Path


def test_data_source_structure():
    """DataSource should have name, data, and prompt_fragment_path."""
    from murmur.core import DataSource

    source = DataSource(
        name="test-source",
        data={"items": [1, 2, 3]},
        prompt_fragment_path=Path("prompts/sources/test.md"),
    )

    assert source.name == "test-source"
    assert source.data == {"items": [1, 2, 3]}
    assert source.prompt_fragment_path == Path("prompts/sources/test.md")


def test_data_source_optional_prompt():
    """DataSource prompt_fragment_path should be optional."""
    from murmur.core import DataSource

    source = DataSource(
        name="simple-source",
        data={"value": 42},
    )

    assert source.name == "simple-source"
    assert source.prompt_fragment_path is None
