from pathlib import Path
from murmur.core import Transformer, TransformerIO


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


class EchoTransformer(Transformer):
    """Test transformer that echoes input to output."""
    name = "echo"
    inputs = ["message"]
    outputs = ["echoed"]
    input_effects = []
    output_effects = []

    def process(self, input: TransformerIO) -> TransformerIO:
        return TransformerIO(
            data={"echoed": input.data.get("message", "")},
            artifacts=input.artifacts
        )


def test_transformer_has_required_attributes():
    """Transformer subclass should have name, inputs, outputs, effects."""
    t = EchoTransformer()
    assert t.name == "echo"
    assert t.inputs == ["message"]
    assert t.outputs == ["echoed"]
    assert t.input_effects == []
    assert t.output_effects == []


def test_transformer_process():
    """Transformer.process should transform input to output."""
    t = EchoTransformer()
    result = t.process(TransformerIO(data={"message": "hello"}))
    assert result.data["echoed"] == "hello"
