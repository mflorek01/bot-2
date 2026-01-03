from __future__ import annotations

import time
from typing import List, Optional

from agent.perception.hashing import stable_element_id, screen_signature_hash
from agent.state.models import ElementState, Observation, TargetSource, UIElement, UIState, WindowInfo


class UICompressor:
    def __init__(self, element_cap: int = 250):
        self.element_cap = element_cap

    def compress(self, observation: Observation) -> UIState:
        # Placeholder transformation; would process UIA tree and OCR results.
        window = observation.window
        raw_elements: List[UIElement] = []
        if observation.ocr_results:
            for idx, text in enumerate(observation.ocr_results):
                element_id = stable_element_id(window, "text", text, None, None, f"ocr:{idx}")
                raw_elements.append(
                    UIElement(
                        element_id=element_id,
                        source=TargetSource.OCR,
                        role="text",
                        name=text,
                        value=None,
                        automation_id=None,
                        class_name=None,
                        bbox=None,
                        states=[],
                        parent_element_ids=[],
                        near_text=None,
                    )
                )
        elements = self._prioritize(raw_elements)
        focused = self._focused_element_id(elements)
        signature = self._compute_signature(observation)
        return UIState(
            window=window,
            timestamp=time.time(),
            elements=elements,
            focused_element_id=focused,
            salient_text=self._salient_text(elements),
            screen_signature=signature,
        )

    def _prioritize(self, elements: List[UIElement]) -> List[UIElement]:
        sorted_elements = sorted(
            elements,
            key=lambda e: (
                self._state_score(e.states),
                e.role or "",
                e.name or "",
                e.element_id,
            ),
        )
        return sorted_elements[: self.element_cap]

    def _state_score(self, states: List[ElementState]) -> int:
        score = 0
        if ElementState.FOCUSED in states:
            score -= 2
        if ElementState.ENABLED in states:
            score -= 1
        return score

    def _focused_element_id(self, elements: List[UIElement]) -> Optional[str]:
        for element in elements:
            if ElementState.FOCUSED in element.states:
                return element.element_id
        return None

    def _salient_text(self, elements: List[UIElement]) -> List[str]:
        texts: List[str] = []
        for element in elements:
            if element.name and element.role in {"button", "link", "menu_item", "text"}:
                texts.append(element.name)
            if len(texts) >= 15:
                break
        return texts

    def _compute_signature(self, observation: Observation) -> Optional[str]:
        if not observation.screenshot_path:
            return None
        try:
            with open(observation.screenshot_path, "rb") as f:
                return screen_signature_hash(f.read())
        except FileNotFoundError:
            return None
