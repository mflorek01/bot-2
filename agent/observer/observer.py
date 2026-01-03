from __future__ import annotations

import importlib
import time
from typing import Optional

from agent.state.models import Observation, WindowInfo


class Observer:
    def __init__(self, screenshotter: Optional[callable] = None, ocr_reader: Optional[callable] = None):
        self.screenshotter = screenshotter
        self.ocr_reader = ocr_reader

    def observe(self) -> Observation:
        window = self._foreground_window_info()
        raw_tree = self._uia_snapshot(window)
        screenshot_path = self._maybe_capture_screenshot(window)
        ocr_results = self._maybe_run_ocr(screenshot_path)
        return Observation(
            window=window,
            raw_tree=raw_tree,
            screenshot_path=screenshot_path,
            ocr_results=ocr_results,
            timestamp=time.time(),
        )

    def _foreground_window_info(self) -> WindowInfo:
        try:
            desktop = self._pywinauto_desktop()
            active = desktop.get_active()
            rect = active.rectangle()
            return WindowInfo(
                hwnd=active.handle,
                pid=active.process_id(),
                exe_name=active.process,
                title=active.window_text(),
                bbox=(rect.left, rect.top, rect.right, rect.bottom),
            )
        except Exception:
            return WindowInfo(hwnd=None, pid=None, exe_name=None, title=None, bbox=None)

    def _pywinauto_desktop(self):
        backend = self._load_pywinauto_desktop_backend()
        return backend(backend="uia")

    def _load_pywinauto_desktop_backend(self):
        module = importlib.import_module("pywinauto.desktop")
        return module.Desktop

    def _uia_snapshot(self, window: WindowInfo):
        try:
            desktop = self._pywinauto_desktop()
            if window.hwnd:
                return desktop.window(handle=window.hwnd).wrapper_object()
            return desktop.active()
        except Exception:
            return None

    def _maybe_capture_screenshot(self, window: WindowInfo) -> Optional[str]:
        if not self.screenshotter:
            return None
        return self.screenshotter(window)

    def _maybe_run_ocr(self, screenshot_path: Optional[str]):
        if not screenshot_path or not self.ocr_reader:
            return None
        return self.ocr_reader(screenshot_path)
