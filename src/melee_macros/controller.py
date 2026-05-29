"""Physical controller reader (SDL via pygame).

Reads any SDL-visible pad — GameCube adapter, Switch Pro, Xbox, DualShock,
generic USB — and normalizes it into pipe-convention axes plus a set of
*logical* button names. Because raw button/axis indices differ across pads,
the index->logical-name mapping lives in config (see config.yaml ->
``controller``).

pygame is imported lazily so the rest of the package (macro compilation,
tests) works without it installed.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field


@dataclass
class ControllerMap:
    index: int = 0
    deadzone: float = 0.15
    # SDL axis index -> role
    axes: dict[str, int] = field(
        default_factory=lambda: {
            "main_x": 0,
            "main_y": 1,
            "c_x": 2,
            "c_y": 3,
            "l_trigger": 4,
            "r_trigger": 5,
        }
    )
    # SDL button index -> logical name
    buttons: dict[int, str] = field(default_factory=dict)
    # invert per-axis if a pad reports flipped values
    invert: dict[str, bool] = field(
        default_factory=lambda: {"main_y": True, "c_y": True}
    )
    trigger_min: float = -1.0  # SDL value at rest for trigger axes
    trigger_max: float = 1.0  # SDL value fully pressed


@dataclass
class PhysicalState:
    """Normalized snapshot of the physical pad, in pipe convention."""

    buttons: frozenset[str] = frozenset()
    main: tuple[float, float] = (0.5, 0.5)
    c: tuple[float, float] = (0.5, 0.5)
    l: float = 0.0
    r: float = 0.0


def _apply_deadzone(v: float, dz: float) -> float:
    """v in [-1,1] -> [-1,1] with a radial deadzone, then ready for pipe map."""
    if abs(v) < dz:
        return 0.0
    return v


def _axis_to_pipe(v: float, invert: bool, dz: float) -> float:
    v = _apply_deadzone(v, dz)
    if invert:
        v = -v
    return max(0.0, min(1.0, (v + 1.0) / 2.0))


def list_joysticks() -> list[str]:
    """Return the names of all SDL-visible joysticks/controllers, by index."""
    os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
    import pygame  # lazy: optional dependency

    pygame.init()
    pygame.joystick.init()
    names = []
    for i in range(pygame.joystick.get_count()):
        js = pygame.joystick.Joystick(i)
        js.init()
        names.append(js.get_name())
    return names


class ControllerReader:
    def __init__(self, mapping: ControllerMap):
        self.map = mapping
        self._js = None
        self._pygame = None

    def open(self) -> None:
        import pygame  # lazy: optional dependency

        self._pygame = pygame
        pygame.init()
        # macOS only delivers controller events when there is a real, VISIBLE
        # window whose Cocoa event queue is drained via event.get(). A hidden or
        # dummy/headless window gets zero input — so open a small visible one and
        # keep it up for the life of the engine.
        try:
            pygame.display.set_mode((220, 60))
            pygame.display.set_caption("melee-macros running — keep this window open")
        except pygame.error:
            pass
        pygame.joystick.init()
        if pygame.joystick.get_count() == 0:
            raise RuntimeError("no SDL joystick/controller detected")
        self._js = pygame.joystick.Joystick(self.map.index)
        self._js.init()

    @property
    def name(self) -> str:
        return self._js.get_name() if self._js else "<none>"

    def _axis(self, role: str) -> float:
        idx = self.map.axes.get(role)
        if idx is None or idx >= self._js.get_numaxes():
            return 0.0
        return self._js.get_axis(idx)

    def poll(self) -> PhysicalState:
        if self._js is None:
            raise RuntimeError("controller not open")
        # event.get() (not pump()) is required on macOS to refresh joystick state.
        self._pygame.event.get()
        dz = self.map.deadzone

        main = (
            _axis_to_pipe(self._axis("main_x"), self.map.invert.get("main_x", False), dz),
            _axis_to_pipe(self._axis("main_y"), self.map.invert.get("main_y", True), dz),
        )
        c = (
            _axis_to_pipe(self._axis("c_x"), self.map.invert.get("c_x", False), dz),
            _axis_to_pipe(self._axis("c_y"), self.map.invert.get("c_y", True), dz),
        )

        def trig(role: str) -> float:
            raw = self._axis(role)
            span = self.map.trigger_max - self.map.trigger_min
            if span == 0:
                return 0.0
            return max(0.0, min(1.0, (raw - self.map.trigger_min) / span))

        l = trig("l_trigger")
        r = trig("r_trigger")

        pressed: set[str] = set()
        for sdl_idx, logical in self.map.buttons.items():
            if sdl_idx < self._js.get_numbuttons() and self._js.get_button(sdl_idx):
                pressed.add(logical)

        # D-pad via hat 0 if present.
        if self._js.get_numhats() > 0:
            hx, hy = self._js.get_hat(0)
            if hx < 0:
                pressed.add("D_LEFT")
            elif hx > 0:
                pressed.add("D_RIGHT")
            if hy > 0:
                pressed.add("D_UP")
            elif hy < 0:
                pressed.add("D_DOWN")

        return PhysicalState(buttons=frozenset(pressed), main=main, c=c, l=l, r=r)

    def raw_buttons(self) -> list[int]:
        """Currently-pressed RAW SDL button indices (for --debug / mapping)."""
        if self._js is None:
            return []
        return [i for i in range(self._js.get_numbuttons()) if self._js.get_button(i)]

    def close(self) -> None:
        if self._pygame is not None:
            self._pygame.joystick.quit()
            self._pygame.quit()
