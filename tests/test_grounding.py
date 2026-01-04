from agent.grounding.grounder import Grounder
from agent.state.models import ActionVerb, ElementState, IntentAction, IntentTarget, TargetSource, UIElement, UIState, WindowInfo


def _window():
    return WindowInfo(hwnd=1, pid=2, exe_name="sample.exe", title="Sample", bbox=(0, 0, 100, 100), platform="windows", warnings=[])


def _ui_state():
    elements = [
        UIElement(
            element_id="submit-btn",
            source=TargetSource.UIA,
            role="button",
            name="Submit",
            value=None,
            automation_id="submit",
            class_name=None,
            bbox=(0, 0, 10, 10),
            states=[ElementState.ENABLED],
            parent_element_ids=[],
            near_text="form",
            salience=2.0,
        ),
        UIElement(
            element_id="cancel-btn",
            source=TargetSource.UIA,
            role="button",
            name="Cancel",
            value=None,
            automation_id="cancel",
            class_name=None,
            bbox=(10, 0, 20, 10),
            states=[ElementState.ENABLED],
            parent_element_ids=[],
            near_text="form",
            salience=1.0,
        ),
    ]
    return UIState(
        window=_window(),
        timestamp=0.0,
        elements=elements,
        focused_element_id=None,
        salient_text=[],
        screen_signature="sig",
    )


def test_grounder_prefers_exact_name():
    ui_state = _ui_state()
    intent = IntentAction(verb=ActionVerb.CLICK, target=IntentTarget(name_contains="submit"))
    grounded = Grounder().ground(intent, ui_state)
    assert grounded.element is not None
    assert grounded.element.element_id == "submit-btn"
    assert grounded.confidence > 0


def test_grounder_honors_automation_id():
    ui_state = _ui_state()
    intent = IntentAction(verb=ActionVerb.CLICK, target=IntentTarget(automation_id="cancel"))
    grounded = Grounder().ground(intent, ui_state)
    assert grounded.element is not None
    assert grounded.element.element_id == "cancel-btn"
