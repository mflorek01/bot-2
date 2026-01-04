from __future__ import annotations

from typing import Optional


class UIAHandleResolver:
    def __init__(self, backend: str = "uia"):
        self.backend = backend

    def resolve(self, backend_ref: Optional[str]):
        if not backend_ref:
            return None
        try:
            module = __import__("pywinauto.desktop", fromlist=["Desktop"])
            desktop = module.Desktop(backend=self.backend)
            parts = backend_ref.split("|")
            handle = int(parts[0]) if parts and parts[0] else None
            automation_id = parts[1] if len(parts) > 1 else None
            name = parts[2] if len(parts) > 2 else None
            role = parts[3] if len(parts) > 3 else None
            if handle:
                return desktop.window(handle=handle).wrapper_object()
            if automation_id:
                return desktop.window(best_match=name, control_type=role, automation_id=automation_id).wrapper_object()
            if name:
                return desktop.window(best_match=name).wrapper_object()
        except Exception:
            return None
        return None
