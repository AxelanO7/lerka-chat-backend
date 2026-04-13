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
            "meta-llama/llama-3.1-8b-instruct": settings.BUDGET_OR_LLAMA_3_1_8B, # Ini 
            "anthropic/claude-3-haiku": settings.BUDGET_OR_CLAUDE_3_HAIKU, # Ini advanced
            "openai/gpt-4o-mini": settings.BUDGET_OR_GPT_4O_MINI,
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
        """Deduct token usage from the model's budget. Ensure it doesn't go below 0."""
        if model in self.budgets:
            self.budgets[model] = max(0, self.budgets[model] - amount)
            logger.info(f"Deducted {amount} tokens from {model}. Remaining budget: {self.budgets[model]}")
        else:
            # Optionally add it to the state tracking if unrecognized
            self.budgets[model] = max(0, settings.BUDGET_GEMMA4 - amount)
            logger.info(f"Deducted {amount} tokens from new model {model}. Remaining: {self.budgets[model]}")

    def get_all_budgets(self) -> Dict[str, int]:
        """Return the current budget state for all models."""
        return self.budgets
