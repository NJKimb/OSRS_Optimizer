from fastapi import FastAPI, Query
from app.core.skills import AccountType
from app.models.player import PlayerProfile
from app.services.hiscores import fetch_player_profile
from app.models.plan import OptimizationRequest, OptimizationResponse
from app.services.optimizer.engine import generate_optimization_plan
from app.routers.quests import router as quests_router


app = FastAPI(
    title="OSRS Account Optimizer API",
    description="API for optimizing questing, skill grinding, and unlock paths.",
    version="1.0.0"
)

app.include_router(quests_router)

@app.get("/")
def read_root():
    return {"message": "OSRS Account Optimizer API is running!"}

@app.get("/api/health")
def health_check():
    return {"status": "healthy"}

@app.get("/api/player/{username}", response_model=PlayerProfile)
async def get_player_profile(username: str, account_type: AccountType = Query(default=AccountType.MAIN)):
    return await fetch_player_profile(username, account_type)

@app.post("/api/optimize/plan", response_model=OptimizationResponse)
async def optimize_plan(request: OptimizationRequest):
    return await generate_optimization_plan(request)

