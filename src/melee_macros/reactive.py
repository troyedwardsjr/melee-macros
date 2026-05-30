"""Closed-loop (state-reading) macros.

A *reactive* macro is a Python generator that yields one
:class:`ControllerState` per game frame and inspects a shared
:class:`MacroContext` (carrying the current :class:`GameView`) at each resume.
That lets it branch on real game state — "airdodge on the first airborne
frame", "press L the frame before landing" — instead of guessing fixed frames.

The engine prefers a reactive version of a macro when (a) one is registered
here and (b) a live ``GameView`` is available (i.e. the libmelee backend is
running). Otherwise it falls back to the fixed timeline in ``macros/fox.py``,
so open-loop pipe mode keeps working unchanged.

Every loop here has a frame-count safety cap so a stalled/blank state can never
hang the engine — it just falls through to the next phase.
"""

from __future__ import annotations

from typing import Callable, Iterator, Optional

from .gamestate import GameView
from .inputs import ControllerState, NEUTRAL_STATE, unit_to_pipe

# Reusable unit-convention coordinates (-1..+1, +y = up).
_WD_FWD = (0.85, -0.50)
_WD_BACK = (-0.85, -0.50)
_DOWN = (0.0, -1.0)
_WL_RIGHT = (0.70, -0.70)
_WL_LEFT = (-0.70, -0.70)


def S(buttons=(), main=None, c=None, l: float = 0.0, r: float = 0.0) -> ControllerState:
    """Build a ControllerState from unit-convention sticks + digital buttons."""
    mp = (unit_to_pipe(main[0]), unit_to_pipe(main[1])) if main else (0.5, 0.5)
    cp = (unit_to_pipe(c[0]), unit_to_pipe(c[1])) if c else (0.5, 0.5)
    return ControllerState(buttons=frozenset(buttons), main=mp, c=cp, l=l, r=r)


class MacroContext:
    """Mutable per-playback context. The engine sets ``view`` each frame."""

    def __init__(self, view: Optional[GameView] = None, facing_right: bool = True):
        self.view = view
        self.facing_right = facing_right


# A reactive macro factory takes a context and returns a frame generator.
ReactiveFactory = Callable[[MacroContext], Iterator[ControllerState]]


class ReactivePlayer:
    """Drives a reactive generator, exposing the same surface as MacroPlayer."""

    def __init__(self, name: str, factory: ReactiveFactory, ctx: MacroContext):
        self.name = name
        self.ctx = ctx
        self._gen = factory(ctx)
        self._done = False

    @property
    def done(self) -> bool:
        return self._done

    def advance(self, view: Optional[GameView] = None) -> ControllerState:
        self.ctx.view = view
        if self._done:
            return NEUTRAL_STATE
        try:
            return next(self._gen)
        except StopIteration:
            self._done = True
            return NEUTRAL_STATE


# ======================================================================
# Closed-loop movement
# ======================================================================
def _wavedash(ctx: MacroContext, diag) -> Iterator[ControllerState]:
    # f0: jump while already holding the down-diagonal so the airdodge angle is set.
    yield S(buttons={"Y"}, main=diag)
    # Hold through jumpsquat until we actually leave the ground.
    for _ in range(10):
        v = ctx.view
        if v is None or v.airborne:
            break
        yield S(main=diag)
    # First airborne frame: airdodge into the ground at the diagonal -> wavedash.
    for _ in range(5):
        yield S(buttons={"L"}, main=diag)


def reactive_wavedash_forward(ctx):
    return _wavedash(ctx, _WD_FWD)


def reactive_wavedash_back(ctx):
    return _wavedash(ctx, _WD_BACK)


# ======================================================================
# Closed-loop SHFFL aerials (real-landing L-cancel)
# ======================================================================
def _aerial_inputs(aerial: str, facing_right: bool):
    """Return (buttons, cstick) for the given aerial."""
    fwd = 1.0 if facing_right else -1.0
    if aerial == "nair":
        return {"A"}, None
    if aerial == "uair":
        return set(), (0.0, 1.0)
    if aerial == "dair":
        return set(), (0.0, -1.0)
    if aerial == "fair":
        return set(), (fwd, 0.0)
    if aerial == "bair":
        return set(), (-fwd, 0.0)
    raise ValueError(aerial)


