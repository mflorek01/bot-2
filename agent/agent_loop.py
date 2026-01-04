from __future__ import annotations

from dataclasses import dataclass
import logging
import platform
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
from agent.state.models import EpisodicStep, ExecutionResult, ExecutionStatus, IntentAction, SafetyLevel, VerificationStatus, WorkingMemory
from agent.verifier.verifier import VerificationContext, Verifier


@dataclass
class AgentConfig:
    log_dir: Path = Path("logs")
    step_budget: int = 20
    enable_ocr: bool = True
    enable_screenshots: bool = True
    safety_level: SafetyLevel = SafetyLevel.NORMAL
    log_verbose: bool = False
    validate_dependencies: bool = True
    ocr_binary: Optional[str] = None
    llm_endpoint: Optional[str] = None
    llm_api_key: Optional[str] = None


class AutomationAgent:
    def __init__(
        self,
        observer: Optional[Observer] = None,
        compressor: Optional[UICompressor] = None,
        grounder: Optional[Grounder] = None,
        verifier: Optional[Verifier] = None,
        decision_engine: Optional[DecisionEngine] = None,
        uia_executor: Optional[UIAExecutor] = None,
        mouse_executor: Optional[MouseKeyboardExecutor] = None,
        logger: Optional[JsonLogger] = None,
        config: AgentConfig = AgentConfig(),
    ):
        self.config = config
        if not isinstance(self.config.log_dir, Path):
            self.config.log_dir = Path(self.config.log_dir)
        self.config.log_dir.mkdir(parents=True, exist_ok=True)
        self.observer = observer or Observer(
            screenshot_dir=config.log_dir / "screenshots",
            enable_screenshots=config.enable_screenshots,
            enable_ocr=config.enable_ocr,
            ocr_reader=self._default_ocr_reader(),
        )
        self.compressor = compressor or UICompressor()
        self.grounder = grounder or Grounder()
        self.verifier = verifier or Verifier()
        self.uia_executor = uia_executor or UIAExecutor()
        self.mouse_executor = mouse_executor or MouseKeyboardExecutor()
        self.skills = SkillLibrary(state_path=config.log_dir / "skills_state.json")
        selector_logger = logger or JsonLogger(config.log_dir, host_platform=platform.system().lower())
        self.logger = selector_logger
        llm = LLMInterface(client=self._default_llm_client)
        self.decision_engine = decision_engine or DecisionEngine(skills=self.skills, selector=self._selector_proxy, llm=llm)
        self.memory = WorkingMemory(step_budget=config.step_budget, risk_mode=config.safety_level.value)
        self.trace: list[EpisodicStep] = []
        self._step_index = 0
        if self.config.validate_dependencies:
            self._validate_environment()

    @property
    def _selector_proxy(self):
        from agent.selector.selector import Selector

        return Selector(safety_level=self.config.safety_level)

    def run(self):
        for _ in range(self.config.step_budget):
            observation = self.observer.observe()
            self.logger.log(self._step_index, "observe", {"window": observation.window.fingerprint, "warnings": observation.warnings})
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

    def _validate_environment(self) -> None:
        logger = logging.getLogger(__name__)
        if self.config.log_verbose:
            logging.basicConfig(level=logging.DEBUG)
        if platform.system().lower().startswith("win"):
            try:
                import importlib

                importlib.import_module("pywinauto")
            except Exception:
                logger.warning("pywinauto not available; UIA execution may be limited.")
        else:
            logger.warning("Non-Windows platform detected; UIA operations may be disabled.")
        try:
            import importlib

            importlib.import_module("pyautogui")
        except Exception:
            logger.warning("pyautogui not available; mouse/keyboard fallback may fail.")
        if self.config.llm_endpoint and not self.config.llm_api_key:
            logger.warning("LLM endpoint configured without API key; falling back to heuristic proposer.")

    @property
    def _default_llm_client(self):
        if self.config.llm_endpoint and self.config.llm_api_key:
            def client(ui_state, goal, candidate_actions=None):
                import requests
                payload = {
                    "goal": goal,
                    "candidate_actions": [a.verb.value for a in candidate_actions] if candidate_actions else [],
                    "salient": ui_state.salient_text,
                }
                headers = {"Authorization": f"Bearer {self.config.llm_api_key}"}
                resp = requests.post(self.config.llm_endpoint, json=payload, timeout=10, headers=headers)
                resp.raise_for_status()
                data = resp.json()
                return data.get("actions", [])
            return client
        # Heuristic fallback
        def client(ui_state, goal, candidate_actions=None):
            _ = goal, candidate_actions
            # Pick the top-salience clickable element if present.
            for element in sorted(ui_state.elements, key=lambda e: (-(e.salience or 0.0), e.element_id)):
                if element.role and element.role.lower() in {"button", "hyperlink"}:
                    from agent.state.models import ActionVerb, IntentTarget, IntentAction as Intent

                    return [Intent(verb=ActionVerb.CLICK, target=IntentTarget(element_id=element.element_id))]
            return []

        return client

    def _default_ocr_reader(self):
        try:
            import pytesseract
            from PIL import Image
        except Exception:
            return None

        def reader(path: str):
            if self.config.ocr_binary:
                pytesseract.pytesseract.tesseract_cmd = self.config.ocr_binary
            img = Image.open(path)
            return [line for line in pytesseract.image_to_string(img).splitlines() if line]

        return reader
