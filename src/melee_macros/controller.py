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
    # Which reader to use: "sdl" (pygame; most pads) or "hid_gc" (raw HID for
    # the Mayflash GameCube adapter, which SDL can't parse on macOS).
    driver: str = "sdl"
    # For driver "sdl": SDL axis index -> role.
    # For driver "hid_gc": HID report BYTE index -> role.
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
    # For driver "sdl": SDL button index (int) -> logical name.
    # For driver "hid_gc": "byte.bit" string -> logical name.
    buttons: dict = field(default_factory=dict)
    # invert per-axis if a pad reports flipped values
    invert: dict[str, bool] = field(
        default_factory=lambda: {"main_y": True, "c_y": True}
    )
    trigger_min: float = -1.0  # SDL value at rest for trigger axes
    trigger_max: float = 1.0  # SDL value fully pressed
    # --- driver "hid_gc" only ---
    hid_vendor: int = 0x0079   # DragonRise / Mayflash adapter (PC mode)
    hid_product: int = 0       # 0 = any product for that vendor
    hid_interface: int = 0     # which adapter PORT (interface_number) to read
    hat_byte: int = 8          # report byte holding the D-pad hat nibble
    # Treat the analog L trigger as a SECOND macro modifier. When the L value
    # exceeds `l_mod_threshold`, emit the logical button `l_mod_name` (a
    # macro-only modifier — give it a name NOT in DIGITAL_BUTTONS so it never
    # reaches the game) and zero the analog L passthrough so the soft press
    # can't trigger shield/airdodge in-game. "" disables this.
    l_mod_name: str = ""
    l_mod_threshold: float = 0.3


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
        # SDL's dedicated HIDAPI driver for the Nintendo/Mayflash GameCube
        # adapter (used in "Wii U" mode, where the adapter reports a real
        # GameCube HID descriptor). Without it, the adapter's "PC/DInput" mode
        # enumerates on macOS with 0 axes/0 buttons. Must be set before init.
        os.environ.setdefault("SDL_JOYSTICK_HIDAPI", "1")
        os.environ.setdefault("SDL_JOYSTICK_HIDAPI_GAMECUBE", "1")

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
        # macOS/IOKit only populates the joystick list AFTER the Cocoa event
        # loop has been pumped a few times; calling get_count() immediately
        # after init() returns 0 even with a pad plugged in. Pump briefly until
        # a device appears (or give up after ~2s).
        import time

        deadline = time.monotonic() + 2.0
        while pygame.joystick.get_count() == 0 and time.monotonic() < deadline:
            pygame.event.get()
            time.sleep(1 / 120)
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


# Standard HID 8-way hat: nibble -> (dx, dy) with y+ = up. 8 = neutral.
_HAT_DIRS = {
    0: (0, 1),    # up
    1: (1, 1),    # up-right
    2: (1, 0),    # right
    3: (1, -1),   # down-right
    4: (0, -1),   # down
    5: (-1, -1),  # down-left
    6: (-1, 0),   # left
    7: (-1, 1),   # up-left
    8: (0, 0),    # neutral
}


