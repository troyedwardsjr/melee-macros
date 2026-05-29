"""Frame-level controller state and the Dolphin pipe coordinate convention.

Coordinate convention (matches libmelee / Dolphin pipe input):
    Analog axes are in [0.0, 1.0] with 0.5 = neutral.
    MAIN/C x: 0.0 = left, 1.0 = right.
    MAIN/C y: 0.0 = down, 1.0 = up.
    Triggers (l, r): 0.0 = released, 1.0 = fully pressed.

Macros are authored in the "unit" convention (-1.0 .. +1.0, 0.0 = neutral,
+y = up) because that matches how the research frame data is written. Use
`unit_to_pipe` to convert.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace

# Digital buttons accepted by Dolphin's pipe input device.
DIGITAL_BUTTONS = frozenset(
    {"A", "B", "X", "Y", "Z", "START", "L", "R", "D_UP", "D_DOWN", "D_LEFT", "D_RIGHT"}
)

NEUTRAL = 0.5


def unit_to_pipe(v: float) -> float:
    """Convert a unit axis value (-1..+1, +up) to pipe convention (0..1, 0.5 center)."""
    return max(0.0, min(1.0, 0.5 + v / 2.0))


def pipe_clamp(v: float) -> float:
    return max(0.0, min(1.0, v))


@dataclass(frozen=True)
class ControllerState:
    """One frame of controller output, in Dolphin pipe convention."""

    buttons: frozenset[str] = frozenset()
    main: tuple[float, float] = (NEUTRAL, NEUTRAL)
    c: tuple[float, float] = (NEUTRAL, NEUTRAL)
    l: float = 0.0
    r: float = 0.0

    def with_button(self, name: str, pressed: bool) -> "ControllerState":
        if name not in DIGITAL_BUTTONS:
            raise ValueError(f"unknown button {name!r}")
        if pressed:
            return replace(self, buttons=self.buttons | {name})
        return replace(self, buttons=self.buttons - {name})


NEUTRAL_STATE = ControllerState()
