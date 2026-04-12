import logging
from typing import Dict
from app.core.config import settings

logger = logging.getLogger(__name__)

class TokenBudgetService:
    def __init__(self):
        self.default_budgets: Dict[str, int] = {
            "llama3.2:3b": settings.BUDGET_LLAMA_3_2,
            "llama2:latest": settings.BUDGET_LLAMA_2,
            "gemma4:latest": settings.BUDGET_GEMMA4,
        }
        self.budgets: Dict[str, int] = {}
        self.reset_budgets()

    def reset_budgets(self) -> None:
        """Reset all budgets to their default configuration."""
        self.budgets = self.default_budgets.copy()
        logger.info("Token budgets reset to defaults.")

    def get_budget(self, model: str) -> int:
        """Get remaining budget for a specific model."""
        return self.budgets.get(model, settings.BUDGET_GEMMA4) # Fallback if model not defined in defaults

    def deduct_budget(self, model: str, amount: int) -> None:
        """Deduct token usage from the model's budget."""
        if model in self.budgets:
            self.budgets[model] -= amount
            logger.info(f"Deducted {amount} tokens from {model}. Remaining budget: {self.budgets[model]}")
        else:
            # Optionally add it to the state tracking if unrecognized
            self.budgets[model] = settings.BUDGET_GEMMA4 - amount
            logger.info(f"Deducted {amount} tokens from new model {model}. Remaining: {self.budgets[model]}")

    def get_all_budgets(self) -> Dict[str, int]:
        """Return the current budget state for all models."""
        return self.budgets
