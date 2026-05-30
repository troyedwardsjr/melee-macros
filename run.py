#!/usr/bin/env python3
"""CLI entrypoint for the Fox macro system.

    python run.py list                 # list all macros and lengths
    python run.py dump <macro>         # print a macro's per-frame inputs
    python run.py check                # compile all macros (no game needed)
    python run.py run [--config FILE]  # start the live engine
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from melee_macros import build_fox_library  # noqa: E402
from melee_macros.config import default_config_path, load_config  # noqa: E402
from melee_macros.inputs import DIGITAL_BUTTONS  # noqa: E402


def cmd_list(_args) -> int:
    lib = build_fox_library()
    for name in lib.names():
        m = lib.get(name)
        print(f"{name:28s} {len(m):3d}f  {m.description}")
    print(f"\n{len(lib.names())} macros.")
    return 0


def _fmt_axis(xy):
    return f"({xy[0]:.3f},{xy[1]:.3f})"


def cmd_dump(args) -> int:
    lib = build_fox_library()
    if args.macro not in lib:
        print(f"no such macro: {args.macro}", file=sys.stderr)
        return 1
    m = lib.get(args.macro)
    print(f"# {m.name} ({len(m)} frames) — {m.description}\n")
    print(f"{'f':>3}  {'buttons':<22} {'main':<16} {'c':<16} {'L':>5} {'R':>5}")
    for i, s in enumerate(m.frames):
        btns = "+".join(sorted(s.buttons)) or "-"
        print(f"{i:>3}  {btns:<22} {_fmt_axis(s.main):<16} {_fmt_axis(s.c):<16} {s.l:>5.2f} {s.r:>5.2f}")
    return 0


def cmd_check(_args) -> int:
    lib = build_fox_library()
    bad = 0
    for name in lib.names():
        m = lib.get(name)
        for i, s in enumerate(m.frames):
            for b in s.buttons:
                if b not in DIGITAL_BUTTONS:
                    print(f"{name} f{i}: invalid button {b}", file=sys.stderr)
                    bad += 1
            for axis, label in ((s.main, "main"), (s.c, "c")):
                for v in axis:
                    if not (0.0 <= v <= 1.0):
                        print(f"{name} f{i}: {label} out of range: {v}", file=sys.stderr)
                        bad += 1
    if bad:
        print(f"FAILED: {bad} issue(s).", file=sys.stderr)
        return 1
    print(f"OK: {len(lib.names())} macros compiled and validated.")
    return 0


def cmd_probe(args) -> int:
    """Print live button/axis indices so you can fill in config.yaml."""
    import time

    sys.stdout.reconfigure(line_buffering=True)  # print live even when redirected
    # Enable SDL's GameCube-adapter HIDAPI driver (Wii U mode). Must be set
    # before pygame/SDL initializes its joystick subsystem.
    import os

    os.environ.setdefault("SDL_JOYSTICK_HIDAPI", "1")
    os.environ.setdefault("SDL_JOYSTICK_HIDAPI_GAMECUBE", "1")
    try:
        import pygame
    except ImportError:
        print("pygame not installed. Run: uv sync", file=sys.stderr)
        return 1

    pygame.init()
    # macOS only delivers controller events when there is a real window and the
    # Cocoa event queue is pumped via event.get(). A dummy/headless driver gets
    # zero input — so open a small window.
    try:
        pygame.display.set_mode((300, 90))
        pygame.display.set_caption("melee-macros probe — keep this window open")
    except pygame.error as e:
        print(f"(could not open a window: {e}; input may not register)", file=sys.stderr)
    pygame.joystick.init()
    # macOS/IOKit only populates the joystick list after the Cocoa event loop
    # has been pumped a few times; polling immediately after init() returns 0
    # even with a pad plugged in. Pump briefly until a device appears.
    deadline = time.monotonic() + 2.0
    while pygame.joystick.get_count() == 0 and time.monotonic() < deadline:
        pygame.event.get()
        time.sleep(1 / 120)
    n = pygame.joystick.get_count()
    if n == 0:
        print("No SDL controller detected. Plug it in and try again.", file=sys.stderr)
        return 1

    # Open and report EVERY detected device. A 4-port adapter (Mayflash) shows
    # up as 4 separate joysticks; an empty port reports 0 axes/0 buttons while
    # the port with a controller plugged in reports the real descriptor. So we
    # watch them all and tag each event with its joystick index — whichever
    # index lights up when you move the stick is the one to put in config.yaml.
    sticks = []
    for i in range(n):
        js = pygame.joystick.Joystick(i)
        js.init()
        sticks.append(js)

    # Pump a moment so capabilities settle, then print per-device caps.
    for _ in range(60):
        pygame.event.get()
        time.sleep(1 / 120)
    print(f"Detected {n} device(s):")
    for i, js in enumerate(sticks):
        rest = [round(js.get_axis(a), 2) for a in range(js.get_numaxes())]
        print(
            f"  index {i}: {js.get_name()} — "
            f"{js.get_numaxes()} axes, {js.get_numbuttons()} buttons, {js.get_numhats()} hats"
            + (f"  rest={rest}" if rest else "")
        )
    print(
        "\nNow move the stick / press buttons on your GameCube controller. Every\n"
        "change prints below, tagged with [index]. The index that responds is the\n"
        "one to set as controller.index in config.yaml. Ctrl-C to stop.\n"
    )

    last_btns: dict[int, set[int]] = {i: set() for i in range(n)}
    last_axes: dict[int, dict[int, float]] = {
        i: {a: js.get_axis(a) for a in range(js.get_numaxes())} for i, js in enumerate(sticks)
    }
    last_hats: dict[int, dict[int, tuple]] = {
        i: {h: (0, 0) for h in range(js.get_numhats())} for i, js in enumerate(sticks)
    }
    try:
        while True:
            # On macOS, controller state only updates when the Cocoa event queue
            # is drained via event.get() (pump() alone is not enough with a window).
            pygame.event.get()
            for i, js in enumerate(sticks):
                btns = {b for b in range(js.get_numbuttons()) if js.get_button(b)}
                if btns != last_btns[i]:
                    down = sorted(btns - last_btns[i])
                    up = sorted(last_btns[i] - btns)
                    if down:
                        print(f"[{i}] button DOWN {down}    (all held: {sorted(btns) or '-'})")
                    if up:
                        print(f"[{i}] button UP   {up}")
                    last_btns[i] = btns
                for a in range(js.get_numaxes()):
                    v = js.get_axis(a)
                    if abs(v - last_axes[i][a]) > 0.12:
                        print(f"[{i}] axis {a}: {v:+.2f}")
                        last_axes[i][a] = v
                for h in range(js.get_numhats()):
                    hv = js.get_hat(h)
                    if hv != last_hats[i][h]:
                        print(f"[{i}] hat {h} (D-pad): {hv}")
                        last_hats[i][h] = hv
            time.sleep(1 / 60)
    except KeyboardInterrupt:
        print("\n[stop]")
    return 0


def cmd_run(args) -> int:
    from melee_macros.controller import ControllerReader, HidGcReader
    from melee_macros.engine import Engine

    cfg = load_config(args.config or default_config_path())

    # --pipe overrides where we write inputs. Use this for slippi-ai (and any
    # libmelee-launched Dolphin): it spawns Dolphin from a THROWAWAY COPY of the
    # Slippi user dir under /tmp/libmelee_*/User, so its pipe is there — NOT in
    # the real Slippi user dir config.yaml points at. `--pipe auto` finds that
    # temp pipe for you; `--pipe PATH` points at an explicit FIFO.
    if args.pipe:
        if args.pipe == "auto" or args.pipe.startswith("auto:"):
            from melee_macros.pipe import find_libmelee_pipe, list_libmelee_pipes

            # `auto:N` pins the pipe for port N (e.g. auto:1 -> slippibot1, your
            # `--p1.type pipe` controller; the AI on P2 is slippibot2). Bare
            # `auto` takes the newest, but warns if several exist so you don't
            # silently grab the AI's port.
            port = None
            if ":" in args.pipe:
                try:
                    port = int(args.pipe.split(":", 1)[1])
                except ValueError:
                    print(f"error: bad --pipe value {args.pipe!r}; use auto or auto:N", file=sys.stderr)
                    return 1
            all_pipes = list_libmelee_pipes()
            found = find_libmelee_pipe(port=port)
            if found is None:
                if port is not None and all_pipes:
                    print(
                        f"error: --pipe auto:{port} found no slippibot{port} pipe. "
                        f"Available: {[p.name for p in all_pipes]}. Did you start "
                        f"slippi-ai with --p{port}.type pipe?",
                        file=sys.stderr,
                    )
                else:
                    print(
                        "error: --pipe auto found no libmelee_* temp pipe. Start "
                        "slippi-ai (so it launches Dolphin) first, then run this.",
                        file=sys.stderr,
                    )
                return 1
            if port is None and len(all_pipes) > 1:
                print(
                    f"[pipe] warning: {len(all_pipes)} libmelee pipes present "
                    f"({[p.name for p in all_pipes]}); picking newest {found.name}. "
                    f"Use --pipe auto:N to target your port (e.g. auto:1).",
                    file=sys.stderr,
                )
            cfg.pipe_path = str(found)
            print(f"[pipe] auto-located libmelee pipe: {found}")
        else:
            cfg.pipe_path = os.path.expanduser(args.pipe)
            print(f"[pipe] using override pipe: {cfg.pipe_path}")
        # slippi-ai already owns/launches the game, so the hybrid state mirror
        # (which tries to attach to the default Slippi Dolphin) won't find it —
        # drop to plain pipe output to avoid a pointless connect attempt.
        if cfg.backend == "hybrid":
            print("[pipe] override active: using 'pipe' backend (no state mirror).")
            cfg.backend = "pipe"

    lib = build_fox_library()
    unknown = [t.macro for t in cfg.triggers if t.macro not in lib]
    if unknown:
        print(f"warning: triggers reference unknown macros: {unknown}", file=sys.stderr)

    # "hid_gc" reads the Mayflash GameCube adapter directly (SDL can't on macOS);
    # everything else goes through the SDL/pygame reader.
    if cfg.controller.driver == "hid_gc":
        reader = HidGcReader(cfg.controller)
    else:
        reader = ControllerReader(cfg.controller)

    def on_event(kind, payload):
        if kind == "ready":
            print(f"[ready] controller: {payload}. {len(cfg.triggers)} triggers bound.")
        elif kind == "waiting":
            if cfg.backend in ("pipe", "hybrid"):
                print(
                    "[waiting] open Dolphin (Slippi Launcher) and set Port 1 to the "
                    "Pipe device, then it will connect. The input window is already open."
                )
        elif kind == "connected":
            print("[connected] Dolphin is reading the pipe. Ctrl-C to stop.")
            if cfg.backend == "hybrid":
                print("[hybrid] attempting read-only state mirror in the background…")
        elif kind == "macro_start":
            print(f"[macro] {payload}")
        elif kind == "debug":
            print(f"[dbg] {payload}")
        elif kind == "stop":
            print("[stop]")

    # Pass on_event so the hybrid backend can report state-mirror status.
    backend = cfg.build_backend(on_event=on_event)

    Engine(
        backend, reader, lib, cfg.triggers,
        passthrough=cfg.passthrough, on_event=on_event, debug=args.debug,
        reactive=cfg.reactive, reactive_edgeguard=cfg.reactive_edgeguard,
    ).run()
    return 0


def main() -> int:
    p = argparse.ArgumentParser(description="Fox macro system for Slippi/Dolphin")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("list", help="list macros").set_defaults(func=cmd_list)
    d = sub.add_parser("dump", help="print a macro's frames")
    d.add_argument("macro")
    d.set_defaults(func=cmd_dump)
    sub.add_parser("check", help="compile + validate all macros").set_defaults(func=cmd_check)
    pr = sub.add_parser("probe", help="print live controller button/axis indices")
    pr.add_argument("--index", type=int, default=0, help="controller index to probe")
    pr.add_argument("--deadzone", type=float, default=0.3, help="axis report threshold")
    pr.set_defaults(func=cmd_probe)
    r = sub.add_parser("run", help="start the live engine")
    r.add_argument("--config", default=None)
    r.add_argument(
        "--pipe",
        default=None,
        metavar="PATH|auto|auto:N",
        help="override the output pipe. 'auto' locates the newest libmelee_* "
        "temp pipe (for slippi-ai); 'auto:N' pins the pipe for port N "
        "(e.g. auto:1 for your --p1.type pipe controller); or pass an explicit "
        "FIFO path.",
    )
    r.add_argument("--debug", action="store_true", help="print raw button indices / stick on every input change")
    r.set_defaults(func=cmd_run)
    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
