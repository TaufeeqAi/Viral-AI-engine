from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends # Added Depends
from agent.ws_api.services.voice_stt import stream_whisper_transcription
from agent.ws_api.services.voice_tts import stream_tts_audio
# FIX 1: Change import from verify_ws_token to get_current_user_ws
from agent.ws_api.services.token_auth import get_current_user_ws

# FIX 2: Ensure APIRouter is defined at the module level and named 'router'
router = APIRouter()

@router.websocket("/ws/chat/voice/{agent_id}")
async def voice_chat_ws(
    websocket: WebSocket,
    agent_id: str,
    # FIX 3: Use get_current_user_ws as a FastAPI dependency
    current_user_username: str = Depends(get_current_user_ws)
):
    await websocket.accept()
    # The 'user' variable now comes from the dependency, no need to call it again
    # user = await verify_ws_token(websocket) # REMOVED: This line is no longer needed

    print(f"Voice WebSocket connected for user: {current_user_username}, agent: {agent_id}")

    try:
        while True:
            audio_chunk = await websocket.receive_bytes()
            print(f"Received audio chunk from {current_user_username} for agent {agent_id}")

            transcript = await stream_whisper_transcription(audio_chunk)
            print(f"Transcribed: {transcript}")
            
            # TODO: Send transcript to agent backend, get response
            # For now, a simple echo
            agent_reply = f"You said: {transcript}"
            print(f"Agent reply: {agent_reply}")

            async for audio_response_chunk in stream_tts_audio(agent_reply):
                await websocket.send_bytes(audio_response_chunk)
            print("Sent TTS audio response.")

    except WebSocketDisconnect:
        print(f"🔌 Disconnected WebSocket: Voice chat for user {current_user_username}, agent {agent_id}")
    except Exception as e:
        print(f"❌ Error in voice_chat_ws for user {current_user_username}, agent {agent_id}: {e}")
        # Optionally close the websocket with an error code
        await websocket.close(code=1011) # Internal Error