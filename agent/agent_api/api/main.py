# api/main.py
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .lifespan import lifespan
from .routes.agents import router as agents_router
from .routes.chat import router as chat_router
from .routes.tools import router as tools_router
from .routes.webhooks import router as webhooks_router


# --------- Logging Setup ---------
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --------- FastAPI App ---------
app = FastAPI(lifespan=lifespan, debug=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --------- Route Registration ---------
app.include_router(agents_router, prefix="/agents", tags=["agents"])
app.include_router(chat_router, prefix="/agents", tags=["chat"])
app.include_router(webhooks_router, tags=["webhooks"])
app.include_router(tools_router, prefix="/tools", tags=["tools"])


@app.get("/")
async def read_root():
    return {"message": "Welcome to the Multi-Agent Bot API!"}