def _shffl(aerial: str):
    def factory(ctx: MacroContext) -> Iterator[ControllerState]:
        # Short hop.
        yield S(buttons={"Y"})
        # Wait until airborne.
        for _ in range(8):
            v = ctx.view
            if v is None or v.airborne:
                break
            yield S()
        # Throw the aerial (2 frames of input).
        btns, cs = _aerial_inputs(aerial, ctx.facing_right)
        yield S(buttons=btns, c=cs)
        yield S(buttons=btns, c=cs)
        # Fast-fall and L-cancel the frame(s) before the real landing.
        lcancelled = False
        for _ in range(45):
            v = ctx.view
            if v is None:
                # No state: best-effort fixed fall + a single L tap.
                yield S(main=_DOWN, l=1.0 if not lcancelled else 0.0)
                lcancelled = True
                continue
            if v.on_ground or v.landing:
                # Backstop: if we somehow never pre-pressed L, tap it now.
                if not lcancelled:
                    yield S(buttons={"L"}, main=_DOWN)
                break
            if v.about_to_land():
                lcancelled = True
                yield S(buttons={"L"}, main=_DOWN)  # L-cancel
            else:
                yield S(main=_DOWN)  # keep fast-falling

    return factory


def reactive_drillshine(ctx: MacroContext) -> Iterator[ControllerState]:
    """SH dair -> (real) landing -> shine -> jump-cancel, all state-driven.

    The fixed drillshine guesses the landing frame, so the dair/shine whiff if
    the hop timing is off. Here we watch the actual game state: dair out of a
    short hop, fast-fall + L-cancel the frame before the real landing, then
    shine (down-B) the instant we're grounded and jump-cancel it.
    """
    # Short hop.
    yield S(buttons={"Y"})
    # Wait until airborne.
    for _ in range(8):
        v = ctx.view
        if v is None or v.airborne:
            break
        yield S()
    # Throw the dair (c-stick down), 2 frames.
    yield S(c=(0.0, -1.0))
    yield S(c=(0.0, -1.0))
    # Fast-fall and L-cancel the frame before the real landing.
    grounded = False
    for _ in range(45):
        v = ctx.view
        if v is None:
            # No state: best-effort fixed fall, then bail to the shine phase.
            yield S(main=_DOWN, l=1.0)
            grounded = True
            break
        if v.on_ground or v.landing:
            grounded = True
            break
        if v.about_to_land():
            yield S(buttons={"L"}, main=_DOWN)  # L-cancel into the landing
        else:
            yield S(main=_DOWN)  # keep fast-falling
    if not grounded:
        return
    # On the ground: shine (down + B), hold a couple frames, then jump-cancel.
    yield S(buttons={"B"}, main=_DOWN)
    yield S(buttons={"B"}, main=_DOWN)
    yield S(buttons={"Y"})  # JC the shine so you can act/continue pressure


# ======================================================================
# Closed-loop ledgedash (anchored to the ledge-hang state)
# ======================================================================
def _ledgedash(stage_to_right: bool):
    toward = _WL_RIGHT if stage_to_right else _WL_LEFT
    away_x = -1.0 if stage_to_right else 1.0

    def factory(ctx: MacroContext) -> Iterator[ControllerState]:
        # Wait until we're actually hanging on the ledge.
        for _ in range(30):
            v = ctx.view
            if v is None or v.on_ledge:
                break
            yield S()
        # Drop off (push away from stage), then jump back toward it.
        yield S(main=(away_x, 0.0))
        yield S(buttons={"Y"}, main=(toward[0] * 0.4, 0.0))
        # Wait until airborne, then airdodge into the stage to waveland.
        for _ in range(8):
            v = ctx.view
            if v is None or v.airborne:
                break
            yield S(buttons={"Y"})
        for _ in range(4):
            yield S(buttons={"L"}, main=toward)

    return factory


