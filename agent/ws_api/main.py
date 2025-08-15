from fastapi import FastAPI
from agent.ws_api.routers import chat_stream, notifications
from fastapi.middleware.cors import CORSMiddleware
from agent.ws_api.routers import voice_chat

app = FastAPI(title="Cyrene WebSocket API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat_stream.router)
app.include_router(notifications.router)

app.include_router(voice_chat.router)
