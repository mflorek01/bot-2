from __future__ import annotations

import time
from typing import List, Optional

from agent.perception.hashing import screen_signature_hash, stable_element_id
from agent.state.models import ElementState, Observation, TargetSource, UIElement, UIState, WindowInfo


class UICompressor:
    def __init__(self, element_cap: int = 250):
        self.element_cap = element_cap

    def compress(self, observation: Observation) -> UIState:
        window = observation.window
        elements: List[UIElement] = []
        if isinstance(observation.raw_tree, list):
            elements.extend(self._from_uia_nodes(window, observation.raw_tree))
        if observation.ocr_results:
            elements.extend(self._from_ocr(window, observation.ocr_results))
        elements = self._prioritize(elements)
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

    def _from_ocr(self, window: WindowInfo, ocr_results: List[str]) -> List[UIElement]:
        ocr_elements: List[UIElement] = []
        for idx, text in enumerate(ocr_results):
            element_id = stable_element_id(window, "text", text, None, None, f"ocr:{idx}")
            ocr_elements.append(
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
                    runtime_properties={},
                )
            )
        return ocr_elements

    def _from_uia_nodes(self, window: WindowInfo, nodes: List[dict]) -> List[UIElement]:
        elements: List[UIElement] = []
        for node in nodes:
            role = (node.get("control_type") or "").lower() or None
            name = node.get("name")
            automation_id = node.get("automation_id")
            bbox = node.get("bbox")
            parent_chain = node.get("parent_chain")
            element_id = stable_element_id(window, role, name, automation_id, bbox, parent_chain)
            states = self._states_from_node(node)
            el = UIElement(
                element_id=element_id,
                source=TargetSource.UIA,
                role=role,
                name=name,
                value=None,
                automation_id=automation_id,
                class_name=node.get("class_name"),
                bbox=bbox,
                states=states,
                parent_element_ids=parent_chain.split("/") if parent_chain else [],
                near_text=None,
                runtime_properties=node.get("legacy_properties", {}),
            )
            if self._is_interactive(el) or ElementState.FOCUSED in states:
                elements.append(el)
        return elements

    def _is_interactive(self, element: UIElement) -> bool:
        interactive_roles = {
            "button",
            "edit",
            "checkbox",
            "radiobutton",
            "hyperlink",
            "listitem",
            "tabitem",
            "menuitem",
            "combobox",
            "slider",
            "spinner",
        }
        return (element.role in interactive_roles) or (element.automation_id is not None)

    def _states_from_node(self, node: dict) -> List[ElementState]:
        states: List[ElementState] = []
        if node.get("is_enabled"):
            states.append(ElementState.ENABLED)
        else:
            states.append(ElementState.DISABLED)
        if node.get("has_keyboard_focus"):
            states.append(ElementState.FOCUSED)
        if node.get("is_offscreen"):
            states.append(ElementState.OFFSCREEN)
        return states

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
