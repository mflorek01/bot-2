from __future__ import annotations

from typing import List, Optional

from agent.state.models import GroundedTarget, IntentAction, IntentTarget, UIElement, UIState


class Grounder:
    def ground(self, intent: IntentAction, ui_state: UIState) -> GroundedTarget:
        candidates = self._match_candidates(intent.target, ui_state) if intent.target else []
        element = candidates[0] if candidates else None
        confidence = 1.0 if element else 0.0
        return GroundedTarget(element=element, confidence=confidence, alternatives=candidates[1:])

    def _match_candidates(self, target: IntentTarget, ui_state: UIState) -> List[UIElement]:
        results: List[UIElement] = []
        for element in ui_state.elements:
            if target.element_id and element.element_id != target.element_id:
                continue
            if target.role and element.role != target.role:
                continue
            if target.name_equals and (element.name or "").lower() != target.name_equals.lower():
                continue
            if target.name_contains and target.name_contains.lower() not in (element.name or "").lower():
                continue
            if target.automation_id and element.automation_id != target.automation_id:
                continue
            results.append(element)
        return sorted(results, key=lambda e: e.element_id)
