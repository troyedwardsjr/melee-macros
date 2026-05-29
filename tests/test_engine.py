"""Engine wiring smoke tests — no pygame/Dolphin required."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from melee_macros import build_fox_library
from melee_macros.controller import PhysicalState
from melee_macros.engine import Engine, TriggerBinding, passthrough_state
from melee_macros.inputs import ControllerState


class StubReader:
    """Feeds a scripted list of PhysicalState snapshots, one per frame."""

    def __init__(self, script):
        self.script = list(script)
        self._i = 0
        self.name = "stub"

    def open(self):
        pass

    def close(self):
        pass

    def poll(self):
        s = self.script[min(self._i, len(self.script) - 1)]
        self._i += 1
        return s


class NullBackend:
    def open(self):
        pass

    def wait_frame(self):
        pass

    def send(self, state):
        pass

    def gamestate(self):
        return None  # open-loop: no live game state

    def close(self):
        pass


def make_engine(script, triggers):
    return Engine(NullBackend(), StubReader(script), build_fox_library(), triggers)


def test_passthrough_filters_non_game_buttons():
    phys = PhysicalState(buttons=frozenset({"A", "MOD"}), main=(0.1, 0.9))
    out = passthrough_state(phys)
    assert "A" in out.buttons
    assert "MOD" not in out.buttons  # MOD is macro-only
    assert out.main == (0.1, 0.9)


def test_single_button_trigger_plays_full_macro():
    lib = build_fox_library()
    wd = lib.get("wavedash_forward")
    neutral = PhysicalState()
    pressed = PhysicalState(buttons=frozenset({"D_RIGHT"}))
    # frame 0 neutral (establish edge baseline), then press, then hold neutral long enough
    script = [neutral, pressed] + [neutral] * (len(wd) + 2)
    eng = make_engine(script, [TriggerBinding(frozenset({"D_RIGHT"}), "wavedash_forward")])

    eng.step()  # frame 0: nothing
    fired = [eng.step() for _ in range(len(wd))]  # should be the full macro
    assert fired == wd.frames, "macro frames did not play back verbatim"
    # after macro, passthrough resumes
    after = eng.step()
    assert after == ControllerState()


def test_combo_priority_over_single():
    triggers = [
        TriggerBinding(frozenset({"A"}), "short_hop"),
        TriggerBinding(frozenset({"MOD", "A"}), "jc_grab"),
    ]
    combo = PhysicalState(buttons=frozenset({"MOD", "A"}))
    script = [PhysicalState(), combo] + [PhysicalState()] * 10
    eng = make_engine(script, triggers)
    eng.step()  # baseline
    first = eng.step()  # combo frame -> jc_grab f0 = jump (Y)
    jc = build_fox_library().get("jc_grab")
    assert first == jc.frames[0]


def test_no_retrigger_while_macro_active():
    # Holding the trigger should not restart the macro mid-playback.
    lib = build_fox_library()
    name = "shine"
    held = PhysicalState(buttons=frozenset({"D_DOWN"}))
    script = [PhysicalState()] + [held] * 20
    eng = make_engine(script, [TriggerBinding(frozenset({"D_DOWN"}), name)])
    eng.step()  # baseline neutral
    frames = [eng.step() for _ in range(len(lib.get(name)))]
    assert frames == lib.get(name).frames


if __name__ == "__main__":
    import traceback

    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS {t.__name__}")
        except Exception:
            failed += 1
            print(f"FAIL {t.__name__}")
            traceback.print_exc()
    print(f"\n{len(tests) - failed}/{len(tests)} passed.")
    raise SystemExit(1 if failed else 0)
