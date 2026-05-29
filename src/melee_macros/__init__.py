"""melee_macros: one-button competitive Fox tech for Slippi/Dolphin.

Public API:
    build_fox_library() -> MacroLibrary
    Macro, MacroBuilder, MacroPlayer
    ControllerState
    Engine, TriggerBinding
    PipeBackend, LibmeleeBackend, DolphinPipe
    load_config
"""

from .backends import LibmeleeBackend, PipeBackend
from .config import AppConfig, load_config
from .controller import ControllerMap, ControllerReader
from .engine import Engine, TriggerBinding
from .inputs import ControllerState
from .library import MacroLibrary, build_fox_library
from .macro import Macro, MacroBuilder, MacroPlayer
from .pipe import DolphinPipe, default_pipe_path

__all__ = [
    "AppConfig",
    "ControllerMap",
    "ControllerReader",
    "ControllerState",
    "DolphinPipe",
    "Engine",
    "LibmeleeBackend",
    "Macro",
    "MacroBuilder",
    "MacroLibrary",
    "MacroPlayer",
    "PipeBackend",
    "TriggerBinding",
    "build_fox_library",
    "default_pipe_path",
    "load_config",
]
