"""Macro registry."""

from __future__ import annotations

from .macro import Macro


class MacroLibrary:
    def __init__(self) -> None:
        self._macros: dict[str, Macro] = {}

    def add(self, macro: Macro) -> Macro:
        if macro.name in self._macros:
            raise ValueError(f"duplicate macro name {macro.name!r}")
        self._macros[macro.name] = macro
        return macro

    def get(self, name: str) -> Macro:
        return self._macros[name]

    def __contains__(self, name: str) -> bool:
        return name in self._macros

    def names(self) -> list[str]:
        return sorted(self._macros)

    def __iter__(self):
        return iter(self._macros.values())


def build_fox_library() -> MacroLibrary:
    from .macros.fox import register_fox_macros

    lib = MacroLibrary()
    register_fox_macros(lib)
    return lib
