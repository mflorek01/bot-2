from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from agent.state.models import Observation, UIState, VerificationResult, VerificationStatus


@dataclass
class VerificationContext:
    previous_state: Optional[UIState]
    current_state: UIState
    observation: Observation
    stuck_threshold: int = 3


class Verifier:
    def __init__(self):
        self._recent_signatures: List[str] = []

    def verify(self, context: VerificationContext) -> VerificationResult:
        status, reason = self._detect_stuck(context.current_state)
        if status == VerificationStatus.STUCK:
            return VerificationResult(status=status, failure_reason=reason, guidance_delta="replan", updated_focus_id=None)
        focus_id = context.current_state.focused_element_id
        return VerificationResult(status=VerificationStatus.SUCCESS, failure_reason=None, guidance_delta=None, updated_focus_id=focus_id)

    def _detect_stuck(self, ui_state: UIState) -> tuple[VerificationStatus, Optional[str]]:
        signature = ui_state.screen_signature
        if not signature:
            return VerificationStatus.SUCCESS, None
        self._recent_signatures.append(signature)
        if len(self._recent_signatures) > 3:
            self._recent_signatures.pop(0)
        if len(self._recent_signatures) == 3 and len(set(self._recent_signatures)) == 1:
            return VerificationStatus.STUCK, "screen signature unchanged"
        return VerificationStatus.SUCCESS, None
