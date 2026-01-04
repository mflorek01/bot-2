from agent.skills.skill_library import SkillLibrary
from agent.state.models import ActionVerb, UIState, WindowInfo, WorkingMemory


def _state(title: str) -> UIState:
    window = WindowInfo(hwnd=1, pid=1, exe_name="app.exe", title=title, bbox=(0, 0, 10, 10), platform="windows", warnings=[])
    return UIState(window=window, timestamp=0.0, elements=[], focused_element_id=None, salient_text=[], screen_signature="sig")


def test_skill_matching_uses_context():
    skills = SkillLibrary()
    state = _state("dialogs window")
    intent = skills.match_procedure(state, WorkingMemory(goal="handle dialogs"))
    assert intent is not None
    assert intent.verb == ActionVerb.CLICK


def test_skill_promotion_and_degradation():
    skills = SkillLibrary()
    skills.record_result("scroll_down", success=True)
    skills.record_result("scroll_down", success=True)
    skills.record_result("scroll_down", success=True)
    assert skills.procedures["scroll_down"].status == "trusted"
    skills.record_result("scroll_down", success=False)
    skills.record_result("scroll_down", success=False)
    skills.record_result("scroll_down", success=False)
    assert skills.procedures["scroll_down"].status == "degraded"


def test_skill_persistence(tmp_path):
    path = tmp_path / "skills.json"
    skills = SkillLibrary(state_path=path)
    skills.record_result("scroll_down", success=True)
    assert path.exists()
    restored = SkillLibrary(state_path=path)
    assert restored.procedures["scroll_down"].stats.successes >= 1
