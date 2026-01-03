from __future__ import annotations

import hashlib
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence


class ActionVerb(str, Enum):
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEYPRESS = "keypress"
    SCROLL = "scroll"
    WAIT = "wait"
    FOCUS_WINDOW = "focus_window"
    OPEN_URL = "open_url"
    CLOSE_DIALOG = "close_dialog"
    ASK_USER = "ask_user"
    STOP = "stop"


class TargetSource(str, Enum):
    UIA = "uia"
    OCR = "ocr"


class ElementState(str, Enum):
    ENABLED = "enabled"
    DISABLED = "disabled"
    FOCUSED = "focused"
    CHECKED = "checked"
    SELECTED = "selected"
    OFFSCREEN = "offscreen"


class ExecutionMethod(str, Enum):
    UIA = "uia"
    MOUSE = "mouse"
    KEYBOARD = "keyboard"
    NOOP = "noop"


class ExecutionStatus(str, Enum):
    OK = "ok"
    FAIL = "fail"
    SKIPPED = "skipped"


class VerificationStatus(str, Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAIL = "fail"
    STUCK = "stuck"


@dataclass(frozen=True)
class WindowInfo:
    hwnd: Optional[int]
    pid: Optional[int]
    exe_name: Optional[str]
    title: Optional[str]
    bbox: Optional[Sequence[int]]

    @property
    def fingerprint(self) -> str:
        raw = f"{self.exe_name or ''}:{self.hwnd or ''}:{self.title or ''}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:12]


@dataclass(frozen=True)
class UIElement:
    element_id: str
    source: TargetSource
    role: Optional[str]
    name: Optional[str]
    value: Optional[str]
    automation_id: Optional[str]
    class_name: Optional[str]
    bbox: Optional[Sequence[int]]
    states: Sequence[ElementState] = field(default_factory=list)
    parent_element_ids: Sequence[str] = field(default_factory=list)
    near_text: Optional[str] = None


@dataclass(frozen=True)
class UIState:
    window: WindowInfo
    timestamp: float
    elements: List[UIElement]
    focused_element_id: Optional[str]
    salient_text: List[str]
    screen_signature: Optional[str]


@dataclass(frozen=True)
class Observation:
    window: WindowInfo
    raw_tree: Any
    screenshot_path: Optional[str]
    ocr_results: Optional[List[str]]
    timestamp: float = field(default_factory=lambda: time.time())


@dataclass(frozen=True)
class IntentTarget:
    role: Optional[str] = None
    name_contains: Optional[str] = None
    name_equals: Optional[str] = None
    automation_id: Optional[str] = None
    near_text: Optional[str] = None
    element_id: Optional[str] = None


@dataclass(frozen=True)
class IntentAction:
    verb: ActionVerb
    target: Optional[IntentTarget] = None
    text: Optional[str] = None
    key: Optional[str] = None
    amount: Optional[int] = None
    wait_seconds: Optional[float] = None


@dataclass(frozen=True)
class GroundedTarget:
    element: Optional[UIElement]
    confidence: float
    alternatives: List[UIElement]


@dataclass(frozen=True)
class ExecutionResult:
    status: ExecutionStatus
    method: ExecutionMethod
    duration: float
    error: Optional[str] = None


@dataclass(frozen=True)
class VerificationResult:
    status: VerificationStatus
    failure_reason: Optional[str]
    guidance_delta: Optional[str]
    updated_focus_id: Optional[str]


@dataclass
class WorkingMemory:
    goal: Optional[str] = None
    subgoal: Optional[str] = None
    constraints: List[str] = field(default_factory=list)
    risk_mode: str = "normal"
    step_budget: int = 20
    last_error: Optional[str] = None
    reflection: Optional[str] = None


@dataclass
class EpisodicStep:
    intent: IntentAction
    grounded: Optional[GroundedTarget]
    execution: Optional[ExecutionResult]
    verification: Optional[VerificationResult]
    observation_signature: Optional[str]


@dataclass
class NotebookEntry:
    key: str
    value: str
    confidence: float
    updated_at: float = field(default_factory=lambda: time.time())


@dataclass
class Notebook:
    facts: Dict[str, NotebookEntry] = field(default_factory=dict)

    def upsert(self, key: str, value: str, confidence: float) -> None:
        self.facts[key] = NotebookEntry(key=key, value=value, confidence=confidence)

    def get(self, key: str) -> Optional[NotebookEntry]:
        return self.facts.get(key)
