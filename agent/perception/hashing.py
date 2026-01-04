from __future__ import annotations

import hashlib
from typing import Optional, Sequence

from agent.state.models import UIElement, WindowInfo


def _bucket_bbox(bbox: Optional[Sequence[int]], cell_size: int = 32) -> str:
    if not bbox or len(bbox) != 4:
        return "none"
    left, top, right, bottom = bbox
    width = right - left
    height = bottom - top
    bucket = (
        round(left / cell_size),
        round(top / cell_size),
        round(width / cell_size),
        round(height / cell_size),
    )
    raw = ":".join(str(v) for v in bucket)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:8]


def stable_element_id(window: WindowInfo, role: Optional[str], name: Optional[str], automation_id: Optional[str], bbox: Optional[Sequence[int]], parent_chain: Optional[str]) -> str:
    """
    Generate a stable identifier for an element using deterministic traits that
    survive small layout shifts between frames.
    """
    base = [window.fingerprint]
    if automation_id:
        base.append(f"auto:{automation_id}")
    name_part = (name or "noname").strip().lower()
    role_part = (role or "unknown").strip().lower()
    bbox_part = _bucket_bbox(bbox)
    parent_part = (parent_chain or "root").lower()
    base.extend([f"name:{name_part}", f"role:{role_part}", f"bbox:{bbox_part}", f"parent:{parent_part}"])
    digest_input = "|".join(base)
    return hashlib.sha256(digest_input.encode("utf-8")).hexdigest()[:16]


def screen_signature_hash(raw_bytes: bytes) -> str:
    return hashlib.sha256(raw_bytes).hexdigest()


def element_signature(element: UIElement, window: Optional[WindowInfo] = None) -> str:
    parent_chain = ":".join(element.parent_element_ids) if element.parent_element_ids else "root"
    payload = "|".join(
        [
            window.fingerprint if window else "",
            element.element_id,
            element.role or "",
            element.name or "",
            element.automation_id or "",
            _bucket_bbox(element.bbox),
            parent_chain,
            ",".join(sorted(state.value for state in element.states)),
        ]
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def frame_signature(elements: Sequence[UIElement], window: Optional[WindowInfo] = None, max_elements: int = 50) -> str:
    selected = sorted(elements, key=lambda e: (-(e.salience or 0), e.element_id))[:max_elements]
    digest = "|".join(element_signature(e, window) for e in selected)
    return hashlib.sha256(digest.encode("utf-8")).hexdigest()


def rehydrate_element(element: UIElement) -> dict:
    return {
        "element_id": element.element_id,
        "name": element.name,
        "role": element.role,
        "automation_id": element.automation_id,
    }
