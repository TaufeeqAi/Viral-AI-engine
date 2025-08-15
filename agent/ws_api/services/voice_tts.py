import aiohttp
import os

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY")

async def stream_tts_audio(text: str):
    headers = {
        "xi-api-key": ELEVENLABS_API_KEY,
        "Content-Type": "application/json"
    }
    payload = {
        "text": text,
        "voice_id": "Rachel",  # or your default
        "model_id": "eleven_monolingual_v1",
        "stream": True
    }

    async with aiohttp.ClientSession() as session:
        async with session.post(
            "https://api.elevenlabs.io/v1/text-to-speech/Rachel/stream",
            headers=headers, json=payload
        ) as resp:
            async for chunk in resp.content.iter_chunked(4096):
                yield chunk
