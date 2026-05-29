"""Main loop: read the physical pad, pass inputs through to Dolphin, and when a
trigger button/combo fires, override passthrough with a macro until it finishes.

Because this program is the *sole* input source Dolphin sees (the GCN port is
set to the pipe device), normal play flows through passthrough; macros simply
take over the output for their duration.
"""

from __future__ import annotations

from dataclasses import dataclass

from .backends import Backend
from .controller import ControllerReader, PhysicalState
from .gamestate import GameView, REQUIRE_PREDICATES
from .inputs import DIGITAL_BUTTONS, ControllerState
from .library import MacroLibrary
from .macro import MacroPlayer
from .reactive import BOT_LIKE, MacroContext, ReactivePlayer, get_reactive


@dataclass
class TriggerBinding:
    buttons: frozenset[str]  # logical names that must all be held
    macro: str
    stick: str | None = None  # optional: "left"/"right"/"up"/"down" on the main stick
    stick_threshold: float = 0.5  # deflection fraction (0.5 -> past the 3/4 mark)
    requires: str | None = None  # optional game-state gate (see REQUIRE_PREDICATES)

    def state_ok(self, view: GameView | None) -> bool:
        """True if the game-state gate passes (or can't be checked / isn't set)."""
        if self.requires is None or view is None:
            return True  # no gate, or open-loop mode -> best-effort allow
        pred = REQUIRE_PREDICATES.get(self.requires)
        return pred(view) if pred else True

    def satisfied(self, phys: PhysicalState) -> bool:
        if not (self.buttons <= phys.buttons):
            return False
        if self.stick is None:
            return True
        # phys.main is pipe convention: 0..1, 0.5 center, up = 1.0.
        x, y = phys.main
        dx, dy = x - 0.5, y - 0.5
        m = self.stick_threshold / 2.0  # 0..0.5 deflection from center
        if self.stick == "right":
            return dx > m and abs(dx) >= abs(dy)
        if self.stick == "left":
            return dx < -m and abs(dx) >= abs(dy)
        if self.stick == "up":
            return dy > m and abs(dy) >= abs(dx)
        if self.stick == "down":
            return dy < -m and abs(dy) >= abs(dx)
        return False

    @property
    def specificity(self) -> int:
        """More-specific bindings win: count buttons, plus 1 for a stick req."""
        return len(self.buttons) + (1 if self.stick else 0)


def passthrough_state(phys: PhysicalState) -> ControllerState:
    buttons = frozenset(b for b in phys.buttons if b in DIGITAL_BUTTONS)
    return ControllerState(buttons=buttons, main=phys.main, c=phys.c, l=phys.l, r=phys.r)


