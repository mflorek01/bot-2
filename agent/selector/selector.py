from __future__ import annotations

from agent.state.models import IntentAction, WorkingMemory


class Selector:
    def gate(self, intent: IntentAction, memory: WorkingMemory) -> IntentAction:
        if self._is_forbidden(intent):
            raise ValueError("Blocked dangerous action")
        return intent

    def _is_forbidden(self, intent: IntentAction) -> bool:
        if intent.target and intent.target.name_contains:
            text = intent.target.name_contains.lower()
            if "purchase" in text or "checkout" in text:
                return True
        return False
