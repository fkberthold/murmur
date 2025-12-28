from pathlib import Path
from datetime import datetime
import subprocess
import shutil
import os


def _find_piper_bin() -> tuple[str | None, str | None]:
    """Find piper binary, return (path, lib_dir) or (None, None)."""
    # Check for bundled piper first
    pkg_root = Path(__file__).parent.parent.parent.parent
    bundled = pkg_root / "bin" / "piper" / "piper"
    if bundled.exists():
        return str(bundled), str(bundled.parent)

    # Check system PATH
    system_piper = shutil.which("piper")
    if system_piper:
        return system_piper, None

    return None, None


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
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = output_dir / f"brief_{timestamp}.wav"

    piper_bin, lib_dir = _find_piper_bin()
    if piper_bin:
        cmd = [
            piper_bin,
            "--model", str(model_path),
            "--output_file", str(output_path),
            "--sentence_silence", str(sentence_silence),
        ]

        # Set up environment with library path if needed
        env = os.environ.copy()
        if lib_dir:
            ld_path = env.get("LD_LIBRARY_PATH", "")
            env["LD_LIBRARY_PATH"] = f"{lib_dir}:{ld_path}" if ld_path else lib_dir

        result = subprocess.run(
            cmd,
            input=text,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            raise RuntimeError(f"Piper CLI failed: {result.stderr}")
        return output_path

    # Fall back to Python library
    try:
        from piper import PiperVoice
        import wave
    except ImportError:
        raise ImportError(
            "piper-tts not installed and piper CLI not found. "
            "Run: pip install piper-tts"
        )

    # Load voice model
    voice = PiperVoice.load(str(model_path))

    # Generate audio - synthesize_stream_raw yields audio chunks
    audio_chunks = []
    for audio_bytes in voice.synthesize_stream_raw(text, sentence_silence=sentence_silence):
        audio_chunks.append(audio_bytes)
    audio_data = b"".join(audio_chunks)

    # Save to WAV file
    with wave.open(str(output_path), "wb") as wav_file:
        wav_file.setnchannels(1)
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(voice.config.sample_rate)
        wav_file.writeframes(audio_data)

    return output_path
