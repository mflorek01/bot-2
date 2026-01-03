from __future__ import annotations

import time
from typing import Optional

from agent.state.models import ExecutionMethod, ExecutionResult, ExecutionStatus, GroundedTarget, IntentAction


class MouseKeyboardExecutor:
    def execute(self, intent: IntentAction, target: GroundedTarget) -> ExecutionResult:
        start = time.time()
        try:
            self._perform(intent, target)
            return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.MOUSE, duration=time.time() - start)
        except Exception as exc:
            return ExecutionResult(
                status=ExecutionStatus.FAIL, method=ExecutionMethod.MOUSE, duration=time.time() - start, error=str(exc)
            )

    def _perform(self, intent: IntentAction, target: GroundedTarget) -> None:
        element = target.element
        if not element or not element.bbox:
            raise ValueError("Cannot perform mouse action without bbox")
        left, top, right, bottom = element.bbox
        x = (left + right) // 2
        y = (top + bottom) // 2
        try:
            import pyautogui
        except Exception as exc:
            raise RuntimeError(f"pyautogui unavailable: {exc}")
        verb = intent.verb.value
        if verb == "click":
            pyautogui.click(x, y)
        elif verb == "double_click":
            pyautogui.doubleClick(x, y)
        elif verb == "right_click":
            pyautogui.rightClick(x, y)
        elif verb == "scroll":
            pyautogui.scroll(intent.amount or 120)
        elif verb == "type":
            if intent.text is None:
                raise ValueError("Missing text for typing")
            pyautogui.click(x, y)
            pyautogui.typewrite(intent.text)
        elif verb == "keypress":
            if intent.key is None:
                raise ValueError("Missing key for keypress")
            pyautogui.press(intent.key)
        elif verb == "wait":
            time.sleep(intent.wait_seconds or 1.0)
        else:
            raise ValueError(f"Unsupported mouse/keyboard verb: {verb}")
