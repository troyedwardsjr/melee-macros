"""Load config.yaml into runtime objects."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from .backends import Backend, HybridBackend, LibmeleeBackend, PipeBackend
from .controller import ControllerMap
from .engine import TriggerBinding
from .pipe import default_pipe_path


@dataclass
class AppConfig:
    pipe_path: str
    fps: float
    backend: str  # "pipe", "hybrid", or "libmelee"
    controller: ControllerMap
    triggers: list[TriggerBinding]
    passthrough: bool = True
    libmelee: dict = field(default_factory=dict)
    reactive: bool = True            # prefer closed-loop macros when state is available
    reactive_edgeguard: bool = False  # allow opponent-reading auto edgeguard (autopilot)

    def build_backend(self, on_event=None) -> Backend:
        if self.backend == "libmelee":
            return LibmeleeBackend(
                dolphin_path=self.libmelee["dolphin_path"],
                iso_path=self.libmelee["iso_path"],
                port=self.libmelee.get("port", 1),
            )
        if self.backend == "hybrid":
            return HybridBackend(
                self.pipe_path,
                dolphin_path=self.libmelee["dolphin_path"],
                port=self.libmelee.get("port", 1),
                fps=self.fps,
                on_event=on_event,
            )
        return PipeBackend(self.pipe_path, fps=self.fps)


def load_config(path: str | os.PathLike) -> AppConfig:
    import yaml  # lazy: optional dependency

    with open(os.path.expanduser(str(path))) as fh:
        raw = yaml.safe_load(fh) or {}

    pipe_path = raw.get("pipe_path") or str(default_pipe_path())

    cdata = raw.get("controller", {}) or {}
    driver = cdata.get("driver", "sdl")
    raw_buttons = cdata.get("buttons") or {}
    if driver == "hid_gc":
        # Keys are "byte.bit" strings; keep them as strings for HidGcReader.
        buttons = {str(k): v for k, v in raw_buttons.items()}
        # hid_gc axes are HID report byte indices, not SDL axis indices, so the
        # SDL defaults don't apply — take exactly what config provides.
        axes = dict(cdata.get("axes") or {})
    else:
        buttons = {int(k): v for k, v in raw_buttons.items()}
        axes = {**ControllerMap().axes, **(cdata.get("axes") or {})}
    cmap = ControllerMap(
        index=cdata.get("index", 0),
        deadzone=cdata.get("deadzone", 0.15),
        driver=driver,
        axes=axes,
        buttons=buttons,
        invert={**ControllerMap().invert, **(cdata.get("invert") or {})},
        trigger_min=cdata.get("trigger_min", -1.0),
        trigger_max=cdata.get("trigger_max", 1.0),
        hid_vendor=int(cdata.get("hid_vendor", 0x0079)),
        hid_product=int(cdata.get("hid_product", 0)),
        hid_interface=int(cdata.get("hid_interface", 0)),
        hat_byte=int(cdata.get("hat_byte", 8)),
        l_mod_name=str(cdata.get("l_mod_name", "") or ""),
        l_mod_threshold=float(cdata.get("l_mod_threshold", 0.3)),
    )

    triggers: list[TriggerBinding] = []
    for entry in raw.get("triggers", []) or []:
        # Accept either `buttons:` (list/str) or `hold:` (list/str) as the held set.
        btns = entry.get("buttons", entry.get("hold", []))
        if isinstance(btns, str):
            btns = [btns]
        stick = entry.get("stick")
        if stick is not None:
            stick = str(stick).lower()
        requires = entry.get("requires")
        if requires is not None:
            requires = str(requires).lower()
        triggers.append(
            TriggerBinding(
                frozenset(btns),
                entry["macro"],
                stick=stick,
                stick_threshold=float(entry.get("stick_threshold", 0.5)),
                requires=requires,
            )
        )

    return AppConfig(
        pipe_path=pipe_path,
        fps=float(raw.get("fps", 60)),
        backend=raw.get("backend", "pipe"),
        controller=cmap,
        triggers=triggers,
        passthrough=raw.get("passthrough", True),
        libmelee=raw.get("libmelee", {}) or {},
        reactive=raw.get("reactive", True),
        reactive_edgeguard=raw.get("reactive_edgeguard", False),
    )


def default_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "config.yaml"
