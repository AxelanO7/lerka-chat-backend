import pytest
from app.services.budget_service import TokenBudgetService
from app.core.config import settings

def test_budget_service_init():
    service = TokenBudgetService()
    budgets = service.get_all_budgets()
    assert budgets["llama3.2:3b"] == settings.BUDGET_LLAMA_3_2
    assert budgets["llama2:latest"] == settings.BUDGET_LLAMA_2
    assert budgets["gemma4:latest"] == settings.BUDGET_GEMMA4

def test_reset_budgets():
    service = TokenBudgetService()
    model = "llama3.2:3b"
    service.deduct_budget(model, 100)
    assert service.get_budget(model) == settings.BUDGET_LLAMA_3_2 - 100
    
    service.reset_budgets()
    assert service.get_budget(model) == settings.BUDGET_LLAMA_3_2

def test_get_budget_fallback():
    service = TokenBudgetService()
    # Unrecognized model should return gemma4 default
    assert service.get_budget("unknown-model") == settings.BUDGET_GEMMA4

def test_deduct_budget_existing():
    service = TokenBudgetService()
    model = "llama2:latest"
    initial = service.get_budget(model)
    service.deduct_budget(model, 500)
    assert service.get_budget(model) == initial - 500

def test_deduct_budget_new_model():
    service = TokenBudgetService()
    model = "brand-new-model"
    # Logic says it uses gemma4 default as baseline for new models
    service.deduct_budget(model, 200)
    assert service.get_budget(model) == settings.BUDGET_GEMMA4 - 200
