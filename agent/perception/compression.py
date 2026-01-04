from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Sequence

from agent.perception.hashing import frame_signature, stable_element_id, screen_signature_hash
from agent.state.models import ElementState, Observation, OCRSpan, TargetSource, UIElement, UIState, WindowInfo


class UICompressor:
    def __init__(self, element_cap: int = 250):
        self.element_cap = element_cap

    def compress(self, observation: Observation) -> UIState:
        window = observation.window
        raw_elements: List[UIElement] = []
        if observation.raw_tree:
            raw_elements.extend(self._elements_from_tree(observation.raw_tree, window, []))
        if observation.ocr_results:
            raw_elements.extend(self._elements_from_ocr(window, observation.ocr_results))
        elements = self._prioritize(raw_elements)
        focused = self._focused_element_id(elements)
        signature = self._compute_signature(observation, elements)
        return UIState(
            window=window,
            timestamp=time.time(),
            elements=elements,
            focused_element_id=focused,
            salient_text=self._salient_text(elements),
            screen_signature=signature,
            derived_from="uia+ocr" if observation.raw_tree else "ocr",
        )

    def _elements_from_tree(self, node: Dict[str, Any], window: WindowInfo, parents: Sequence[str]) -> List[UIElement]:
        elements: List[UIElement] = []
        element_id = stable_element_id(window, node.get("role"), node.get("name"), node.get("automation_id"), node.get("bbox"), node.get("parent_chain"))
        states = self._coerce_states(node.get("states", []))
        element = UIElement(
            element_id=element_id,
            source=TargetSource.UIA,
            role=node.get("role"),
            name=node.get("name"),
            value=node.get("value"),
            automation_id=node.get("automation_id"),
            class_name=node.get("class_name"),
            bbox=node.get("bbox"),
            states=states,
            parent_element_ids=list(parents),
            near_text=node.get("near_text"),
            salience=self._salience_score(node, states),
            backend_ref=node.get("backend_ref"),
        )
        elements.append(element)
        for child in node.get("children", []):
            elements.extend(self._elements_from_tree(child, window, [*parents, element_id]))
        return elements

    def _elements_from_ocr(self, window: WindowInfo, spans: Sequence[OCRSpan]) -> List[UIElement]:
        elements: List[UIElement] = []
        for idx, span in enumerate(spans):
            element_id = stable_element_id(window, "text", span.text, None, span.bbox, f"ocr:{idx}")
            bbox = span.bbox
            if not bbox and span.text:
                # Synthetic bbox to allow mouse fallback (approximate size)
                bbox = (0, idx * 10, max(40, len(span.text) * 6), idx * 10 + 14)
            elements.append(
                UIElement(
                    element_id=element_id,
                    source=TargetSource.OCR,
                    role="text",
                    name=span.text,
                    value=None,
                    automation_id=None,
                    class_name=None,
                    bbox=bbox,
                    states=[ElementState.ENABLED],
                    parent_element_ids=[],
                    near_text=None,
                    salience=0.2,
                )
            )
        return elements

    def _coerce_states(self, states: Sequence[Any]) -> List[ElementState]:
        normalized: List[ElementState] = []
        for state in states:
            if isinstance(state, ElementState):
                normalized.append(state)
            else:
                try:
                    normalized.append(ElementState(str(state)))
                except Exception:
                    continue
        return normalized

    def _prioritize(self, elements: List[UIElement]) -> List[UIElement]:
        sorted_elements = sorted(
            elements,
            key=lambda e: (
                -float(e.salience or 0.0),
                -(1 if ElementState.FOCUSED in e.states else 0),
                e.role or "",
                e.name or "",
                e.element_id,
            ),
            reverse=False,
        )
        return sorted_elements[: self.element_cap]

    def _focused_element_id(self, elements: List[UIElement]) -> Optional[str]:
        for element in elements:
            if ElementState.FOCUSED in element.states:
                return element.element_id
        return None

    def _salient_text(self, elements: List[UIElement]) -> List[str]:
        texts: List[str] = []
        for element in sorted(elements, key=lambda e: -(e.salience or 0.0)):
            if element.name and element.role and element.role.lower() in {"button", "link", "menu_item", "text", "menuitem"}:
                texts.append(element.name)
            if len(texts) >= 15:
                break
        return texts

    def _compute_signature(self, observation: Observation, elements: Sequence[UIElement]) -> Optional[str]:
        parts: List[str] = []
        if observation.screenshot_path:
            try:
                with open(observation.screenshot_path, "rb") as f:
                    parts.append(screen_signature_hash(f.read()))
            except FileNotFoundError:
                pass
        if elements:
            parts.append(frame_signature(elements, observation.window))
        if not parts:
            return None
        return screen_signature_hash("|".join(parts).encode("utf-8"))

    def _salience_score(self, node: Dict[str, Any], states: Sequence[ElementState]) -> float:
        role = (node.get("role") or "").lower()
        name = node.get("name") or ""
        score = 0.0
        if role in {"button", "hyperlink", "link", "menuitem", "listitem"}:
            score += 2.5
        if ElementState.FOCUSED in states:
            score += 3.0
        if ElementState.ENABLED in states:
            score += 0.5
        if ElementState.OFFSCREEN in states:
            score -= 1.0
        score += min(len(name) / 20.0, 1.0)
        if node.get("automation_id"):
            score += 0.5
        return score