class HidGcReader:
    """Raw-HID reader for the Mayflash GameCube adapter (PC/DInput mode).

    SDL/pygame cannot parse this adapter on macOS (it enumerates with 0 axes /
    0 buttons), so we open the chosen adapter PORT directly via hidapi and decode
    its 9-byte report ourselves. Mapping (byte indices, button byte.bit, invert)
    comes from config; defaults match a calibrated Mayflash unit.

    Report layout (per port, rest = ``00 00 80 80 80 80 00 00 08``):
      byte 0/1  digital button bitfields
      byte 2..5 stick axes (rest 0x80)
      byte 6/7  analog L/R triggers (rest 0x00)
      byte 8    low nibble = D-pad hat (8 = neutral)
    """

    def __init__(self, mapping: ControllerMap):
        self.map = mapping
        self._dev = None
        self._last = bytes(9)
        # Pre-parse "byte.bit" -> logical name into (byte, mask, name) tuples.
        self._btns: list[tuple[int, int, str]] = []
        for key, name in (self.map.buttons or {}).items():
            byte_s, _, bit_s = str(key).partition(".")
            self._btns.append((int(byte_s), 1 << int(bit_s), name))

    def open(self) -> None:
        import hid  # lazy: optional dependency

        target = None
        for d in hid.enumerate():
            if d.get("vendor_id") != self.map.hid_vendor:
                continue
            if self.map.hid_product and d.get("product_id") != self.map.hid_product:
                continue
            if d.get("interface_number") != self.map.hid_interface:
                continue
            target = d
            break
        if target is None:
            raise RuntimeError(
                f"no HID device vendor=0x{self.map.hid_vendor:04x} "
                f"interface={self.map.hid_interface} found "
                "(is the adapter plugged in and Steam quit?)"
            )
        self._dev = hid.device()
        self._dev.open_path(target["path"])
        self._dev.set_nonblocking(True)
        self._name = target.get("product_string") or "GameCube adapter"

    @property
    def name(self) -> str:
        return getattr(self, "_name", "<none>")

    def _refresh(self) -> bytes:
        """Drain pending HID reports; keep the most recent full one."""
        if self._dev is None:
            raise RuntimeError("controller not open")
        for _ in range(32):
            data = self._dev.read(64)
            if not data:
                break
            if len(data) >= 9:
                self._last = bytes(data)
        return self._last

    def _axis_pipe(self, role: str) -> float:
        byte = self.map.axes.get(role)
        if byte is None or byte >= len(self._last):
            return 0.5
        n = (self._last[byte] - 128) / 127.0  # -> [-1, 1], stick center 0x80
        return _axis_to_pipe(n, self.map.invert.get(role, False), self.map.deadzone)

    def poll(self) -> PhysicalState:
        rep = self._refresh()

        main = (self._axis_pipe("main_x"), self._axis_pipe("main_y"))
        c = (self._axis_pipe("c_x"), self._axis_pipe("c_y"))

        def trig(role: str) -> float:
            byte = self.map.axes.get(role)
            if byte is None or byte >= len(rep):
                return 0.0
            return max(0.0, min(1.0, rep[byte] / 255.0))  # rest 0x00 -> 0

        pressed: set[str] = set()
        for byte, mask, name in self._btns:
            if byte < len(rep) and (rep[byte] & mask):
                pressed.add(name)

        l = trig("l_trigger")
        r = trig("r_trigger")
        # Analog L doubling as a held macro modifier: past the threshold it
        # becomes the logical L_MOD button and its analog value is suppressed
        # (so it won't shield/airdodge while you use it to trigger a macro).
        if self.map.l_mod_name and l >= self.map.l_mod_threshold:
            pressed.add(self.map.l_mod_name)
            l = 0.0

        # D-pad via the hat nibble.
        if self.map.hat_byte < len(rep):
            dx, dy = _HAT_DIRS.get(rep[self.map.hat_byte] & 0x0F, (0, 0))
            if dx < 0:
                pressed.add("D_LEFT")
            elif dx > 0:
                pressed.add("D_RIGHT")
            if dy > 0:
                pressed.add("D_UP")
            elif dy < 0:
                pressed.add("D_DOWN")

        return PhysicalState(buttons=frozenset(pressed), main=main, c=c, l=l, r=r)

    def raw_buttons(self) -> list[int]:
        """Currently-set raw bits across byte 0/1 (for --debug), as byte*8+bit."""
        rep = self._last
        out = []
        for byte in (0, 1):
            if byte < len(rep):
                for bit in range(8):
                    if rep[byte] & (1 << bit):
                        out.append(byte * 8 + bit)
        return out

    def close(self) -> None:
        if self._dev is not None:
            try:
                self._dev.close()
            except Exception:  # noqa: BLE001
                pass
            self._dev = None
