from __future__ import annotations

import importlib
import logging
import time
from typing import Optional, Tuple

from agent.state.models import ActionVerb, ExecutionMethod, ExecutionResult, ExecutionStatus, GroundedTarget, IntentAction


class MouseKeyboardExecutor:
    def __init__(self, driver: Optional[callable] = None, max_retries: int = 1, backoff_seconds: float = 0.1):
        self.driver = driver
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.logger = logging.getLogger(__name__)

    def execute(self, intent: IntentAction, target: GroundedTarget) -> ExecutionResult:
        start = time.time()
        error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                self._perform(intent, target)
                return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.MOUSE, duration=time.time() - start)
            except Exception as exc:
                error = str(exc)
                self.logger.debug("Mouse/keyboard attempt %s failed: %s", attempt + 1, error)
                time.sleep(self.backoff_seconds * (2 ** attempt))
        return ExecutionResult(
            status=ExecutionStatus.FAIL, method=ExecutionMethod.MOUSE, duration=time.time() - start, error=error
        )

    def _perform(self, intent: IntentAction, target: GroundedTarget) -> None:
        if not target.element:
            raise ValueError("Cannot perform action without grounded element")
        driver = self._load_driver()
        bbox_center = self._bbox_center(target.element.bbox)
        if intent.verb in {ActionVerb.CLICK, ActionVerb.DOUBLE_CLICK, ActionVerb.RIGHT_CLICK}:
            if not bbox_center:
                raise RuntimeError("No coordinates for mouse action")
            self._click(driver, bbox_center, intent.verb)
        elif intent.verb == ActionVerb.TYPE and intent.text is not None:
            self._type(driver, intent.text)
        elif intent.verb == ActionVerb.SCROLL and intent.amount is not None:
            self._scroll(driver, intent.amount, bbox_center)
        elif intent.verb == ActionVerb.FOCUS_WINDOW and bbox_center:
            self._click(driver, bbox_center, ActionVerb.CLICK)
        elif intent.verb == ActionVerb.WAIT:
            time.sleep(intent.wait_seconds or 0.5)
        else:
            raise ValueError(f"Unsupported mouse/keyboard verb {intent.verb}")

    def _load_driver(self):
        if self.driver:
            return self.driver
        try:
            return importlib.import_module("pyautogui")
        except Exception as exc:
            raise RuntimeError(f"pyautogui not available for mouse/keyboard fallback: {exc}")

    def _bbox_center(self, bbox: Optional[Tuple[int, int, int, int]]) -> Optional[Tuple[int, int]]:
        if not bbox:
            return None
        left, top, right, bottom = bbox
        return (int((left + right) / 2), int((top + bottom) / 2))

    def _click(self, driver: any, point: Tuple[int, int], verb: ActionVerb) -> None:
        button = "left"
        clicks = 1
        if verb == ActionVerb.DOUBLE_CLICK:
            clicks = 2
        if verb == ActionVerb.RIGHT_CLICK:
            button = "right"
        driver.click(x=point[0], y=point[1], clicks=clicks, button=button)

    def _type(self, driver: any, text: str) -> None:
        driver.typewrite(text, interval=0.01)

    def _scroll(self, driver: any, amount: int, point: Optional[Tuple[int, int]]) -> None:
        if point:
            driver.moveTo(point[0], point[1])
        driver.scroll(amount)
