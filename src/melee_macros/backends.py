"""Output backends: where compiled controller frames are sent, and how frame
timing is paced.

Two backends:

* :class:`PipeBackend` — writes to Dolphin's pipe input and paces frames with a
  wall-clock 60 Hz loop. Works with no extra game integration, but timing is
  *open-loop*: it assumes the emulator runs at a steady 60 fps and there is no
  per-frame handshake, so single-frame inputs can occasionally land a frame
  early/late under load.

* :class:`LibmeleeBackend` — uses libmelee's ``Console`` to step the game one
  frame at a time. ``wait_frame`` blocks until the next gamestate arrives, so
  every macro frame lands on exactly one game frame (frame-accurate). Requires
  a running Slippi Dolphin + ISO and the optional ``melee`` dependency.

* :class:`HybridBackend` — sends inputs through the pipe (so YOU launch Dolphin
  from the Slippi Launcher, exactly like ``PipeBackend``), but also spins up a
  read-only libmelee connection in a background thread to mirror live game
  state. That gives closed-loop macros and auto-edgeguard their ``GameView``
  without libmelee launching the game. If the read connection can't be made (or
  drops), output is unaffected — ``gamestate()`` just returns ``None`` and
  macros fall back to fixed timing.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Protocol

from .gamestate import GameView, from_libmelee
from .inputs import ControllerState
from .pipe import DolphinPipe


class Backend(Protocol):
    def open(self) -> None: ...
    def wait_frame(self) -> None: ...
    def send(self, state: ControllerState) -> None: ...
    def gamestate(self) -> GameView | None: ...
    def close(self) -> None: ...


class _Clock:
    """Fixed-step pacer that corrects for drift and resets after long stalls."""

    def __init__(self, fps: float = 60.0):
        self.dt = 1.0 / fps
        self._next = None

    def tick(self) -> None:
        now = time.perf_counter()
        if self._next is None:
            self._next = now + self.dt
            return
        sleep = self._next - now
        if sleep > 0:
            time.sleep(sleep)
            self._next += self.dt
        else:
            # Overran the budget; resync rather than spiral.
            self._next = now + self.dt


class PipeBackend:
    def __init__(self, pipe_path: str, fps: float = 60.0, create: bool = True):
        self.pipe = DolphinPipe(pipe_path, create=create)
        self.clock = _Clock(fps)

    def open(self) -> None:
        self.pipe.open()

    def wait_frame(self) -> None:
        self.clock.tick()

    def send(self, state: ControllerState) -> None:
        self.pipe.send(state)

    def gamestate(self) -> GameView | None:
        return None  # open-loop: no game state available

    def close(self) -> None:
        self.pipe.close()


class LibmeleeBackend:
    """Frame-accurate backend driven by libmelee's console stepping.

    The engine should call wait_frame() (which blocks on console.step()) then
    send() each loop. The physical-controller read still happens in the engine.
    """

    def __init__(self, *, dolphin_path: str, iso_path: str, port: int = 1):
        # libmelee does not expand "~" or env vars, so normalize here.
        self.dolphin_path = os.path.expanduser(os.path.expandvars(dolphin_path))
        self.iso_path = os.path.expanduser(os.path.expandvars(iso_path))
        self.port = port
        self._console = None
        self._controller = None
        self._melee = None
        self._gamestate = None

    def open(self) -> None:
        import melee  # lazy: optional dependency

        self._melee = melee
        self._console = melee.Console(path=self.dolphin_path)
        self._controller = melee.Controller(
            console=self._console, port=self.port, type=melee.ControllerType.STANDARD
        )
        self._console.run(iso_path=self.iso_path)
        self._console.connect()
        self._controller.connect()

    def wait_frame(self) -> None:
        # Blocks until the next gamestate is available -> one game frame.
        self._gamestate = self._console.step()

    def gamestate(self) -> GameView | None:
        return from_libmelee(self._gamestate, self.port)

    def send(self, state: ControllerState) -> None:
        melee = self._melee
        c = self._controller
        Button = melee.Button
        c.tilt_analog(Button.BUTTON_MAIN, state.main[0], state.main[1])
        c.tilt_analog(Button.BUTTON_C, state.c[0], state.c[1])
        c.press_shoulder(Button.BUTTON_L, state.l)
        c.press_shoulder(Button.BUTTON_R, state.r)
        name_map = {
            "A": Button.BUTTON_A,
            "B": Button.BUTTON_B,
            "X": Button.BUTTON_X,
            "Y": Button.BUTTON_Y,
            "Z": Button.BUTTON_Z,
            "START": Button.BUTTON_START,
            "L": Button.BUTTON_L,
            "R": Button.BUTTON_R,
            "D_UP": Button.BUTTON_D_UP,
            "D_DOWN": Button.BUTTON_D_DOWN,
            "D_LEFT": Button.BUTTON_D_LEFT,
            "D_RIGHT": Button.BUTTON_D_RIGHT,
        }
        for name, btn in name_map.items():
            if name in state.buttons:
                c.press_button(btn)
            else:
                c.release_button(btn)
        c.flush()

    def close(self) -> None:
        if self._console is not None:
            self._console.stop()


class HybridBackend:
    """Pipe output + read-only libmelee state mirror (background thread).

    Output and pacing are identical to :class:`PipeBackend` (you launch Dolphin
    yourself and point Port 1 at the pipe). A daemon thread separately connects
    a libmelee ``Console`` in read-only mode to the SAME running Dolphin and
    keeps the latest :class:`GameView` available via :meth:`gamestate`.

    The reader is best-effort and fully decoupled: if libmelee isn't installed,
    can't connect, or the connection drops, the input path keeps working and
    ``gamestate()`` returns ``None`` (macros use fixed timing).
    """

    def __init__(
        self,
        pipe_path: str,
        *,
        dolphin_path: str,
        port: int = 1,
        fps: float = 60.0,
        on_event=None,
    ):
        self.pipe = DolphinPipe(pipe_path, create=True)
        self.clock = _Clock(fps)
        self.dolphin_path = os.path.expanduser(os.path.expandvars(dolphin_path))
        self.port = port
        self._on_event = on_event or (lambda *a: None)
        self._latest: GameView | None = None
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._connected = False

    def open(self) -> None:
        # Output first (blocks until Dolphin opens the pipe — same as pipe mode).
        self.pipe.open()
        # Start the read-only state mirror in the background.
        self._thread = threading.Thread(target=self._reader_loop, daemon=True)
        self._thread.start()

    def _reader_loop(self) -> None:
        try:
            import melee  # lazy/optional
        except ImportError:
            self._on_event("debug", "hybrid: melee not installed; state mirror off")
            return
        try:
            console = melee.Console(path=self.dolphin_path, copy_home_directory=False)
        except Exception as e:  # noqa: BLE001 - never let the reader kill the engine
            self._on_event("debug", f"hybrid: Console init failed: {e}")
            return
        # connect() (no run()) attaches to the ALREADY-running Dolphin.
        try:
            ok = console.connect()
        except Exception as e:  # noqa: BLE001
            self._on_event("debug", f"hybrid: connect() raised: {e}")
            return
        if not ok:
            self._on_event(
                "debug",
                "hybrid: could not connect to running Dolphin for state "
                "(inputs still work; macros use fixed timing).",
            )
            return
        self._connected = True
        self._on_event("debug", "hybrid: state mirror connected.")
        try:
            while not self._stop.is_set():
                gs = console.step()  # blocks ~one frame; None if the link drops
                if gs is None:
                    continue
                view = from_libmelee(gs, self.port)
                with self._lock:
                    self._latest = view
        except Exception as e:  # noqa: BLE001
            self._on_event("debug", f"hybrid: reader stopped: {e}")
        finally:
            try:
                console.stop()
            except Exception:  # noqa: BLE001
                pass

    def wait_frame(self) -> None:
        self.clock.tick()

    def gamestate(self) -> GameView | None:
        with self._lock:
            return self._latest

    def send(self, state: ControllerState) -> None:
        self.pipe.send(state)

    def close(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=1.0)
        self.pipe.close()
