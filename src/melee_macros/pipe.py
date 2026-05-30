"""Dolphin/Slippi *Pipe Input* writer.

Dolphin exposes a controller device that reads newline-delimited commands from
a named pipe (FIFO). Configure a GCN port in Dolphin to the device
``Pipe/0/<name>`` and Dolphin will read from
``<User>/Pipes/<name>``. On macOS the Slippi user dir is typically
``~/Library/Application Support/Slippi Dolphin/`` (older builds:
``.../Dolphin/``).

Command protocol (one per line):
    PRESS <BUTTON>
    RELEASE <BUTTON>
    SET MAIN <x> <y>     # 0..1, 0.5 center, y up
    SET C <x> <y>
    SET L <v>            # 0..1 analog trigger
    SET R <v>

This module diffs successive :class:`ControllerState` objects and only writes
the commands that changed, which is how libmelee drives the same pipe.
"""

from __future__ import annotations

import os
import stat
import tempfile
from pathlib import Path
from typing import Optional

from .inputs import DIGITAL_BUTTONS, NEUTRAL_STATE, ControllerState

# Candidate Slippi/Dolphin user directories on macOS, most-likely first. The
# Slippi Launcher's netplay Dolphin keeps its User dir under com.project-slippi.
_MAC_USER_DIRS = (
    "~/Library/Application Support/com.project-slippi.dolphin/netplay/User",
    "~/Library/Application Support/Slippi Dolphin",
    "~/Library/Application Support/Dolphin",
)


def default_pipe_path(name: str = "slippibot") -> Path:
    for base in _MAC_USER_DIRS:
        base_dir = Path(os.path.expanduser(base))
        if base_dir.exists():
            return base_dir / "Pipes" / name
    # Fall back to the first (Slippi) path; caller/open() will create the dir.
    return Path(os.path.expanduser(_MAC_USER_DIRS[0])) / "Pipes" / name


def list_libmelee_pipes(name_prefix: str = "slippibot") -> list[Path]:
    """All libmelee temp-dir pipe FIFOs, newest first.

    slippi-ai / libmelee launch Dolphin from a throwaway COPY of the Slippi
    user dir at ``<tmp>/libmelee_XXXXXX/User`` (``tmp_home_directory=True``),
    so its pipes live at ``<tmp>/libmelee_XXXXXX/User/Pipes/slippibot<port>``,
    NOT in the real Slippi user dir we write to by default. That mismatch is
    why injection works against the official Slippi Dolphin but not against the
    Dolphin slippi-ai spawns.
    """
    tmp = Path(tempfile.gettempdir())
    candidates: list[Path] = []
    for home in tmp.glob("libmelee_*"):
        pipes_dir = home / "User" / "Pipes"
        if not pipes_dir.is_dir():
            continue
        for p in pipes_dir.iterdir():
            if not p.name.startswith(name_prefix):
                continue
            try:
                if stat.S_ISFIFO(p.stat().st_mode):
                    candidates.append(p)
            except OSError:
                continue
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates


def find_libmelee_pipe(
    name_prefix: str = "slippibot", port: Optional[int] = None
) -> Optional[Path]:
    """Locate a libmelee temp-dir pipe FIFO.

    If ``port`` is given, return the pipe named ``slippibot<port>`` exactly
    (this is the port-pinned form — e.g. your ``--p1.type pipe`` controller is
    ``slippibot1``, the AI on P2 is ``slippibot2``). Otherwise return the most
    recently created matching FIFO. Returns ``None`` if no such pipe exists
    (slippi-ai/Dolphin isn't running yet).
    """
    pipes = list_libmelee_pipes(name_prefix)
    if not pipes:
        return None
    if port is not None:
        target = f"{name_prefix}{port}"
        for p in pipes:
            if p.name == target:
                return p
        return None
    return pipes[0]  # newest


class DolphinPipe:
    """Opens the FIFO and emits diffed pipe commands."""

    def __init__(self, path: str | os.PathLike, create: bool = True):
        self.path = Path(os.path.expanduser(str(path)))
        self._create = create
        self._fh = None
        self._last = NEUTRAL_STATE

    def open(self) -> None:
        if self._create:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if not self.path.exists():
                os.mkfifo(self.path)
        # Open in write mode; this blocks until Dolphin opens the read end.
        self._fh = open(self.path, "w", buffering=1)
        self._last = NEUTRAL_STATE
        self._write_full(NEUTRAL_STATE)

    def close(self) -> None:
        if self._fh is not None:
            try:
                self._write_full(NEUTRAL_STATE)
            finally:
                self._fh.close()
                self._fh = None

    def __enter__(self) -> "DolphinPipe":
        self.open()
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # --- writing ---------------------------------------------------------
    def _emit(self, line: str) -> None:
        assert self._fh is not None, "pipe not open"
        self._fh.write(line + "\n")

    def _write_full(self, s: ControllerState) -> None:
        for b in sorted(s.buttons):
            self._emit(f"PRESS {b}")
        for b in sorted(DIGITAL_BUTTONS - s.buttons):
            self._emit(f"RELEASE {b}")
        self._emit(f"SET MAIN {s.main[0]:.4f} {s.main[1]:.4f}")
        self._emit(f"SET C {s.c[0]:.4f} {s.c[1]:.4f}")
        self._emit(f"SET L {s.l:.4f}")
        self._emit(f"SET R {s.r:.4f}")
        self._fh.flush()
        self._last = s

    def send(self, s: ControllerState) -> None:
        """Write only what changed vs. the previously sent state."""
        if self._fh is None:
            raise RuntimeError("pipe not open")
        prev = self._last
        for b in s.buttons - prev.buttons:
            self._emit(f"PRESS {b}")
        for b in prev.buttons - s.buttons:
            self._emit(f"RELEASE {b}")
        if s.main != prev.main:
            self._emit(f"SET MAIN {s.main[0]:.4f} {s.main[1]:.4f}")
        if s.c != prev.c:
            self._emit(f"SET C {s.c[0]:.4f} {s.c[1]:.4f}")
        if s.l != prev.l:
            self._emit(f"SET L {s.l:.4f}")
        if s.r != prev.r:
            self._emit(f"SET R {s.r:.4f}")
        self._fh.flush()
        self._last = s
