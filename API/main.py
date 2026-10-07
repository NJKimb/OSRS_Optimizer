from fastapi import FastAPI
from app.routers.quests import router as quests_router
from app.routers.player import router as player_router
from app.routers.optimizer import router as optimizer_router
from fastapi.middleware.cors import CORSMiddleware

from config import get_settings

app = FastAPI(
    title="OSRS Account Optimizer API",
    description="API for optimizing questing, skill grinding, and unlock paths.",
    version="1.0.0",
)

settings = get_settings()

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

app.include_router(quests_router)
app.include_router(player_router)
app.include_router(optimizer_router)


@app.get("/")
def read_root():
    return {"message": "OSRS Account Optimizer API is running!"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}
