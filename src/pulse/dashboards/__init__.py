"""Dashboard modules. Each submodule defines its own layout."""

from importlib import import_module
from types import ModuleType

AVAILABLE: tuple[str, ...] = ("world", "tech")


def load(name: str) -> ModuleType:
    if name not in AVAILABLE:
        raise KeyError(name)
    return import_module(f"pulse.dashboards.{name}")
