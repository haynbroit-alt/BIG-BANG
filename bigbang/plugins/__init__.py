"""
BIG BANG plugin registry.

Plugins are the unit of capability in the compiler pipeline.
Each plugin is a module that implements the BangPlugin interface
(is_active, get_files, pip_requirements).

Built-in plugins are registered at import time.
External plugins are loaded by module name via load_external().
"""
import importlib
from pathlib import Path

from bigbang.universe import Universe


class _Registry:
    def __init__(self):
        self._plugins: dict[str, dict] = {}

    def register(self, module) -> None:
        name = getattr(module, "NAME", module.__name__)
        self._plugins[name] = {
            "name": name,
            "description": getattr(module, "DESCRIPTION", ""),
            "is_active": module.is_active,
            "get_files": module.get_files,
            "pip_requirements": getattr(module, "pip_requirements", lambda u: []),
        }

    def load_external(self, module_name: str) -> None:
        if module_name in self._plugins:
            return
        try:
            self.register(importlib.import_module(module_name))
        except ImportError as exc:
            raise ImportError(
                f"Plugin '{module_name}' not found. "
                f"Install it with: pip install {module_name}"
            ) from exc

    def active_for(self, universe: Universe) -> list[dict]:
        return [p for p in self._plugins.values() if p["is_active"](universe)]

    def all(self) -> list[dict]:
        return list(self._plugins.values())

    def collect_requirements(self, universe: Universe) -> list[str]:
        reqs: list[str] = []
        for p in self.active_for(universe):
            reqs.extend(p["pip_requirements"](universe))
        return reqs


registry = _Registry()


def _register_builtins() -> None:
    from bigbang.plugins import backend, frontend, docker, docs, auth, ed25519
    for mod in (backend, frontend, docker, docs, auth, ed25519):
        registry.register(mod)


_register_builtins()
