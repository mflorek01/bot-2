from __future__ import annotations

import logging
import time
from typing import List, Optional, Sequence

from agent.state.models import ActionVerb, IntentAction, IntentTarget, UIState


class LLMInterface:
    """
    Thin wrapper used only for proposing or verifying actions.
    The controller remains deterministic; this module is a stochastic lens.
    """

    def __init__(self, client: Optional[callable] = None, max_retries: int = 2, backoff_seconds: float = 0.5, validator: Optional[callable] = None):
        self.client = client
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.validator = validator
        self.logger = logging.getLogger(__name__)

    def propose(self, ui_state: UIState, goal: Optional[str], candidate_actions: Optional[Sequence[IntentAction]] = None) -> List[IntentAction]:
        if not self.client:
            return self._deterministic_fallback(ui_state)
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                response = self.client(ui_state=ui_state, goal=goal, candidate_actions=candidate_actions)
                return self._validate_actions(response)
            except Exception as exc:
                last_error = exc
                self.logger.debug("LLM propose attempt %s failed: %s", attempt + 1, exc, exc_info=exc)
                time.sleep(self.backoff_seconds * (2 ** attempt))
        self.logger.warning("LLM propose failed after retries: %s", last_error)
        return []

    def rank(self, ui_state: UIState, candidates: Sequence[IntentAction]) -> List[IntentAction]:
        validated = self._validate_actions(candidates)
        if not validated:
            return validated
        if self.validator:
            validated = self.validator(validated, ui_state)
        return list(validated)

    def _validate_actions(self, actions: Optional[Sequence[IntentAction]]) -> List[IntentAction]:
        valid: List[IntentAction] = []
        if not actions:
            return valid
        for action in actions:
            parsed = self._coerce_action(action)
            if parsed:
                valid.append(parsed)
        if not valid:
            fallback = IntentAction(verb=ActionVerb.WAIT, wait_seconds=1.0)
            return [fallback]
        return valid

    def _coerce_action(self, action: any) -> Optional[IntentAction]:
        if isinstance(action, IntentAction):
            return action
        if isinstance(action, dict):
            verb_raw = action.get("verb")
            if not verb_raw:
                return None
            try:
                verb = ActionVerb(verb_raw)
            except Exception:
                return None
            target = action.get("target") or {}
            intent_target = None
            if isinstance(target, dict):
                intent_target = IntentTarget(
                    element_id=target.get("element_id"),
                    automation_id=target.get("automation_id"),
                    name_contains=target.get("name_contains"),
                    name_equals=target.get("name_equals"),
                    role=target.get("role"),
                )
            return IntentAction(
                verb=verb,
                target=intent_target,
                text=action.get("text"),
                key=action.get("key"),
                amount=action.get("amount"),
                wait_seconds=action.get("wait_seconds"),
            )
        return None

    def _deterministic_fallback(self, ui_state: UIState) -> List[IntentAction]:
        # Heuristic fallback when no LLM client is wired: click first focused or salient element.
        sorted_elements = sorted(ui_state.elements, key=lambda e: (-(e.salience or 0.0), e.element_id))
        for element in sorted_elements:
            if element.role and element.role.lower() in {"button", "hyperlink", "menuitem"}:
                return [
                    IntentAction(
                        verb=ActionVerb.CLICK,
                        target=getattr(__import__("agent.state.models", fromlist=["IntentTarget"]), "IntentTarget")(element_id=element.element_id),
                    )
                ]
        return []
