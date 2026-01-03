from __future__ import annotations

import hashlib
from typing import Optional, Sequence

from agent.state.models import UIElement, WindowInfo


def _bucket_bbox(bbox: Optional[Sequence[int]]) -> str:
    if not bbox or len(bbox) != 4:
        return "none"
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    cell_size = 25
    bucket = (
        left // cell_size,
        top // cell_size,
        width // cell_size,
        height // cell_size,
    )
    raw = ":".join(str(v) for v in bucket)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def stable_element_id(window: WindowInfo, role: Optional[str], name: Optional[str], automation_id: Optional[str], bbox: Optional[Sequence[int]], parent_chain: Optional[str]) -> str:
    base = f"{window.fingerprint}:"
    if automation_id:
        base += f"auto:{automation_id}"
    else:
        name_part = name or "noname"
        role_part = role or "unknown"
        bbox_part = _bucket_bbox(bbox)
        parent_part = parent_chain or "root"
        base += f"heur:{name_part}:{role_part}:{bbox_part}:{parent_part}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()[:16]


def screen_signature_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def rehydrate_element(element: UIElement) -> dict:
    return {
        "element_id": element.element_id,
        "name": element.name,
        "role": element.role,
        "automation_id": element.automation_id,
    }
