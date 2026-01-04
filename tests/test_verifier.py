from agent.verifier.verifier import VerificationContext, Verifier
from agent.state.models import ElementState, Observation, TargetSource, UIElement, UIState, VerificationStatus, WindowInfo


def _window():
    return WindowInfo(hwnd=1, pid=2, exe_name="sample.exe", title="Sample", bbox=(0, 0, 100, 100), platform="windows", warnings=[])


def _state(signature: str, elements_count: int) -> UIState:
    elements = [
        UIElement(
            element_id=str(i),
            source=TargetSource.UIA,
            role="text",
            name=f"Item {i}",
            value=None,
            automation_id=None,
            class_name=None,
            bbox=(0, i * 5, 10, i * 5 + 2),
            states=[ElementState.ENABLED],
            parent_element_ids=[],
            near_text=None,
            salience=0.1,
        )
        for i in range(elements_count)
    ]
    return UIState(window=_window(), timestamp=0.0, elements=elements, focused_element_id=None, salient_text=[], screen_signature=signature)


def test_verifier_detects_stuck():
    verifier = Verifier()
    observation = Observation(window=_window(), raw_tree=None, screenshot_path=None, ocr_results=[])
    context = VerificationContext(previous_state=None, current_state=_state("same", 2), observation=observation)
    verifier.verify(context)
    verifier.verify(context)
    result = verifier.verify(context)
    assert result.status == VerificationStatus.STUCK


def test_verifier_detects_element_drop():
    verifier = Verifier()
    observation = Observation(window=_window(), raw_tree=None, screenshot_path=None, ocr_results=[])
    prev_state = _state("a", 5)
    curr_state = _state("b", 1)
    context = VerificationContext(previous_state=prev_state, current_state=curr_state, observation=observation)
    result = verifier.verify(context)
    assert result.status == VerificationStatus.FAIL
    assert result.failure_reason == "large element drop"
