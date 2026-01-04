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
        delta_status, guidance, failure = self._state_delta(context)
        focus_id = context.current_state.focused_element_id
        return VerificationResult(status=delta_status, failure_reason=failure, guidance_delta=guidance, updated_focus_id=focus_id)

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

    def _state_delta(self, context: VerificationContext) -> tuple[VerificationStatus, Optional[str], Optional[str]]:
        previous = context.previous_state
        current = context.current_state
        if not previous:
            return VerificationStatus.SUCCESS, None, None
        guidance: Optional[str] = None
        failure: Optional[str] = None
        if previous.screen_signature and current.screen_signature and previous.screen_signature == current.screen_signature:
            failure = "no screen change detected"
            guidance = "retry-different-target"
        prev_count = len(previous.elements)
        curr_count = len(current.elements)
        if prev_count and curr_count < max(prev_count * 0.3, 1):
            failure = "large element drop"
            guidance = "adjust-window"
        if previous.focused_element_id != current.focused_element_id and current.focused_element_id:
            guidance = "focus-shift"
        status = VerificationStatus.FAIL if failure else VerificationStatus.SUCCESS
        return status, guidance, failure
