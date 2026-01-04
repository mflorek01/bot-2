from __future__ import annotations

import logging
from difflib import SequenceMatcher
from dataclasses import replace
from typing import List, Optional

from agent.state.models import GroundedTarget, IntentAction, IntentTarget, UIElement, UIState


class Grounder:
    def __init__(self, logger: Optional[logging.Logger] = None):
        self.logger = logger or logging.getLogger(__name__)

    def ground(self, intent: IntentAction, ui_state: UIState) -> GroundedTarget:
        candidates = self._match_candidates(intent.target, ui_state) if intent.target else []
        element = candidates[0] if candidates else None
        confidence = candidates[0].salience if candidates else 0.0
        return GroundedTarget(element=element, confidence=float(confidence), alternatives=candidates[1:])

    def _match_candidates(self, target: IntentTarget, ui_state: UIState) -> List[UIElement]:
        scored: List[UIElement] = []
        debug_rows: List[str] = []
        for element in ui_state.elements:
            score, reason = self._score_element(target, element)
            if score <= 0:
                continue
            element_salience = element.salience + score
            debug_rows.append(f"{element.element_id} -> {element_salience:.2f} ({reason})")
            scored.append(replace(element, salience=element_salience))
        scored_sorted = sorted(scored, key=lambda e: (-(e.salience or 0.0), e.element_id))
        if debug_rows:
            self.logger.debug("Grounding candidates:\n%s", "\n".join(debug_rows))
        return scored_sorted

    def _score_element(self, target: IntentTarget, element: UIElement) -> tuple[float, str]:
        score = 0.0
        reasons: List[str] = []
        if target.element_id:
            if target.element_id == element.element_id:
                reasons.append("element_id")
                score += 5.0
            else:
                return 0.0, "different element_id"
        if target.automation_id:
            if target.automation_id == element.automation_id:
                reasons.append("automation_id")
                score += 3.5
            else:
                return 0.0, "automation mismatch"
        if target.role and element.role:
            if target.role.lower() == element.role.lower():
                reasons.append("role")
                score += 1.0
            else:
                score -= 0.5
        name = (element.name or "").lower()
        if target.name_equals:
            if name == target.name_equals.lower():
                reasons.append("name_exact")
                score += 3.0
            else:
                return 0.0, "name mismatch"
        if target.name_contains:
            contains = target.name_contains.lower() in name
            fuzzy = SequenceMatcher(None, target.name_contains.lower(), name).ratio()
            if contains or fuzzy > 0.55:
                reasons.append("name_contains")
                score += 2.0 * fuzzy
            else:
                return 0.0, "name missing"
        if target.near_text and element.near_text:
            if target.near_text.lower() in element.near_text.lower():
                reasons.append("near_text")
                score += 1.2
        if element.bbox and isinstance(element.bbox, (list, tuple)):
            width = max(element.bbox[2] - element.bbox[0], 1)
            height = max(element.bbox[3] - element.bbox[1], 1)
            area_score = min(width * height / 200000.0, 1.0)
            score += 0.5 * (1 - area_score)
            reasons.append("geometry")
        if element.salience:
            score += min(element.salience, 3.0) * 0.2
        return score, ",".join(reasons) if reasons else "heuristic"
