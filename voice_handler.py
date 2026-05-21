"""Voice message handler using OpenAI Whisper."""

import os
import subprocess
import tempfile
from typing import Optional

WHISPER_MODEL = None


def load_whisper_model():
    """Load Whisper model (lazy loading)."""
    global WHISPER_MODEL
    if WHISPER_MODEL is None:
        import whisper
        WHISPER_MODEL = whisper.load_model("small")
    return WHISPER_MODEL


async def download_voice_file(bot, file_id: str, output_path: str) -> str:
    """Download voice file from Telegram."""
    file = await bot.get_file(file_id)
    await bot.download_file(file.file_path, destination=output_path)
    return output_path


def convert_ogg_to_wav(ogg_path: str, wav_path: str) -> bool:
    """Convert OGG to WAV using ffmpeg."""
    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", ogg_path, "-ar", "16000", "-ac", "1", wav_path],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        return False
    except FileNotFoundError:
        return False


def transcribe_audio(wav_path: str) -> Optional[str]:
    """Transcribe audio file to text using Whisper."""
    try:
        model = load_whisper_model()
        result = model.transcribe(wav_path, language="ru")
        return result["text"].strip()
    except Exception:
        return None


async def process_voice_message(bot, file_id: str) -> Optional[str]:
    """
    Process voice message: download, convert, transcribe.

    Args:
        bot: Telegram bot instance
        file_id: Telegram file ID

    Returns:
        Transcribed text or None if failed
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        ogg_path = os.path.join(tmpdir, "voice.ogg")
        wav_path = os.path.join(tmpdir, "voice.wav")

        await download_voice_file(bot, file_id, ogg_path)

        if not convert_ogg_to_wav(ogg_path, wav_path):
            return None

        text = transcribe_audio(wav_path)
        return text
