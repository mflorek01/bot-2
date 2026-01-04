from agent.perception.hashing import frame_signature, stable_element_id
from agent.state.models import ElementState, TargetSource, UIElement, WindowInfo


def _window():
    return WindowInfo(hwnd=1, pid=1, exe_name="app.exe", title="Title", bbox=(0, 0, 100, 100), platform="windows", warnings=[])


def test_stable_element_id_resilient_to_small_shifts():
    window = _window()
    eid1 = stable_element_id(window, "button", "OK", "auto1", (10, 10, 30, 30), "root")
    eid2 = stable_element_id(window, "button", "OK", "auto1", (12, 11, 32, 31), "root")
    assert eid1 == eid2


def test_frame_signature_order_invariant():
    window = _window()
    elements = [
        UIElement(
            element_id="a",
            source=TargetSource.UIA,
            role="button",
            name="OK",
            value=None,
            automation_id=None,
            class_name=None,
            bbox=(0, 0, 10, 10),
            states=[ElementState.ENABLED],
            parent_element_ids=[],
            near_text=None,
            salience=2.0,
        ),
        UIElement(
            element_id="b",
            source=TargetSource.UIA,
            role="text",
            name="Label",
            value=None,
            automation_id=None,
            class_name=None,
            bbox=(0, 0, 5, 5),
            states=[],
            parent_element_ids=[],
            near_text=None,
            salience=0.1,
        ),
    ]
    sig1 = frame_signature(elements, window)
    sig2 = frame_signature(list(reversed(elements)), window)
    assert sig1 == sig2
