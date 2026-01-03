from __future__ import annotations

import time
from typing import Optional

from agent.state.models import ExecutionMethod, ExecutionResult, ExecutionStatus, GroundedTarget, IntentAction


class UIAExecutor:
    def __init__(self, app_loader: Optional[callable] = None):
        self.app_loader = app_loader

    def execute(self, intent: IntentAction, target: GroundedTarget) -> ExecutionResult:
        start = time.time()
        try:
            self._invoke(intent, target)
            return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.UIA, duration=time.time() - start)
        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.FAIL,
                method=ExecutionMethod.UIA,
                duration=time.time() - start,
                error=str(exc),
            )

    def _invoke(self, intent: IntentAction, target: GroundedTarget) -> None:
        element = target.element
        if not element:
            raise ValueError("Cannot invoke UIA action without grounded element")
        # Placeholder: actual pywinauto calls would go here.
        _ = intent, element, self.app_loader
