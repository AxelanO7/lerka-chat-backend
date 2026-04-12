from fastapi import APIRouter, Depends
from typing import Dict
from app.services.budget_service import TokenBudgetService
from app.api.deps import get_budget_service

router = APIRouter()

@router.get("", response_model=Dict[str, int])
async def get_budgets(
    budget_service: TokenBudgetService = Depends(get_budget_service)
):
    """Get current token budget for all models."""
    return budget_service.get_all_budgets()

@router.post("/reset")
async def reset_budgets(
    budget_service: TokenBudgetService = Depends(get_budget_service)
):
    """Reset token budgets back to their defaults."""
    budget_service.reset_budgets()
    return {"message": "Budgets reset successfully", "budgets": budget_service.get_all_budgets()}
