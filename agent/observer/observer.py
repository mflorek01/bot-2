from __future__ import annotations

import importlib
import platform
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence

from agent.state.models import ElementState, Observation, TargetSource, UIElement, WindowInfo


@dataclass
class RawUIANode:
    control_type: Optional[str]
    name: Optional[str]
    automation_id: Optional[str]
    class_name: Optional[str]
    bbox: Optional[Sequence[int]]
    is_enabled: bool
    has_keyboard_focus: bool
    is_offscreen: bool
    patterns: List[str]
    legacy_properties: Dict[str, Any]


class Observer:
    def __init__(self, screenshotter: Optional[callable] = None, ocr_reader: Optional[callable] = None, max_depth: int = 4, max_nodes: int = 400):
        self.screenshotter = screenshotter
        self.ocr_reader = ocr_reader
        self.max_depth = max_depth
        self.max_nodes = max_nodes

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
        if platform.system().lower() != "windows":
            return []
        try:
            desktop = self._pywinauto_desktop()
            if window.hwnd:
                root = desktop.window(handle=window.hwnd).wrapper_object()
            else:
                root = desktop.active()
            nodes: List[Dict[str, Any]] = []
            self._walk_uia(root, nodes, parent_chain="root", depth=0)
            return nodes
        except Exception:
            return []

    def _maybe_capture_screenshot(self, window: WindowInfo) -> Optional[str]:
        if not self.screenshotter:
            return None
        return self.screenshotter(window)

    def _maybe_run_ocr(self, screenshot_path: Optional[str]):
        if not screenshot_path or not self.ocr_reader:
            return None
        return self.ocr_reader(screenshot_path)

    def _walk_uia(self, element: Any, nodes: List[Dict[str, Any]], parent_chain: str, depth: int) -> None:
        if depth > self.max_depth or len(nodes) >= self.max_nodes:
            return
        try:
            info = element.element_info
            rect = info.rectangle
            bbox = None
            if rect:
                bbox = (rect.left, rect.top, rect.right, rect.bottom)
            node = {
                "control_type": getattr(info, "control_type", None),
                "name": getattr(info, "name", None),
                "automation_id": getattr(info, "automation_id", None),
                "class_name": getattr(info, "class_name", None),
                "bbox": bbox,
                "is_enabled": getattr(info, "is_enabled", False),
                "has_keyboard_focus": getattr(info, "has_keyboard_focus", False),
                "is_offscreen": getattr(info, "is_offscreen", False),
                "patterns": list(getattr(info, "get_pattern_ids", lambda: [])() or []),
                "legacy_properties": {},
                "parent_chain": parent_chain,
            }
            nodes.append(node)
            child_parent_chain = f"{parent_chain}/{node['control_type'] or 'node'}:{node['automation_id'] or node['name'] or len(nodes)}"
            for child in element.children():
                self._walk_uia(child, nodes, parent_chain=child_parent_chain, depth=depth + 1)
        except Exception:
            return
