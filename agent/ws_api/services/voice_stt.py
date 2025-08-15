import aiohttp

async def stream_whisper_transcription(audio_bytes: bytes) -> str:
    async with aiohttp.ClientSession() as session:
        async with session.post("http://localhost:4000/whisper", data=audio_bytes) as response:
            result = await response.json()
            return result["text"]
