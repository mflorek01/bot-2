from __future__ import annotations

from typing import List, Optional, Sequence

from agent.state.models import IntentAction, UIState


class LLMInterface:
    """
    Thin wrapper used only for proposing or verifying actions.
    The controller remains deterministic; this module is a stochastic lens.
    """

    def propose(self, ui_state: UIState, goal: Optional[str], candidate_actions: Optional[Sequence[IntentAction]] = None) -> List[IntentAction]:
        _ = ui_state, goal, candidate_actions
        return []

    def rank(self, ui_state: UIState, candidates: Sequence[IntentAction]) -> List[IntentAction]:
        _ = ui_state
        return list(candidates)
