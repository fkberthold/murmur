from pathlib import Path
from datetime import datetime


def synthesize_with_piper(
    text: str,
    model_path: Path,
    output_dir: Path,
    sentence_silence: float = 0.3,
) -> Path:
    """
    Synthesize text to audio using Piper TTS.

    Args:
        text: Text to synthesize
        model_path: Path to Piper .onnx model file
        output_dir: Directory to save output
        sentence_silence: Pause between sentences in seconds

    Returns:
        Path to generated WAV file
    """
    try:
        from piper import PiperVoice
        import wave
    except ImportError:
        raise ImportError("piper-tts not installed. Run: pip install piper-tts")

    # Load voice model
    voice = PiperVoice.load(str(model_path))

    # Generate audio
    audio_data = voice.synthesize(text, sentence_silence=sentence_silence)

    # Save to WAV file
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"brief_{timestamp}.wav"

    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(voice.config.sample_rate)
        wav_file.writeframes(audio_data)

    return output_path
