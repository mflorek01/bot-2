from __future__ import annotations

import logging
from typing import Iterable, Optional, Set

from agent.state.models import ActionVerb, IntentAction, SafetyLevel, WorkingMemory


class Selector:
    def __init__(self, allow_verbs: Optional[Iterable[ActionVerb]] = None, deny_text: Optional[Iterable[str]] = None, safety_level: SafetyLevel = SafetyLevel.NORMAL, max_actions: int = 100):
        self.allow_verbs: Optional[Set[ActionVerb]] = set(allow_verbs) if allow_verbs else None
        self.deny_text = {t.lower() for t in deny_text} if deny_text else {"purchase", "checkout", "delete account"}
        self.safety_level = safety_level
        self.max_actions = max_actions
        self._action_counter = 0
        self.logger = logging.getLogger(__name__)

    def gate(self, intent: IntentAction, memory: WorkingMemory) -> IntentAction:
        self._action_counter += 1
        if self._action_counter > self.max_actions:
            raise ValueError("Rate limit exceeded for actions")
        if self.allow_verbs and intent.verb not in self.allow_verbs:
            raise ValueError(f"Action {intent.verb.value} not in allowlist")
        if self._is_forbidden(intent):
            raise ValueError("Blocked dangerous action")
        if self._is_high_safety(memory):
            if intent.verb in {ActionVerb.OPEN_URL, ActionVerb.RIGHT_CLICK}:
                raise ValueError("Action forbidden under high safety policy")
            if intent.verb == ActionVerb.SCROLL and not self._is_scroll_allowed(intent):
                raise ValueError("Scroll forbidden under high safety policy")
        self.logger.debug("Selector passed intent %s (safety=%s)", intent.verb, self.safety_level.value)
        return intent

    def _is_forbidden(self, intent: IntentAction) -> bool:
        target_texts = [
            intent.target.name_contains if intent.target else None,
            intent.target.name_equals if intent.target else None,
        ]
        for text in target_texts:
            if not text:
                continue
            lowered = text.lower()
            if any(term in lowered for term in self.deny_text):
                return True
        return False

    def _is_high_safety(self, memory: WorkingMemory) -> bool:
        return self.safety_level == SafetyLevel.HIGH or memory.risk_mode == "high"

    def _is_scroll_allowed(self, intent: IntentAction) -> bool:
        if intent.target and intent.target.name_contains:
            txt = intent.target.name_contains.lower()
            if "scroll" in txt or "list" in txt:
                return True
        if intent.amount and abs(intent.amount) <= 1200:
            return True
        return False
