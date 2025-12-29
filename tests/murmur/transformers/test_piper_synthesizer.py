from pathlib import Path
from unittest.mock import patch, MagicMock
from murmur.core import TransformerIO
from murmur.transformers.piper_synthesizer import PiperSynthesizer


def test_piper_synthesizer_has_correct_metadata():
    """PiperSynthesizer should declare correct inputs/outputs/effects."""
    synth = PiperSynthesizer()
    assert synth.name == "piper-synthesizer"
    assert "script" in synth.inputs
    assert synth.outputs == ["audio"]
    assert "tts" in synth.output_effects
    assert "filesystem" in synth.output_effects


def test_piper_synthesizer_creates_audio(tmp_path):
    """PiperSynthesizer should create audio file and return path."""
    output_path = tmp_path / "test.wav"

    with patch("murmur.transformers.piper_synthesizer.synthesize_with_piper") as mock_synth:
        mock_synth.return_value = output_path
        # Create a fake file so the symlink works
        output_path.write_bytes(b"fake audio")

        synth = PiperSynthesizer()
        input_io = TransformerIO(data={
            "script": "Hello, this is a test.",
            "piper_model": "en_US-libritts_r-medium",
            "output_dir": str(tmp_path),
        })

        result = synth.process(input_io)

        assert "audio" in result.data
        assert "audio" in result.artifacts
        mock_synth.assert_called_once()
