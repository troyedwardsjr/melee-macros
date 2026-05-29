#!/usr/bin/env python3
"""Show the digital-button bytes (0 and 1) of the GameCube adapter as binary,
so we can see exactly which bit each button sets.

    uv run --with hidapi python btnprobe.py

Press each button and watch the two bitfields. Press START a few times, then
A, B, X, Y, Z, and squeeze L / R fully (the digital "click" at the bottom).
Ctrl-C to stop.
"""
from __future__ import annotations

import time

import hid

VID = 0x0079
IFACE = 0  # adapter port your controller is in


def main() -> int:
    path = None
    for d in hid.enumerate():
        if d.get("vendor_id") == VID and d.get("interface_number") == IFACE:
            path = d["path"]
            break
    if path is None:
        print(f"No VID 0x{VID:04x} interface {IFACE} found (adapter plugged in? Steam quit?)")
        return 1
    h = hid.device()
    h.open_path(path)
    h.set_nonblocking(True)
    print("Press buttons. Showing byte0 / byte1 as bits (bit7..bit0). Ctrl-C to stop.\n")

    last = None
    try:
        while True:
            data = bytes(h.read(64))
            if len(data) >= 9 and data != last:
                b0, b1 = data[0], data[1]
                names = []
                # current best-guess map, for reference
                guess = {(0, 1): "A", (0, 2): "B", (0, 0): "X", (0, 3): "Y", (0, 7): "Z", (1, 1): "START"}
                for (bb, bit), nm in guess.items():
                    if data[bb] & (1 << bit):
                        names.append(nm)
                print(
                    f"byte0={b0:08b}  byte1={b1:08b}  full={data.hex(' ')}"
                    + (f"   [{'+'.join(names)}]" if names else "")
                )
                last = data
            time.sleep(1 / 120)
    except KeyboardInterrupt:
        print("\n[stop]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
