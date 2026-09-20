from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from app.routers.quests import router as quests_router
from app.routers.player import router as player_router
from app.routers.optimizer import router as optimizer_router


app = FastAPI(
    title="OSRS Account Optimizer API",
    description="API for optimizing questing, skill grinding, and unlock paths.",
    version="1.0.0"
)

# Enable CORS for frontend clients running from any host or port
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(quests_router)
app.include_router(player_router)
app.include_router(optimizer_router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy"}


# Mount static client frontend if directory exists
client_path = Path(__file__).resolve().parent.parent / "client"
if client_path.exists():
    app.mount("/", StaticFiles(directory=str(client_path), html=True), name="client")
else:
    @app.get("/")
    def read_root():
        return {"message": "OSRS Account Optimizer API is running!"}