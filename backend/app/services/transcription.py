import asyncio
import logging
import os

import httpx

logger = logging.getLogger(__name__)

# Browsers record audio in a webm/opus container; AssemblyAI accepts many formats,
# but we normalise to 16 kHz mono WAV with ffmpeg first for a clean, reliable upload.
_WAV_MIME = "audio/wav"
_ASSEMBLYAI_BASE = "https://api.assemblyai.com/v2"
_POLL_SECONDS = 1.0
_MAX_POLLS = 40


async def _to_wav(audio: bytes, mime_type: str) -> tuple[bytes, str]:
    """Transcode an audio chunk to 16 kHz mono WAV with ffmpeg; fall back to the original."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "ffmpeg", "-hide_banner", "-loglevel", "error",
            "-i", "pipe:0", "-ac", "1", "-ar", "16000", "-f", "wav", "pipe:1",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await proc.communicate(input=audio)
        if proc.returncode == 0 and out:
            return out, _WAV_MIME
        logger.warning(
            "ffmpeg could not transcode a %s chunk (rc=%s): %s",
            mime_type, proc.returncode, err.decode("utf-8", "ignore")[:200],
        )
    except FileNotFoundError:
        logger.warning("ffmpeg is not installed; uploading the original audio")
    except Exception:
        logger.exception("Unexpected error while transcoding an audio chunk")
    return audio, mime_type


async def transcribe_audio_chunk(audio: bytes, mime_type: str = "audio/webm") -> str:
    """Transcribe one short audio clip with AssemblyAI (upload -> transcript -> poll)."""
    api_key = os.getenv("ASSEMBLYAI_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError("Transcription is not configured")
    data, _send_mime = await _to_wav(audio, mime_type)
    headers = {"authorization": api_key}
    async with httpx.AsyncClient(timeout=30) as client:
        # 1) Upload the audio bytes; AssemblyAI returns a private URL for them.
        upload = await client.post(f"{_ASSEMBLYAI_BASE}/upload", headers=headers, content=data)
        upload.raise_for_status()
        upload_url = upload.json()["upload_url"]

        # 2) Request a transcript of that upload.
        # Force the English model (no per-clip language auto-detection, so mixed
        # languages are all transcribed as English). AssemblyAI punctuates by default.
        created = await client.post(
            f"{_ASSEMBLYAI_BASE}/transcript",
            headers=headers,
            json={"audio_url": upload_url, "language_code": "en"},
        )
        created.raise_for_status()
        transcript_id = created.json()["id"]

        # 3) Poll until the short clip finishes (usually a few seconds).
        for _ in range(_MAX_POLLS):
            poll = await client.get(f"{_ASSEMBLYAI_BASE}/transcript/{transcript_id}", headers=headers)
            poll.raise_for_status()
            body = poll.json()
            status = body.get("status")
            if status == "completed":
                return (body.get("text") or "").strip()[:5000]
            if status == "error":
                raise RuntimeError(f"AssemblyAI error: {body.get('error', 'unknown')}")
            await asyncio.sleep(_POLL_SECONDS)
    return ""
