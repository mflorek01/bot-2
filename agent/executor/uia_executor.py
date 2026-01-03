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
        wrapper = self._resolve_wrapper(element, target)
        verb = intent.verb.value
        if verb in {"click", "double_click", "right_click"}:
            self._perform_click(wrapper, verb)
        elif verb == "type":
            if intent.text is None:
                raise ValueError("Missing text for type action")
            try:
                wrapper.set_edit_text(intent.text)
            except Exception:
                wrapper.type_keys(intent.text, with_spaces=True, set_foreground=True)
        elif verb == "keypress":
            if intent.key is None:
                raise ValueError("Missing key for keypress action")
            wrapper.type_keys(intent.key, set_foreground=True)
        elif verb == "scroll":
            amount = intent.amount or 120
            wrapper.wheel_mouse_input(wheel_dist=amount)
        elif verb == "wait":
            time.sleep(intent.wait_seconds or 1.0)
        elif verb == "focus_window":
            wrapper.set_focus()
        elif verb == "close_dialog":
            wrapper.close()
        elif verb == "open_url":
            if intent.text:
                import webbrowser

                webbrowser.open(intent.text)
        elif verb == "ask_user":
            raise RuntimeError("ask_user requires out-of-band handling")
        elif verb == "stop":
            return
        else:
            raise ValueError(f"Unsupported verb: {verb}")

    def _resolve_wrapper(self, element, target: GroundedTarget):
        try:
            desktop = self._load_desktop()
        except Exception as exc:
            raise RuntimeError(f"pywinauto not available: {exc}")
        if target.window and target.window.hwnd:
            window = desktop.window(handle=target.window.hwnd)
        else:
            window = desktop.active()
        criteria = {}
        if element.automation_id:
            criteria["automation_id"] = element.automation_id
        if element.name:
            criteria["title"] = element.name
        if element.class_name:
            criteria["class_name"] = element.class_name
        if element.role:
            criteria["control_type"] = element.role
        try:
            candidate = window.child_window(**criteria).wrapper_object()
            return candidate
        except Exception:
            pass
        descendants = window.descendants(**{k: v for k, v in criteria.items() if k in {"automation_id", "title", "control_type"}})
        if descendants:
            return descendants[0].wrapper_object()
        raise RuntimeError("Unable to resolve UIA element")

    def _perform_click(self, wrapper, verb: str):
        if verb == "click":
            wrapper.click_input()
        elif verb == "double_click":
            wrapper.double_click_input()
        elif verb == "right_click":
            wrapper.right_click_input()

    def _load_desktop(self):
        import importlib

        module = importlib.import_module("pywinauto.desktop")
        return module.Desktop(backend="uia")
