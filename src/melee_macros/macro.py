"""Macro model: an author-friendly timeline builder that compiles to an
explicit per-frame list of :class:`ControllerState`.

Frame convention (0-indexed):
    Frame 0 is the first frame the macro is applied. The research docs use a
    1-indexed convention where "frame 1 = jump press, airborne on frame 4"
    (3-frame jumpsquat). Here that maps to: jump on frame 0, jumpsquat on
    frames 0/1/2, airborne on frame 3. So an action the research places on
    "frame N" goes on builder frame N-1.
"""

from __future__ import annotations

from dataclasses import dataclass

from .inputs import NEUTRAL, ControllerState, unit_to_pipe


@dataclass
class _ButtonHold:
    button: str
    start: int
    end: int  # exclusive


@dataclass
class _StickHold:
    which: str  # "main" or "c"
    x: float
    y: float
    start: int
    end: int  # exclusive


@dataclass
class _TriggerHold:
    side: str  # "l" or "r"
    value: float
    start: int
    end: int  # exclusive


class MacroBuilder:
    """Declarative builder. Author in unit coords (-1..+1, +up); compiles to
    pipe-convention per-frame states."""

    def __init__(self, name: str, description: str = "", *, character: str = "fox"):
        self.name = name
        self.description = description
        self.character = character
        self._buttons: list[_ButtonHold] = []
        self._sticks: list[_StickHold] = []
        self._triggers: list[_TriggerHold] = []
        self._explicit_len: int | None = None

    # --- digital buttons -------------------------------------------------
    def hold(self, button: str, start: int, end: int) -> "MacroBuilder":
        self._buttons.append(_ButtonHold(button, start, end))
        return self

    def tap(self, button: str, at: int, dur: int = 1) -> "MacroBuilder":
        return self.hold(button, at, at + dur)

    # --- analog sticks (unit coords) ------------------------------------
    def main(self, x: float, y: float, start: int, end: int) -> "MacroBuilder":
        self._sticks.append(_StickHold("main", x, y, start, end))
        return self

    def main_at(self, x: float, y: float, at: int, dur: int = 1) -> "MacroBuilder":
        return self.main(x, y, at, at + dur)

    def cstick(self, x: float, y: float, start: int, end: int) -> "MacroBuilder":
        self._sticks.append(_StickHold("c", x, y, start, end))
        return self

    def cstick_at(self, x: float, y: float, at: int, dur: int = 1) -> "MacroBuilder":
        return self.cstick(x, y, at, at + dur)

    # --- analog triggers (0..1) -----------------------------------------
    def trigger(self, side: str, value: float, start: int, end: int) -> "MacroBuilder":
        self._triggers.append(_TriggerHold(side, value, start, end))
        return self

    def pad_to(self, length: int) -> "MacroBuilder":
        """Force the macro to be at least `length` frames (trailing neutral)."""
        self._explicit_len = length
        return self

    # --- compile ---------------------------------------------------------
    def _length(self) -> int:
        end = 0
        for h in self._buttons:
            end = max(end, h.end)
        for s in self._sticks:
            end = max(end, s.end)
        for t in self._triggers:
            end = max(end, t.end)
        if self._explicit_len is not None:
            end = max(end, self._explicit_len)
        return end

    def build(self) -> "Macro":
        length = self._length()
        frames: list[ControllerState] = []
        for f in range(length):
            buttons = frozenset(
                h.button for h in self._buttons if h.start <= f < h.end
            )
            main = (NEUTRAL, NEUTRAL)
            c = (NEUTRAL, NEUTRAL)
            for s in self._sticks:  # later events win on overlap
                if s.start <= f < s.end:
                    px, py = unit_to_pipe(s.x), unit_to_pipe(s.y)
                    if s.which == "main":
                        main = (px, py)
                    else:
                        c = (px, py)
            l = r = 0.0
            for t in self._triggers:
                if t.start <= f < t.end:
                    if t.side == "l":
                        l = t.value
                    else:
                        r = t.value
            frames.append(ControllerState(buttons=buttons, main=main, c=c, l=l, r=r))
        return Macro(self.name, self.description, frames, character=self.character)


@dataclass
class Macro:
    name: str
    description: str
    frames: list[ControllerState]
    character: str = "fox"

    def __len__(self) -> int:
        return len(self.frames)

    def player(self) -> "MacroPlayer":
        return MacroPlayer(self)


class MacroPlayer:
    """Stateful cursor that yields one frame per `advance()` call."""

    def __init__(self, macro: Macro):
        self.macro = macro
        self._i = 0

    @property
    def name(self) -> str:
        return self.macro.name

    @property
    def done(self) -> bool:
        return self._i >= len(self.macro.frames)

    def advance(self, view=None) -> ControllerState:
        # `view` is accepted for interface parity with ReactivePlayer; fixed
        # timelines ignore it.
        state = self.macro.frames[self._i]
        self._i += 1
        return state
