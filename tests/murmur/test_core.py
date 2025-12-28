from pathlib import Path
from murmur.core import TransformerIO


def test_transformer_io_defaults():
    """TransformerIO should initialize with empty defaults."""
    io = TransformerIO()
    assert io.data == {}
    assert io.artifacts == {}


def test_transformer_io_with_data():
    """TransformerIO should accept data and artifacts."""
    io = TransformerIO(
        data={"key": "value"},
        artifacts={"audio": Path("/tmp/test.mp3")}
    )
    assert io.data["key"] == "value"
    assert io.artifacts["audio"] == Path("/tmp/test.mp3")
