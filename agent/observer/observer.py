from __future__ import annotations

import importlib
import logging
import platform
from pathlib import Path
import time
from typing import Any, Dict, List, Optional, Sequence

from agent.state.models import ElementState, Observation, OCRSpan, WindowInfo

logger = logging.getLogger(__name__)


class Observer:
    def __init__(self, screenshotter: Optional[callable] = None, ocr_reader: Optional[callable] = None, screenshot_dir: Path | str = Path("screenshots"), enable_screenshots: bool = True, enable_ocr: bool = True, max_depth: int = 4):
        self.screenshotter = screenshotter
        self.ocr_reader = ocr_reader
        self.screenshot_dir = Path(screenshot_dir)
        self.enable_screenshots = enable_screenshots
        self.enable_ocr = enable_ocr
        self.max_depth = max_depth
        self.screenshot_dir.mkdir(parents=True, exist_ok=True)
        self._platform = platform.system().lower()

    def observe(self) -> Observation:
        warnings: List[str] = []
        if not self._is_windows:
            warning = f"Non-Windows platform detected ({self._platform}); UIA features disabled"
            logger.debug(warning)
            warnings.append(warning)
        window = self._foreground_window_info(warnings)
        raw_tree = self._uia_snapshot(window, warnings)
        screenshot_path = self._maybe_capture_screenshot(window, warnings)
        ocr_results = self._maybe_run_ocr(screenshot_path, warnings)
        return Observation(
            window=window,
            raw_tree=raw_tree,
            screenshot_path=screenshot_path,
            ocr_results=ocr_results,
            timestamp=time.time(),
            warnings=warnings,
        )

    @property
    def _is_windows(self) -> bool:
        return self._platform.startswith("win")

    def _foreground_window_info(self, warnings: List[str]) -> WindowInfo:
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
                platform=self._platform,
                warnings=warnings,
            )
        except Exception as exc:
            warnings.append(f"Unable to resolve foreground window: {exc}")
            return WindowInfo(hwnd=None, pid=None, exe_name=None, title=None, bbox=None, platform=self._platform, warnings=warnings)

    def _pywinauto_desktop(self):
        backend = self._load_pywinauto_desktop_backend()
        return backend(backend="uia")

    def _load_pywinauto_desktop_backend(self):
        if not self._is_windows:
            raise RuntimeError("pywinauto is only available on Windows hosts")
        module = importlib.import_module("pywinauto.desktop")
        return module.Desktop

    def _uia_snapshot(self, window: WindowInfo, warnings: List[str]) -> Optional[Dict[str, Any]]:
        if not self._is_windows:
            return None
        try:
            desktop = self._pywinauto_desktop()
            wrapper = desktop.window(handle=window.hwnd).wrapper_object() if window.hwnd else desktop.active()
            return self._serialize_wrapper(wrapper, depth=0, parent_chain="root")
        except Exception as exc:
            warnings.append(f"UIA snapshot failed: {exc}")
            logger.debug("UIA snapshot failure", exc_info=exc)
            return None

    def _serialize_wrapper(self, wrapper: Any, depth: int, parent_chain: str) -> Dict[str, Any]:
        if depth > self.max_depth:
            return None
        info = getattr(wrapper, "element_info", None)
        bbox = self._rect_to_bbox(getattr(info, "rectangle", None))
        ref = self._wrapper_ref(info, parent_chain)
        node = {
            "name": getattr(info, "name", None) or getattr(wrapper, "window_text", lambda: None)(),
            "role": getattr(info, "control_type", None) or getattr(wrapper, "friendly_class_name", lambda: None)(),
            "automation_id": getattr(info, "automation_id", None),
            "class_name": getattr(info, "class_name", None),
            "bbox": bbox,
            "states": self._wrapper_states(wrapper),
            "children": [],
            "parent_chain": parent_chain,
            "backend_ref": ref,
        }
        children: Sequence[Any] = []
        try:
            children = getattr(wrapper, "children", lambda: [])()
        except Exception:
            children = []
        for idx, child in enumerate(children):
            child_serialized = self._serialize_wrapper(child, depth + 1, f"{parent_chain}.{idx}")
            if child_serialized:
                node["children"].append(child_serialized)
        return node

    def _wrapper_states(self, wrapper: Any) -> List[ElementState]:
        states: List[ElementState] = []
        checks = [
            (ElementState.FOCUSED, "has_keyboard_focus"),
            (ElementState.ENABLED, "is_enabled"),
            (ElementState.OFFSCREEN, "is_offscreen"),
            (ElementState.CHECKED, "get_toggle_state"),
            (ElementState.SELECTED, "is_selected"),
        ]
        for state, attr in checks:
            try:
                probe = getattr(wrapper, attr, None)
                if callable(probe):
                    result = probe()
                else:
                    result = probe
                if result:
                    states.append(state)
            except Exception:
                continue
        return states

    def _rect_to_bbox(self, rect: Any) -> Optional[Sequence[int]]:
        if not rect:
            return None
        try:
            return (int(rect.left), int(rect.top), int(rect.right), int(rect.bottom))
        except Exception:
            return None

    def _wrapper_ref(self, info: Any, parent_chain: str) -> Optional[str]:
        try:
            handle = getattr(info, "handle", None)
            automation_id = getattr(info, "automation_id", None)
            name = getattr(info, "name", None)
            role = getattr(info, "control_type", None)
            parts = [str(handle) if handle is not None else "", automation_id or "", name or "", role or "", parent_chain]
            return "|".join(parts)
        except Exception:
            return None

    def _maybe_capture_screenshot(self, window: WindowInfo, warnings: List[str]) -> Optional[str]:
        if not self.enable_screenshots:
            return None
        target_path = self.screenshot_dir / f"{int(time.time() * 1000)}.png"
        if self.screenshotter:
            try:
                return self.screenshotter(window)
            except Exception as exc:
                warnings.append(f"Custom screenshotter failed: {exc}")
                logger.debug("Custom screenshot failure", exc_info=exc)
                return None
        if not self._is_windows:
            return None
        try:
            screenshot_module = importlib.import_module("pywinauto.screenshot")
            screenshot_module.take_screenshot(str(target_path), hwnd=window.hwnd)
            return str(target_path)
        except Exception as exc:
            warnings.append(f"Screenshot capture failed: {exc}")
            logger.debug("Screenshot capture failure", exc_info=exc)
            return None

    def _maybe_run_ocr(self, screenshot_path: Optional[str], warnings: List[str]) -> Optional[List[OCRSpan]]:
        if not screenshot_path or not self.enable_ocr:
            return None
        if not self.ocr_reader:
            return None
        try:
            results = self.ocr_reader(screenshot_path)
        except Exception as exc:
            warnings.append(f"OCR failed: {exc}")
            logger.debug("OCR failure", exc_info=exc)
            return None
        spans: List[OCRSpan] = []
        if isinstance(results, list):
            for entry in results:
                if isinstance(entry, OCRSpan):
                    spans.append(entry)
                elif isinstance(entry, dict) and "text" in entry:
                    spans.append(OCRSpan(text=entry.get("text", ""), bbox=entry.get("bbox"), confidence=entry.get("confidence")))
                else:
                    spans.append(OCRSpan(text=str(entry)))
        elif isinstance(results, str):
            spans.append(OCRSpan(text=results))
        return spans or None
