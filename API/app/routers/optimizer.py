from fastapi import APIRouter
from app.models.plan import OptimizationRequest, OptimizationResponse
from app.services.optimizer.engine import generate_optimization_plan

router = APIRouter(prefix="/api/optimize", tags=["Optimization"])

@router.post("/plan", response_model=OptimizationResponse)
async def optimize_plan(request: OptimizationRequest):
    return await generate_optimization_plan(request)