def _ledgedash_jcshine(stage_to_right: bool):
    """Closed-loop high-intangibility ledgedash: like _ledgedash but inserts a
    JC-shine (shine -> jump-cancel) to extend the actionable intangible window
    before the waveland airdodge. Anchored to the real ledge-hang/airborne
    states so it self-corrects for ECB instead of guessing fixed frames."""
    toward = _WL_RIGHT if stage_to_right else _WL_LEFT
    away_x = -1.0 if stage_to_right else 1.0

    def factory(ctx: MacroContext) -> Iterator[ControllerState]:
        # Wait until we're actually hanging on the ledge.
        for _ in range(30):
            v = ctx.view
            if v is None or v.on_ledge:
                break
            yield S()
        # Drop off (push away from stage), then jump back toward it.
        yield S(main=(away_x, 0.0))
        yield S(buttons={"Y"}, main=(toward[0] * 0.4, 0.0))
        # Shine to extend intangibility, brief gap, then JC the shine.
        yield S(main=_DOWN, buttons={"B"})
        yield S()
        yield S(buttons={"Y"})
        # Wait until airborne, then airdodge into the stage to waveland.
        for _ in range(8):
            v = ctx.view
            if v is None or v.airborne:
                break
            yield S(buttons={"Y"})
        for _ in range(4):
            yield S(buttons={"L"}, main=toward)

    return factory


# ======================================================================
# Reactive (bot-like) edgeguard — reads the OPPONENT's state to pick a cover.
# Gated behind config `reactive_edgeguard: true` because auto-selecting and
# executing the kill from opponent state is autopilot, not execution assist.
# ======================================================================
def _ledgehog(ctx: MacroContext, toward_right: bool) -> Iterator[ControllerState]:
    # Dash to the ledge and drop/slide off to grab it (deny their recovery).
    x = 1.0 if toward_right else -1.0
    for _ in range(10):
        yield S(main=(x, 0.0))
        v = ctx.view
        if v is not None and v.on_ledge:
            return
    # Slide off into the ledge grab.
    for _ in range(6):
        yield S(main=(x, -0.2))


def _bair_offstage(ctx: MacroContext, toward_right: bool) -> Iterator[ControllerState]:
    # Turn toward the edge, short hop out, bair back inward.
    x = 1.0 if toward_right else -1.0
    yield S(buttons={"Y"}, main=(x, 0.0))
    for _ in range(6):
        v = ctx.view
        if v is None or v.airborne:
            break
        yield S(main=(x, 0.0))
    # bair = c-stick away from facing (we face the edge, so c-stick inward).
    cs = (-x, 0.0)
    yield S(c=cs)
    yield S(c=cs)
    for _ in range(6):
        yield S(main=(0.0, -1.0))  # fast fall back toward stage


def reactive_edgeguard(ctx: MacroContext) -> Iterator[ControllerState]:
    v = ctx.view
    if v is None or not (v.opp_present and v.opp_off_stage):
        return  # nothing to guard -> no-op
    side = v.opp_side()
    if side == 0:
        side = 1 if v.opp_x >= 0 else -1
    toward_right = side > 0
    if v.opp_below_ledge:
        # They're low: steal the ledge.
        yield from _ledgehog(ctx, toward_right)
    else:
        # They're high: contest with an offstage bair.
        yield from _bair_offstage(ctx, toward_right)


# ======================================================================
# Registry
# ======================================================================
# name -> reactive factory. Names mirror the fixed macros they upgrade.
REACTIVE: dict[str, ReactiveFactory] = {
    "wavedash_forward": reactive_wavedash_forward,
    "wavedash_back": reactive_wavedash_back,
    "shffl_nair": _shffl("nair"),
    "shffl_fair": _shffl("fair"),
    "shffl_bair": _shffl("bair"),
    "shffl_uair": _shffl("uair"),
    "shffl_dair": _shffl("dair"),
    "drillshine": reactive_drillshine,
    "ledgedash_stage_right": _ledgedash(True),
    "ledgedash_stage_left": _ledgedash(False),
    "ledgedash_jcshine_right": _ledgedash_jcshine(True),
    "ledgedash_jcshine_left": _ledgedash_jcshine(False),
    "reactive_edgeguard": reactive_edgeguard,
}

# Reactive macros that read the opponent's state (autopilot) — only enabled
# when config opts in via `reactive_edgeguard: true`.
BOT_LIKE = frozenset({"reactive_edgeguard"})


def get_reactive(name: str) -> Optional[ReactiveFactory]:
    return REACTIVE.get(name)
