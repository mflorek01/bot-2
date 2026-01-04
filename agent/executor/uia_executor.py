from __future__ import annotations

import time
import logging
from typing import Any, Optional

from agent.executor.handle_resolver import UIAHandleResolver
from agent.state.models import ActionVerb, ExecutionMethod, ExecutionResult, ExecutionStatus, GroundedTarget, IntentAction


class UIAExecutor:
    def __init__(self, app_loader: Optional[callable] = None, max_retries: int = 2, backoff_seconds: float = 0.25, resolver: Optional[UIAHandleResolver] = None):
        self.app_loader = app_loader
        self.max_retries = max_retries
        self.backoff_seconds = backoff_seconds
        self.logger = logging.getLogger(__name__)
        self.resolver = resolver or UIAHandleResolver()

    def execute(self, intent: IntentAction, target: GroundedTarget) -> ExecutionResult:
        start = time.time()
        error: Optional[str] = None
        for attempt in range(self.max_retries + 1):
            try:
                self._invoke(intent, target)
                return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.UIA, duration=time.time() - start)
            except Exception as exc:
                error = self._map_error(exc)
                self.logger.debug("UIA attempt %s failed: %s", attempt + 1, error)
                time.sleep(self.backoff_seconds * (2 ** attempt))
        return ExecutionResult(
            status=ExecutionStatus.FAIL,
            method=ExecutionMethod.UIA,
            duration=time.time() - start,
            error=error,
        )

    def _invoke(self, intent: IntentAction, target: GroundedTarget) -> None:
        element = target.element
        if not element:
            raise ValueError("Cannot invoke UIA action without grounded element")
        wrapper = self._resolve_wrapper(element)
        if not wrapper:
            raise RuntimeError("UIA element wrapper unavailable")
        verb = intent.verb
        if verb in {ActionVerb.CLICK, ActionVerb.DOUBLE_CLICK, ActionVerb.RIGHT_CLICK}:
            self._perform_click(wrapper, verb)
        elif verb == ActionVerb.TYPE and intent.text is not None:
            self._perform_type(wrapper, intent.text)
        elif verb == ActionVerb.SCROLL and intent.amount is not None:
            self._perform_scroll(wrapper, intent.amount)
        elif verb == ActionVerb.FOCUS_WINDOW:
            self._perform_focus(wrapper)
        elif verb == ActionVerb.WAIT:
            time.sleep(intent.wait_seconds or 0.1)
        else:
            raise ValueError(f"Unsupported UIA action: {verb.value}")

    def _resolve_wrapper(self, element: any) -> Optional[Any]:
        if self.app_loader:
            try:
                return self.app_loader(element)
            except Exception:
                return None
        ref = getattr(element, "backend_ref", None)
        if not ref:
            return None
        return self.resolver.resolve(ref)

    def _perform_click(self, wrapper: Any, verb: ActionVerb) -> None:
        action = {
            ActionVerb.CLICK: "click_input",
            ActionVerb.DOUBLE_CLICK: "double_click_input",
            ActionVerb.RIGHT_CLICK: "right_click_input",
        }.get(verb, "click_input")
        if hasattr(wrapper, action):
            getattr(wrapper, action)()
            return
        if hasattr(wrapper, "invoke"):
            wrapper.invoke()
            return
        raise RuntimeError("UIA element cannot be clicked")

    def _perform_type(self, wrapper: Any, text: str) -> None:
        if hasattr(wrapper, "type_keys"):
            wrapper.type_keys(text, with_spaces=True, set_foreground=True)
            return
        if hasattr(wrapper, "set_value"):
            wrapper.set_value(text)
            return
        raise RuntimeError("UIA element cannot accept text input")

    def _perform_scroll(self, wrapper: Any, amount: int) -> None:
        if hasattr(wrapper, "scroll"):
            wrapper.scroll(amount)
            return
        if hasattr(wrapper, "wheel_mouse_input"):
            wrapper.wheel_mouse_input(wheel_dist=amount)
            return
        raise RuntimeError("UIA element cannot scroll")

    def _perform_focus(self, wrapper: Any) -> None:
        if hasattr(wrapper, "set_focus"):
            wrapper.set_focus()
        else:
            raise RuntimeError("UIA element cannot focus")

    def _map_error(self, exc: Exception) -> str:
        message = str(exc)
        if "timeout" in message.lower():
            return f"uia-timeout:{message}"
        if "not found" in message.lower():
            return f"uia-missing:{message}"
        return f"uia-error:{message}"
