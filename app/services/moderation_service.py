import re
from typing import Tuple

class ModerationService:
    def __init__(self):
        # Basic keyword blocklist for Phase 1
        self.blocklist = [
            r"\bjailbreak\b",
            r"\bignore previous instructions\b",
            r"\bhow to hack\b",
            r"\bmake bomb\b",
            r"\bexploit vulnerability\b"
        ]
        # Compiled patterns
        self.blocklist_patterns = [re.compile(pattern, re.IGNORECASE) for pattern in self.blocklist]
        
        # PII patterns: Email and Phone numbers
        self.email_pattern = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+")
        # Simple phone pattern: matching variations of (+123/08...) format
        self.phone_pattern = re.compile(r"(\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4,6}|\b08\d{8,11}\b")

    def moderate_prompt(self, prompt: str) -> Tuple[bool, bool, str]:
        """
        Returns:
            (is_blocked: bool, do_not_cache: bool, reason: str)
        """
        # 1. Check keyword blocklist
        for pattern in self.blocklist_patterns:
            if pattern.search(prompt):
                return True, True, "Prompt contains prohibited content/keywords."
        
        # 2. Check for PII (do not block, just flag not to cache)
        do_not_cache = False
        reason = ""
        if self.email_pattern.search(prompt) or self.phone_pattern.search(prompt):
            do_not_cache = True
            reason = "PII detected (email or phone number)"
            
        return False, do_not_cache, reason

moderation_service = ModerationService()
