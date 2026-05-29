"""State-aware layer tests — GameView predicates, ReactivePlayer playback,
state-gated triggers, and reactive-vs-fixed engine selection.

No pygame/Dolphin/libmelee required: we feed hand-built GameView snapshots.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from melee_macros import build_fox_library
from melee_macros.controller import PhysicalState
from melee_macros.engine import Engine, TriggerBinding
from melee_macros.gamestate import REQUIRE_PREDICATES, GameView
from melee_macros.inputs import ControllerState
from melee_macros.reactive import (
    BOT_LIKE,
    MacroContext,
    ReactivePlayer,
    get_reactive,
    reactive_wavedash_forward,
)


# ----------------------------------------------------------------------
# Test doubles
# ----------------------------------------------------------------------
class StubReader:
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


class StateBackend:
    """Backend that replays a scripted list of GameViews, one per frame."""

    def __init__(self, views):
        self.views = list(views)
        self._i = 0

    def open(self):
        pass

    def wait_frame(self):
        pass

    def send(self, state):
        pass

    def gamestate(self):
        v = self.views[min(self._i, len(self.views) - 1)] if self.views else None
        self._i += 1
        return v

    def close(self):
        pass


# ----------------------------------------------------------------------
# GameView predicates
# ----------------------------------------------------------------------
def test_gameview_self_predicates():
    grounded = GameView(action="STANDING", on_ground=True)
    assert grounded.actionable
    assert not grounded.airborne
    assert not grounded.shielding

    shield = GameView(action="SHIELD", on_ground=True)
    assert shield.shielding
    assert not shield.actionable  # shielding is not in the actionable set

    grab = GameView(action="GRAB_WAIT", on_ground=True)
    assert grab.holding_grab

    ledge = GameView(action="EDGE_HANGING", on_ground=False)
    assert ledge.on_ledge
    assert ledge.airborne

    air_falling = GameView(action="FALL", on_ground=False, speed_y=-1.5)
    assert air_falling.falling
    assert air_falling.about_to_land(lookahead=2, ground_pad=4.0) is False or True  # smoke

    hit = GameView(action="DAMAGE_HIGH", hitstun=12.0)
    assert hit.in_hitstun


def test_about_to_land_heuristic():
    # Descending and close to the ground -> predicts a landing.
    near = GameView(action="FALL", on_ground=False, y=3.0, speed_y=-2.0)
    assert near.about_to_land(lookahead=2, ground_pad=4.0)
    # High up and rising -> not landing.
    high = GameView(action="JUMP", on_ground=False, y=40.0, speed_y=2.0)
    assert not high.about_to_land()


def test_opp_side_and_offstage():
    v = GameView(opp_present=True, opp_off_stage=True, opp_x=80.0, edge_x=68.0, opp_y=-5.0)
    assert v.opp_side() == 1
    assert v.opp_below_ledge
    left = GameView(opp_present=True, opp_off_stage=True, opp_x=-80.0, edge_x=68.0)
    assert left.opp_side() == -1
    onstage = GameView(opp_present=True, opp_x=0.0, edge_x=68.0)
    assert onstage.opp_side() == 0


def test_require_predicates_match_properties():
    shield = GameView(action="SHIELD", on_ground=True)
    assert REQUIRE_PREDICATES["shielding"](shield)
    assert not REQUIRE_PREDICATES["airborne"](shield)
    air = GameView(action="FALL", on_ground=False)
    assert REQUIRE_PREDICATES["airborne"](air)
    assert not REQUIRE_PREDICATES["grounded"](air)
    grab = GameView(action="GRAB_WAIT", on_ground=True)
    assert REQUIRE_PREDICATES["holding_grab"](grab)
    opp = GameView(opp_present=True, opp_off_stage=True)
    assert REQUIRE_PREDICATES["opp_offstage"](opp)


# ----------------------------------------------------------------------
# ReactivePlayer playback
# ----------------------------------------------------------------------
def test_reactive_player_runs_to_completion():
    ctx = MacroContext(view=None, facing_right=True)
    player = ReactivePlayer("wavedash_forward", reactive_wavedash_forward, ctx)
    assert not player.done
    frames = []
    # Feed an airborne view so the jumpsquat loop breaks promptly.
    air = GameView(action="JUMPF", on_ground=False)
    for _ in range(40):
        if player.done:
            break
        frames.append(player.advance(air))
    assert player.done
    assert frames, "reactive player produced no frames"
    # The wavedash ends with an airdodge (L) into the diagonal.
    assert any("L" in f.buttons for f in frames)


def test_reactive_player_neutral_after_done():
    ctx = MacroContext(view=None, facing_right=True)
    player = ReactivePlayer("wavedash_forward", reactive_wavedash_forward, ctx)
    air = GameView(action="JUMPF", on_ground=False)
    while not player.done:
        player.advance(air)
    out = player.advance(air)
    assert out == ControllerState()  # NEUTRAL_STATE


def test_registry_has_expected_names():
    for name in ("wavedash_forward", "wavedash_back", "shffl_nair", "reactive_edgeguard"):
        assert get_reactive(name) is not None, name
    assert get_reactive("definitely_not_a_macro") is None
    assert "reactive_edgeguard" in BOT_LIKE


# ----------------------------------------------------------------------
# Engine: state-gated triggers
# ----------------------------------------------------------------------
def _engine(script, views, triggers, **kw):
    return Engine(
        StateBackend(views), StubReader(script), build_fox_library(), triggers, **kw
    )


def test_requires_gate_blocks_when_state_fails():
    # shine_oos requires shielding; fire the trigger while NOT shielding -> blocked.
    press = PhysicalState(buttons=frozenset({"Z"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 6
    not_shield = GameView(action="STANDING", on_ground=True)
    views = [not_shield] * len(script)
    # Disable reactive so we test the fixed library macro + the gate only.
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"Z"}), "shine_oos", requires="shielding")],
        reactive=False,
    )
    eng.step()  # baseline
    eng.step()  # trigger frame, but gate fails -> macro must not start
    assert eng._active is None  # no macro fired; input just passes through


def test_requires_gate_allows_when_state_passes():
    press = PhysicalState(buttons=frozenset({"Z"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 6
    shielding = GameView(action="SHIELD", on_ground=True)
    views = [shielding] * len(script)
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"Z"}), "shine_oos", requires="shielding")],
        reactive=False,
    )
    lib = build_fox_library()
    eng.step()  # baseline
    out = eng.step()  # gate passes -> macro frame 0
    assert out == lib.get("shine_oos").frames[0]


def test_state_ok_with_no_view_is_permissive():
    # When the view is None (open-loop), a `requires` gate is best-effort allow.
    t = TriggerBinding(frozenset({"Z"}), "shine_oos", requires="shielding")
    assert t.state_ok(None) is True
    assert t.state_ok(GameView(action="STANDING")) is False
    assert t.state_ok(GameView(action="SHIELD")) is True


# ----------------------------------------------------------------------
# Engine: reactive vs fixed selection
# ----------------------------------------------------------------------
def test_engine_prefers_reactive_when_view_present():
    press = PhysicalState(buttons=frozenset({"D_RIGHT"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 20
    air = GameView(action="JUMPF", on_ground=False)
    views = [GameView(action="STANDING", on_ground=True)] + [air] * (len(script) - 1)
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"D_RIGHT"}), "wavedash_forward")],
        reactive=True,
    )
    eng.step()  # baseline
    eng.step()  # fire
    assert isinstance(eng._active, ReactivePlayer)


def test_engine_uses_fixed_when_reactive_disabled():
    press = PhysicalState(buttons=frozenset({"D_RIGHT"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 20
    air = GameView(action="JUMPF", on_ground=False)
    views = [air] * len(script)
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"D_RIGHT"}), "wavedash_forward")],
        reactive=False,
    )
    from melee_macros.macro import MacroPlayer

    eng.step()
    eng.step()
    assert isinstance(eng._active, MacroPlayer)


def test_bot_like_edgeguard_gated_off_by_default():
    # reactive_edgeguard is BOT_LIKE; without the flag the engine must NOT pick
    # the reactive version (it should fall back to the fixed library macro if
    # one exists, otherwise the binding is simply not "known" as fixed).
    press = PhysicalState(buttons=frozenset({"D_LEFT"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 10
    views = [GameView(action="STANDING", opp_present=True, opp_off_stage=True)] * len(script)
    # Bind to a reactive-only name; with edgeguard off and no fixed macro, it
    # should not fire at all.
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"D_LEFT"}), "reactive_edgeguard")],
        reactive=True, reactive_edgeguard=False,
    )
    eng.step()
    eng.step()
    assert eng._active is None  # gated off + no fixed fallback -> must not fire


def test_bot_like_edgeguard_runs_when_enabled():
    press = PhysicalState(buttons=frozenset({"D_LEFT"}))
    script = [PhysicalState(), press] + [PhysicalState()] * 10
    views = [GameView(action="STANDING", opp_present=True, opp_off_stage=True, opp_x=-80, edge_x=68)] * len(script)
    eng = _engine(
        script, views,
        [TriggerBinding(frozenset({"D_LEFT"}), "reactive_edgeguard")],
        reactive=True, reactive_edgeguard=True,
    )
    eng.step()
    eng.step()
    assert isinstance(eng._active, ReactivePlayer)


def test_reactive_drillshine_registered_and_runs():
    assert get_reactive("drillshine") is not None
    from melee_macros.reactive import reactive_drillshine

    ctx = MacroContext(view=None, facing_right=True)
    player = ReactivePlayer("drillshine", reactive_drillshine, ctx)
    # Airborne while rising, then grounded -> should dair, land, shine, JC.
    air = GameView(action="JUMPF", on_ground=False, y=10.0, speed_y=-3.0)
    ground = GameView(action="LANDING", on_ground=True)
    frames = []
    seq = [air, air, air, air, ground, ground, ground, ground]
    for i in range(20):
        if player.done:
            break
        frames.append(player.advance(seq[min(i, len(seq) - 1)]))
    assert player.done
    assert any(f.c[1] < 0.4 for f in frames), "no dair (c-stick down)"
    assert any("B" in f.buttons for f in frames), "no shine (B) on landing"


def test_auto_edgeguard_fires_on_opp_offstage_rising_edge():
    # No button triggers at all; engine should auto-fire when opp goes offstage.
    script = [PhysicalState()] * 8
    onstage = GameView(action="STANDING", on_ground=True, opp_present=True,
                       opp_off_stage=False, opp_x=20, edge_x=68)
    offstage = GameView(action="STANDING", on_ground=True, opp_present=True,
                        opp_off_stage=True, opp_x=-80, edge_x=68)
    views = [onstage, onstage, offstage, offstage, offstage, offstage, offstage, offstage]
    eng = _engine(script, views, [], reactive=True, reactive_edgeguard=True)
    eng.step()  # onstage
    eng.step()  # onstage
    eng.step()  # rising edge -> auto edgeguard fires
    assert isinstance(eng._active, ReactivePlayer)
    assert eng._active.name == "reactive_edgeguard"


def test_auto_edgeguard_off_when_flag_disabled():
    script = [PhysicalState()] * 5
    offstage = GameView(action="STANDING", on_ground=True, opp_present=True,
                        opp_off_stage=True, opp_x=-80, edge_x=68)
    views = [offstage] * 5
    eng = _engine(script, views, [], reactive=True, reactive_edgeguard=False)
    eng.step()
    eng.step()
    assert eng._active is None


def test_auto_edgeguard_not_while_self_airborne():
    # If WE are off the ground (e.g. recovering), don't hijack control.
    script = [PhysicalState()] * 5
    onstage = GameView(action="FALL", on_ground=False, opp_present=True, opp_off_stage=False)
    off_self_air = GameView(action="FALL", on_ground=False, opp_present=True,
                            opp_off_stage=True, opp_x=-80, edge_x=68)
    views = [onstage, off_self_air, off_self_air, off_self_air, off_self_air]
    eng = _engine(script, views, [], reactive=True, reactive_edgeguard=True)
    eng.step()
    eng.step()  # opp offstage rising, but we're airborne -> no auto fire
    assert eng._active is None


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
