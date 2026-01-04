from agent.agent_loop import AgentConfig, AutomationAgent
from agent.executor.mouse_keyboard import MouseKeyboardExecutor
from agent.executor.uia_executor import UIAExecutor
from agent.perception.compression import UICompressor
from agent.state.models import ActionVerb, ElementState, ExecutionMethod, ExecutionResult, ExecutionStatus, Observation, WindowInfo


class DummyObserver:
    def observe(self) -> Observation:
        window = WindowInfo(hwnd=1, pid=1, exe_name="app.exe", title="Title", bbox=(0, 0, 20, 20), platform="test", warnings=[])
        raw_tree = {
            "name": "OK",
            "role": "button",
            "automation_id": "ok",
            "class_name": "Button",
            "bbox": (0, 0, 10, 10),
            "states": [ElementState.ENABLED],
            "children": [],
            "parent_chain": "root",
        }
        return Observation(window=window, raw_tree=raw_tree, screenshot_path=None, ocr_results=[])


class NoOpExecutor(UIAExecutor):
    def execute(self, intent, target) -> ExecutionResult:
        _ = intent, target
        return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.NOOP, duration=0.0)


class NoOpMouse(MouseKeyboardExecutor):
    def execute(self, intent, target) -> ExecutionResult:
        _ = intent, target
        return ExecutionResult(status=ExecutionStatus.OK, method=ExecutionMethod.NOOP, duration=0.0)


def test_agent_loop_runs_with_mock_components(tmp_path):
    observer = DummyObserver()
    compressor = UICompressor()
    agent = AutomationAgent(
        observer=observer,
        compressor=compressor,
        uia_executor=NoOpExecutor(),
        mouse_executor=NoOpMouse(),
        config=AgentConfig(log_dir=tmp_path, step_budget=1, enable_ocr=False, enable_screenshots=False),
    )
    agent.memory.goal = "Click ok"
    agent.run()
    assert agent.trace
    assert agent.trace[0].intent.verb in {ActionVerb.CLICK, ActionVerb.WAIT}
