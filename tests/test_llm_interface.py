from agent.decision.llm_interface import LLMInterface
from agent.state.models import ActionVerb, ElementState, TargetSource, UIElement, UIState, WindowInfo


def _state():
    window = WindowInfo(hwnd=1, pid=1, exe_name="app.exe", title="App", bbox=(0, 0, 10, 10), platform="windows", warnings=[])
    elements = [
        UIElement(
            element_id="btn1",
            source=TargetSource.UIA,
            role="button",
            name="Click me",
            value=None,
            automation_id=None,
            class_name=None,
            bbox=None,
            states=[ElementState.ENABLED],
            parent_element_ids=[],
            near_text=None,
            salience=2.0,
            backend_ref=None,
        )
    ]
    return UIState(window=window, timestamp=0.0, elements=elements, focused_element_id=None, salient_text=[], screen_signature="sig")


def test_llm_interface_fallback_generates_action():
    llm = LLMInterface(client=None)
    actions = llm.propose(_state(), goal="click button")
    assert actions
    assert actions[0].verb == ActionVerb.CLICK
