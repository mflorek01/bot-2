from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

from agent.state.models import IntentAction, UIState, WorkingMemory


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
    def __init__(self):
        self.procedures: Dict[str, Procedure] = {}

    def register(self, procedure: Procedure) -> None:
        self.procedures[procedure.name] = procedure

    def match_procedure(self, ui_state: UIState, memory: WorkingMemory) -> Optional[IntentAction]:
        _ = ui_state, memory
        for procedure in self.procedures.values():
            if procedure.status == "trusted":
                if procedure.steps:
                    return procedure.steps[0].intent
        return None
