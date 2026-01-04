from __future__ import annotations

from dataclasses import dataclass, field
import json
from pathlib import Path
from typing import Dict, List, Optional

from agent.state.models import ActionVerb, IntentAction, IntentTarget, UIState, WorkingMemory


@dataclass
class ProcedureStats:
    runs: int = 0
    successes: int = 0
    failures: int = 0


@dataclass
class ProcedureCheckpoint:
    description: str
    expected_change: Optional[str] = None


@dataclass
class ProcedureStep:
    intent: IntentAction
    checkpoint: Optional[ProcedureCheckpoint] = None


@dataclass
class Procedure:
    name: str
    context_hint: Optional[str]
    preconditions: List[str]
    steps: List[ProcedureStep]
    stop_condition: Optional[str]
    risk: str = "normal"
    status: str = "draft"
    stats: ProcedureStats = field(default_factory=ProcedureStats)


class SkillLibrary:
    def __init__(self, state_path: Optional[Path] = None):
        self.state_path = state_path
        self.procedures: Dict[str, Procedure] = {}
        self._register_defaults()
        self._load_state()

    def register(self, procedure: Procedure) -> None:
        self.procedures[procedure.name] = procedure

    def _register_defaults(self) -> None:
        confirm_ok = Procedure(
            name="confirm_ok",
            context_hint="dialogs",
            preconditions=["dialog_open"],
            steps=[
                ProcedureStep(
                    intent=IntentAction(verb=ActionVerb.CLICK, target=IntentTarget(name_equals="OK", role="button")),
                    checkpoint=ProcedureCheckpoint(description="click ok", expected_change="dialog dismissed"),
                )
            ],
            stop_condition="dialog_closed",
            risk="low",
            status="trusted",
        )
        scroll_down = Procedure(
            name="scroll_down",
            context_hint="long_content",
            preconditions=["content_scrollable"],
            steps=[
                ProcedureStep(
                    intent=IntentAction(verb=ActionVerb.SCROLL, amount=-600),
                    checkpoint=ProcedureCheckpoint(description="scroll content", expected_change="new items visible"),
                )
            ],
            stop_condition="content_end",
            risk="normal",
            status="trial",
        )
        self.register(confirm_ok)
        self.register(scroll_down)

    def match_procedure(self, ui_state: UIState, memory: WorkingMemory) -> Optional[IntentAction]:
        for procedure in self.procedures.values():
            if self._matches_context(procedure, ui_state, memory):
                if procedure.steps:
                    return procedure.steps[0].intent
        return None

    def record_result(self, procedure_name: str, success: bool) -> None:
        procedure = self.procedures.get(procedure_name)
        if not procedure:
            return
        procedure.stats.runs += 1
        if success:
            procedure.stats.successes += 1
        else:
            procedure.stats.failures += 1
        self._update_status(procedure)
        self._persist_state()

    def _matches_context(self, procedure: Procedure, ui_state: UIState, memory: WorkingMemory) -> bool:
        if procedure.status not in {"trusted", "trial"}:
            return False
        if procedure.context_hint:
            in_goal = procedure.context_hint.lower() in (memory.goal or "").lower()
            title = (ui_state.window.title or "").lower()
            exe = (ui_state.window.exe_name or "").lower()
            if not (in_goal or procedure.context_hint.lower() in title or procedure.context_hint.lower() in exe):
                return False
        if procedure.status == "trial" and memory.risk_mode == "high":
            return False
        return True

    def _update_status(self, procedure: Procedure) -> None:
        if procedure.stats.successes >= 3 and procedure.stats.failures == 0:
            procedure.status = "trusted"
        elif procedure.stats.failures >= 3 and procedure.stats.failures >= procedure.stats.successes:
            procedure.status = "degraded"

    def _persist_state(self) -> None:
        if not self.state_path:
            return
        payload = {
            name: {
                "runs": p.stats.runs,
                "successes": p.stats.successes,
                "failures": p.stats.failures,
                "status": p.status,
            }
            for name, p in self.procedures.items()
        }
        self.state_path.parent.mkdir(parents=True, exist_ok=True)
        self.state_path.write_text(json.dumps(payload), encoding="utf-8")

    def _load_state(self) -> None:
        if not self.state_path or not self.state_path.exists():
            return
        try:
            data = json.loads(self.state_path.read_text(encoding="utf-8"))
        except Exception:
            return
        for name, meta in data.items():
            if name in self.procedures:
                proc = self.procedures[name]
                proc.stats.runs = meta.get("runs", proc.stats.runs)
                proc.stats.successes = meta.get("successes", proc.stats.successes)
                proc.stats.failures = meta.get("failures", proc.stats.failures)
                proc.status = meta.get("status", proc.status)
