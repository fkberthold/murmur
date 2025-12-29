from pathlib import Path
from murmur.core import Transformer, TransformerIO
from murmur.lib.piper import synthesize_with_piper


class PiperSynthesizer(Transformer):
    """Synthesizes script to audio using Piper TTS."""

    name = "piper-synthesizer"
    inputs = ["script", "piper_model", "output_dir"]
    outputs = ["audio"]
    input_effects = []
    output_effects = ["tts", "filesystem"]

    def process(self, input: TransformerIO) -> TransformerIO:
        script = input.data.get("script", "")
        model_name = input.data.get("piper_model", "en_US-libritts_r-medium")
        output_dir = Path(input.data.get("output_dir", "output"))
        sentence_silence = input.data.get("sentence_silence", 0.3)

        # Construct model path
        model_path = Path("models/piper") / f"{model_name}.onnx"

        # Synthesize
        audio_path = synthesize_with_piper(
            text=script,
            model_path=model_path,
            output_dir=output_dir,
            sentence_silence=sentence_silence,
        )

        # Create latest.wav symlink
        latest_path = output_dir / "latest.wav"
        if latest_path.exists() or latest_path.is_symlink():
            latest_path.unlink()
        latest_path.symlink_to(audio_path.name)

        return TransformerIO(
            data={"audio": str(audio_path)},
            artifacts={"audio": audio_path}
        )
