"""
BIG BANG plugin system.

A plugin is any Python module that exports:
    NAME        str                 Unique identifier
    is_active   (universe) -> bool  Whether to run for this universe
    get_files   (universe, output, ctx) -> list[(template_name, Path)]
                                    Template + destination pairs to render

Built-in plugins are registered here. External plugins are loaded by name
via importlib when listed under `plugins:` in genesis.yaml.
"""
import importlib
from pathlib import Path
from typing import Callable

# Plugin interface type hints
IsActiveFn = Callable[[dict], bool]
GetFilesFn = Callable[[dict, Path, dict], list[tuple[str, Path]]]


class _Registry:
    def __init__(self):
        self._plugins: dict[str, dict] = {}

    def register(self, module) -> None:
        name = getattr(module, "NAME", module.__name__)
        self._plugins[name] = {
            "name": name,
            "is_active": module.is_active,
            "get_files": module.get_files,
            "description": getattr(module, "DESCRIPTION", ""),
        }

    def load_external(self, module_name: str) -> None:
        try:
            mod = importlib.import_module(module_name)
            self.register(mod)
        except ImportError as exc:
            raise ImportError(
                f"Plugin '{module_name}' not found. "
                f"Install it with: pip install {module_name}"
            ) from exc

    def active_for(self, universe: dict) -> list[dict]:
        return [p for p in self._plugins.values() if p["is_active"](universe)]

    def all(self) -> list[dict]:
        return list(self._plugins.values())


registry = _Registry()


def _register_builtins() -> None:
    from bigbang.plugins import backend, frontend, docker, docs, auth
    for mod in (backend, frontend, docker, docs, auth):
        registry.register(mod)


_register_builtins()