class Engine:
    def __init__(
        self,
        backend: Backend,
        reader: ControllerReader,
        library: MacroLibrary,
        triggers: list[TriggerBinding],
        *,
        passthrough: bool = True,
        on_event=None,
        debug: bool = False,
        reactive: bool = True,
        reactive_edgeguard: bool = False,
    ):
        self.backend = backend
        self.reader = reader
        self.library = library
        # Most-specific first so "MOD+stick" or "L+A" wins over a bare "A".
        self.triggers = sorted(triggers, key=lambda t: -t.specificity)
        self.passthrough = passthrough
        self.on_event = on_event or (lambda *a: None)
        self.debug = debug
        # Prefer closed-loop macros when a live GameView is available.
        self.reactive = reactive
        self.reactive_edgeguard = reactive_edgeguard
        self._active = None  # MacroPlayer | ReactivePlayer | None
        self._prev_satisfied: dict[int, bool] = {}
        self._dbg_last: tuple | None = None
        self._prev_opp_off = False  # for auto-edgeguard rising-edge detection

    def _reactive_usable(self, name: str, view: GameView | None) -> bool:
        """True if the closed-loop version of `name` can run this frame."""
        return (
            self.reactive
            and view is not None
            and get_reactive(name) is not None
            and (name not in BOT_LIKE or self.reactive_edgeguard)
        )

    def _playable(self, name: str, view: GameView | None) -> bool:
        """True if SOME player can be built for `name` right now.

        A fixed-library macro is always playable. A reactive-only macro (no
        fixed timeline) is playable only when its closed-loop version is usable
        — otherwise firing it would crash with no fallback timeline.
        """
        return name in self.library or self._reactive_usable(name, view)

    def _make_player(self, name: str, view: GameView | None):
        """Pick the closed-loop player when possible, else the fixed timeline."""
        if self._reactive_usable(name, view):
            ctx = MacroContext(view=view, facing_right=view.facing_right)
            return ReactivePlayer(name, get_reactive(name), ctx)
        return self.library.get(name).player()

    def _fired_macro(self, phys: PhysicalState, view: GameView | None) -> str | None:
        """Return a macro name on the rising edge of any trigger binding.

        A binding only fires if its button/stick condition rises, a usable
        player exists for it this frame, AND its optional game-state gate
        (`requires`) passes.
        """
        fired = None
        for i, t in enumerate(self.triggers):
            now = t.satisfied(phys)
            was = self._prev_satisfied.get(i, False)
            if (
                now and not was and fired is None
                and self._playable(t.macro, view) and t.state_ok(view)
            ):
                fired = t.macro
            self._prev_satisfied[i] = now
        return fired

    AUTO_EDGEGUARD = "reactive_edgeguard"

    def _auto_edgeguard(self, view: GameView | None) -> str | None:
        """Auto-fire the reactive edgeguard the moment the opponent goes
        off-stage (rising edge), with no button press.

        Only active when `reactive_edgeguard` is enabled AND we have live state.
        Gated on being grounded ourselves so it doesn't hijack your own
        recovery, and edge-triggered so it fires once per opponent trip
        off-stage rather than every frame.
        """
        if not (self.reactive_edgeguard and view is not None):
            self._prev_opp_off = False
            return None
        opp_off = bool(view.opp_present and view.opp_off_stage)
        rising = opp_off and not self._prev_opp_off
        self._prev_opp_off = opp_off
        # Don't grab control unless we're grounded and able to act.
        if rising and view.on_ground and self._playable(self.AUTO_EDGEGUARD, view):
            return self.AUTO_EDGEGUARD
        return None

    def step(self) -> ControllerState:
        """Produce one frame of output. Call once per game frame."""
        phys = self.reader.poll()
        view = self.backend.gamestate()

        if self.debug:
            raw = tuple(self.reader.raw_buttons())
            snap = (raw, tuple(phys.buttons), phys.main)
            if snap != self._dbg_last:
                extra = ""
                if view is not None:
                    extra = f"  state={view.action}@{view.action_frame} ground={view.on_ground}"
                self.on_event(
                    "debug",
                    f"raw_buttons={list(raw)}  logical={sorted(phys.buttons)}  "
                    f"main=({phys.main[0]:.2f},{phys.main[1]:.2f}){extra}",
                )
                self._dbg_last = snap

        if self._active is not None and not self._active.done:
            state = self._active.advance(view)
            if self._active.done:
                self.on_event("macro_end", self._active.name)
                self._active = None
            return state

        self._active = None
        # Explicit button/stick triggers win; otherwise the auto-edgeguard may
        # fire on the rising edge of the opponent going off-stage.
        fired = self._fired_macro(phys, view) or self._auto_edgeguard(view)
        if fired is not None:
            self.on_event("macro_start", fired)
            self._active = self._make_player(fired, view)
            return self._active.advance(view)

        if self.passthrough:
            return passthrough_state(phys)
        return ControllerState()

    def run(self) -> None:
        # Open the controller/window FIRST so it appears immediately. Opening a
        # pipe backend blocks until Dolphin connects to the read end, so doing
        # it first would hang with no window and no feedback.
        self.reader.open()
        self.on_event("ready", self.reader.name)
        self.on_event("waiting", None)
        self.backend.open()
        self.on_event("connected", None)
        try:
            while True:
                self.backend.wait_frame()
                self.backend.send(self.step())
        except KeyboardInterrupt:
            self.on_event("stop", None)
        finally:
            self.reader.close()
            self.backend.close()
