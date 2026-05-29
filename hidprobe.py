#!/usr/bin/env python3
"""Guided calibrator for the Mayflash GameCube adapter (raw HID, bypasses SDL).

    uv run --with hidapi python hidprobe.py

It walks you through each control one at a time, auto-detects which report
byte/bit/direction it maps to, and at the end prints a ready-to-paste config
block (interface number + byte map + which axes need inverting).

Follow the prompts; press ENTER-free — it advances automatically once it sees
the input and you release it.
"""
from __future__ import annotations

import sys
import time

import hid

VID = 0x0079  # DragonRise / Mayflash (PC mode)
REPORT_LEN = 9
STICK_BYTES = (2, 3, 4, 5)   # rest ~0x80
TRIG_BYTES = (6, 7)          # rest ~0x00
BTN_BYTES = (0, 1)           # digital button bitfields


def read_latest(h) -> bytes | None:
    """Drain pending reports, return the most recent full one."""
    latest = None
    for _ in range(32):
        data = bytes(h.read(64))
        if not data:
            break
        if len(data) >= REPORT_LEN:
            latest = data
    return latest


def wait_settle(h, baseline: bytes) -> bytes:
    """Block until the report returns close to baseline (control released)."""
    while True:
        d = read_latest(h)
        if d is not None:
            baseline = d
            if _near_rest(d):
                return d
        time.sleep(1 / 120)


def _near_rest(d: bytes) -> bool:
    for b in STICK_BYTES:
        if abs(d[b] - 0x80) > 30:
            return False
    for b in TRIG_BYTES:
        if d[b] > 40:
            return False
    if d[0] != 0 or d[1] != 0:
        return False
    if (d[8] & 0x0F) != 0x08:  # hat neutral
        return False
    return True


def detect_change(h, rest: bytes, kind: str):
    """Wait for the user's input; return a description of what changed."""
    while True:
        d = read_latest(h)
        if d is None:
            time.sleep(1 / 120)
            continue
        if kind == "stick":
            best, bestmag = None, 0
            for b in STICK_BYTES:
                mag = abs(d[b] - 0x80)
                if mag > bestmag:
                    best, bestmag = b, mag
            if bestmag > 50:
                return {"byte": best, "value": d[best], "high": d[best] > 0x80}
        elif kind == "trigger":
            best, bestval = None, 0
            for b in TRIG_BYTES:
                if d[b] > bestval:
                    best, bestval = b, d[b]
            if bestval > 100:
                return {"byte": best, "value": d[best]}
        elif kind == "button":
            for b in BTN_BYTES:
                changed = d[b] ^ rest[b]
                for bit in range(8):
                    if changed & (1 << bit) and (d[b] & (1 << bit)):
                        return {"byte": b, "bit": bit}
            # some pads put extra buttons in the high nibble of byte 8
            hi = (d[8] & 0xF0) ^ (rest[8] & 0xF0)
            for bit in range(4, 8):
                if hi & (1 << bit) and (d[8] & (1 << bit)):
                    return {"byte": 8, "bit": bit}
        elif kind == "dpad":
            nib = d[8] & 0x0F
            if nib != 0x08:
                return {"hat": nib}
        time.sleep(1 / 120)


