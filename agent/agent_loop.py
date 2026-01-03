from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from agent.decision.decision_engine import DecisionEngine
from agent.decision.llm_interface import LLMInterface
from agent.executor.mouse_keyboard import MouseKeyboardExecutor
from agent.executor.uia_executor import UIAExecutor
from agent.grounding.grounder import Grounder
from agent.logging.json_logger import JsonLogger
from agent.observer.observer import Observer
from agent.perception.compression import UICompressor
from agent.skills.skill_library import SkillLibrary
from agent.state.models import EpisodicStep, ExecutionResult, ExecutionStatus, IntentAction, VerificationStatus, WorkingMemory
from agent.verifier.verifier import VerificationContext, Verifier


@dataclass
class AgentConfig:
    log_dir: Path = Path("logs")
    step_budget: int = 20


class AutomationAgent:
    def __init__(self, observer: Optional[Observer] = None, compressor: Optional[UICompressor] = None, grounder: Optional[Grounder] = None, verifier: Optional[Verifier] = None, decision_engine: Optional[DecisionEngine] = None, uia_executor: Optional[UIAExecutor] = None, mouse_executor: Optional[MouseKeyboardExecutor] = None, logger: Optional[JsonLogger] = None, config: AgentConfig = AgentConfig()):
        self.observer = observer or Observer()
        self.compressor = compressor or UICompressor()
        self.grounder = grounder or Grounder()
        self.verifier = verifier or Verifier()
        self.uia_executor = uia_executor or UIAExecutor()
        self.mouse_executor = mouse_executor or MouseKeyboardExecutor()
        self.skills = SkillLibrary()
        selector_logger = logger or JsonLogger(config.log_dir)
        self.logger = selector_logger
        llm = LLMInterface()
        self.decision_engine = decision_engine or DecisionEngine(skills=self.skills, selector=self._selector_proxy, llm=llm)
        self.config = config
        self.memory = WorkingMemory(step_budget=config.step_budget)
        self.trace: list[EpisodicStep] = []
        self._step_index = 0

    @property
    def _selector_proxy(self):
        from agent.selector.selector import Selector

        return Selector()

    def run(self):
        for _ in range(self.config.step_budget):
            observation = self.observer.observe()
            self.logger.log(self._step_index, "observe", {"window": observation.window.fingerprint})
            ui_state = self.compressor.compress(observation)
            self.logger.log(self._step_index, "state", {"elements": len(ui_state.elements)})
            decision = self.decision_engine.decide(ui_state, self.memory)
            self.logger.log(self._step_index, "decide", {"rationale": decision.rationale, "used_llm": decision.used_llm})
            grounded = self.grounder.ground(decision.intent, ui_state)
            self.logger.log(self._step_index, "ground", {"confidence": grounded.confidence})
            execution = self._execute(decision.intent, grounded)
            self.logger.log(self._step_index, "execute", {"status": execution.status.value, "method": execution.method.value})
            new_observation = self.observer.observe()
            new_state = self.compressor.compress(new_observation)
            verification = self.verifier.verify(
                VerificationContext(previous_state=ui_state, current_state=new_state, observation=new_observation)
            )
            self.logger.log(self._step_index, "verify", {"status": verification.status.value})
            self._update_memory(verification)
            self.trace.append(
                EpisodicStep(
                    intent=decision.intent,
                    grounded=grounded,
                    execution=execution,
                    verification=verification,
                    observation_signature=new_state.screen_signature,
                )
            )
            self._step_index += 1
            if verification.status in {VerificationStatus.STUCK, VerificationStatus.FAIL}:
                break

    def _execute(self, intent: IntentAction, grounded: any) -> ExecutionResult:
        if grounded.element:
            result = self.uia_executor.execute(intent, grounded)
            if result.status == ExecutionStatus.OK:
                return result
        return self.mouse_executor.execute(intent, grounded)

    def _update_memory(self, verification):
        if verification.failure_reason:
            self.memory.last_error = verification.failure_reason
