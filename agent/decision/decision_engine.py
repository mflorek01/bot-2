from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from agent.decision.llm_interface import LLMInterface
from agent.selector.selector import Selector
from agent.skills.skill_library import SkillLibrary
from agent.state.models import ElementState, IntentAction, UIState, WorkingMemory


@dataclass
class DecisionOutcome:
    intent: IntentAction
    rationale: str
    used_llm: bool


class DecisionEngine:
    def __init__(self, skills: SkillLibrary, selector: Selector, llm: Optional[LLMInterface] = None):
        self.skills = skills
        self.selector = selector
        self.llm = llm or LLMInterface()

    def decide(self, ui_state: UIState, memory: WorkingMemory) -> DecisionOutcome:
        procedure_intent = self._run_procedure(ui_state, memory)
        if procedure_intent:
            safe_intent = self.selector.gate(procedure_intent, memory)
            return DecisionOutcome(intent=safe_intent, rationale="procedure", used_llm=False)

        micropolicy_intent = self._micropolicy(ui_state)
        if micropolicy_intent:
            safe_intent = self.selector.gate(micropolicy_intent, memory)
            return DecisionOutcome(intent=safe_intent, rationale="micropolicy", used_llm=False)

        proposed = self._llm_propose(ui_state, memory)
        safe = self.selector.gate(proposed, memory)
        return DecisionOutcome(intent=safe, rationale="llm", used_llm=True)

    def _run_procedure(self, ui_state: UIState, memory: WorkingMemory) -> Optional[IntentAction]:
        return self.skills.match_procedure(ui_state, memory)

    def _micropolicy(self, ui_state: UIState) -> Optional[IntentAction]:
        for element in ui_state.elements:
            if element.name and element.name.lower() in {"ok", "next"} and ElementState.DISABLED not in element.states:
                # role check optional; deterministic micro policy
                from agent.state.models import ActionVerb, IntentTarget

                return IntentAction(
                    verb=ActionVerb.CLICK,
                    target=IntentTarget(element_id=element.element_id, name_equals=element.name, role=element.role),
                )
        return None

    def _llm_propose(self, ui_state: UIState, memory: WorkingMemory) -> IntentAction:
        candidates: List[IntentAction] = []
        proposals = self.llm.propose(ui_state, memory.goal, candidate_actions=candidates)
        ranked = self.llm.rank(ui_state, proposals)
        if ranked:
            return ranked[0]
        # Fallback no-op
        from agent.state.models import ActionVerb, IntentAction as Intent

        return Intent(verb=ActionVerb.WAIT, wait_seconds=1.0)