def main() -> int:
    seen: dict[bytes, dict] = {}
    for dd in hid.enumerate():
        if dd.get("vendor_id") == VID:
            seen.setdefault(dd["path"], dd)
    if not seen:
        print("No Mayflash (VID 0x0079) HID interfaces found.")
        return 1

    devs = []
    for p, info in seen.items():
        h = hid.device()
        try:
            h.open_path(p)
            h.set_nonblocking(True)
            devs.append((info.get("interface_number"), h))
        except Exception as e:  # noqa: BLE001
            print(f"failed to open iface {info.get('interface_number')}: {e}")
    if not devs:
        print("Could not open any interface (another app may hold the device).")
        return 1

    print("Wiggle the MAIN stick so I can find which port your controller is in...")
    iface, dev = None, None
    while iface is None:
        for ifc, h in devs:
            d = read_latest(h)
            if d and (abs(d[2] - 0x80) > 50 or abs(d[3] - 0x80) > 50):
                iface, dev = ifc, h
                break
        time.sleep(1 / 120)
    print(f"-> controller is on interface_number = {iface}\n")
    print("Now release the stick (center it)...")
    rest = wait_settle(dev, read_latest(dev) or bytes(REPORT_LEN))
    print(f"rest report: {rest.hex(' ')}\n")

    steps_stick = [
        ("main_x", "push MAIN stick fully RIGHT, then release"),
        ("main_y", "push MAIN stick fully UP, then release"),
        ("c_x", "push C-stick fully RIGHT, then release"),
        ("c_y", "push C-stick fully UP, then release"),
    ]
    steps_trig = [
        ("l_trigger", "squeeze the L trigger fully, then release"),
        ("r_trigger", "squeeze the R trigger fully, then release"),
    ]
    steps_btn = ["A", "B", "X", "Y", "Z", "START"]
    steps_dpad = [("D_UP", "UP"), ("D_DOWN", "DOWN"), ("D_LEFT", "LEFT"), ("D_RIGHT", "RIGHT")]

    axes: dict[str, dict] = {}
    invert: dict[str, bool] = {}
    buttons: dict[int, dict] = {}  # (byte,bit) -> name, but keyed for printing
    button_map: list[tuple[int, int, str]] = []
    dpad_hats: dict[str, int] = {}

    def prompt(msg):
        print(f"  >> {msg}")
        sys.stdout.flush()

    for role, msg in steps_stick:
        prompt(msg)
        r = detect_change(dev, rest, "stick")
        axes[role] = r["byte"]
        # pipe convention: RIGHT and UP should map to 1.0. _axis high (>0x80)
        # means that direction reads high; if pushing RIGHT/UP reads LOW we must
        # invert.
        invert[role] = not r["high"]
        print(f"     {role} = byte{r['byte']} (push read 0x{r['value']:02x}, invert={invert[role]})")
        wait_settle(dev, rest)

    for role, msg in steps_trig:
        prompt(msg)
        r = detect_change(dev, rest, "trigger")
        axes[role] = r["byte"]
        print(f"     {role} = byte{r['byte']} (full read 0x{r['value']:02x})")
        wait_settle(dev, rest)

    for name in steps_btn:
        prompt(f"press {name}, then release")
        r = detect_change(dev, rest, "button")
        button_map.append((r["byte"], r["bit"], name))
        print(f"     {name} = byte{r['byte']} bit{r['bit']}")
        wait_settle(dev, rest)

    for role, label in steps_dpad:
        prompt(f"press D-pad {label}, then release")
        r = detect_change(dev, rest, "dpad")
        dpad_hats[role] = r["hat"]
        print(f"     {role} = hat nibble {r['hat']}")
        wait_settle(dev, rest)

    # ---- emit a config-ready summary -------------------------------------
    print("\n================= CALIBRATION RESULT =================")
    print(f"interface_number: {iface}")
    print("axes (report byte index):")
    for role in ("main_x", "main_y", "c_x", "c_y", "l_trigger", "r_trigger"):
        if role in axes:
            print(f"  {role}: {axes[role]}")
    print("invert:")
    for role in ("main_x", "main_y", "c_x", "c_y"):
        if role in invert:
            print(f"  {role}: {str(invert[role]).lower()}")
    print("buttons (byte,bit -> name):")
    for b, bit, name in button_map:
        print(f"  byte{b} bit{bit}: {name}")
    print("dpad hat nibbles:")
    for role, nib in dpad_hats.items():
        print(f"  {role}: {nib}")
    print("=====================================================")
    print("\nPaste this whole block back to me and I'll wire up the reader + config.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
