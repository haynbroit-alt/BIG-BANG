"""
BIG BANG plugin registry — class-based, dependency-aware.

Each plugin is a BangPlugin subclass that declares:
  NAME        — unique identifier
  DESCRIPTION — human-readable summary
  REQUIRES    — other plugin NAMEs that must run before this one
  is_active() — whether the plugin applies to a given universe
  get_files() — (template, dest) pairs to render
  pip_requirements() — packages the generated code needs

The registry resolves plugin load order via topological sort of REQUIRES.
Unresolved REQUIRES are auto-activated if they exist in the registry.
"""
import importlib
from collections import deque
from pathlib import Path
from typing import Optional

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe


class _Registry:
    def __init__(self) -> None:
        self._classes: dict[str, type[BangPlugin]] = {}

    # ── Registration ──────────────────────────────────────────────────────────

    def register_class(self, cls: type[BangPlugin]) -> None:
        """Register a BangPlugin subclass directly."""
        key = cls.NAME or cls.__name__
        self._classes[key] = cls

    def register(self, module) -> None:
        """Register a plugin from a module — finds the BangPlugin subclass in it."""
        import inspect
        mod_name = getattr(module, "__name__", "")
        for _, obj in inspect.getmembers(module, inspect.isclass):
            if (issubclass(obj, BangPlugin)
                    and obj is not BangPlugin
                    and getattr(obj, "__module__", "") == mod_name):
                self.register_class(obj)
                return
        # Fallback: duck-typed module (NAME, is_active, get_files at module level)
        name = getattr(module, "NAME", mod_name)
        self._classes[name] = _make_compat_class(module)

    def load_external(self, module_name: str) -> None:
        if module_name in self._classes:
            return
        try:
            self.register(importlib.import_module(module_name))
        except ImportError as exc:
            raise ImportError(
                f"Plugin '{module_name}' not found. "
                f"Install it with: pip install {module_name}"
            ) from exc

    # ── Query ─────────────────────────────────────────────────────────────────

    def resolve_order(self, universe: Universe) -> list[dict]:
        """
        Return active plugins as dicts, in dependency-resolved topological order.
        Plugins listed in REQUIRES are auto-activated even if is_active() is False,
        so dependencies are never missing from the emit phase.
        """
        active: dict[str, type[BangPlugin]] = {
            name: cls
            for name, cls in self._classes.items()
            if cls.is_active(universe)
        }

        # Auto-activate declared dependencies
        frontier = list(active.keys())
        while frontier:
            name = frontier.pop()
            cls = self._classes.get(name)
            if not cls:
                continue
            for req in cls.REQUIRES:
                if req not in active and req in self._classes:
                    active[req] = self._classes[req]
                    frontier.append(req)

        # Validate all REQUIRES can be satisfied
        for name, cls in active.items():
            for req in cls.REQUIRES:
                if req not in active:
                    raise ValueError(
                        f"Plugin '{name}' requires '{req}' which is not registered. "
                        f"Install it or add it to your genesis.yaml plugins list."
                    )

        # Topological sort (dependencies first)
        dep_graph = {
            name: [r for r in cls.REQUIRES if r in active]
            for name, cls in active.items()
        }
        order = _topo_sort(dep_graph)
        return [self._to_dict(active[name]) for name in order if name in active]

    def active_for(self, universe: Universe) -> list[dict]:
        """Alias for resolve_order — backward compatible."""
        return self.resolve_order(universe)

    def all(self) -> list[dict]:
        return [self._to_dict(cls) for cls in self._classes.values()]

    def collect_requirements(self, universe: Universe) -> list[str]:
        return [
            req
            for p in self.resolve_order(universe)
            for req in p["pip_requirements"](universe)
        ]

    # ── Internal ──────────────────────────────────────────────────────────────

    def _to_dict(self, cls: type[BangPlugin]) -> dict:
        return {
            "name":             cls.NAME,
            "description":      cls.DESCRIPTION,
            "requires":         list(cls.REQUIRES),
            "is_active":        cls.is_active,
            "get_files":        cls.get_files,
            "pip_requirements": cls.pip_requirements,
            "post_generate":    cls.post_generate,
        }


def _topo_sort(graph: dict[str, list[str]]) -> list[str]:
    """
    Kahn's algorithm.  graph[A] = [B] means A depends on B (B runs first).
    Returns nodes in dependency-first order.
    """
    rev: dict[str, list[str]] = {n: [] for n in graph}
    in_degree: dict[str, int] = {n: 0 for n in graph}

    for node, deps in graph.items():
        for dep in deps:
            if dep in rev:
                rev[dep].append(node)
                in_degree[node] += 1

    queue = deque(n for n, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        n = queue.popleft()
        result.append(n)
        for dependent in rev[n]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    # If cycle, append remaining nodes in arbitrary order
    if len(result) < len(graph):
        result.extend(n for n in graph if n not in set(result))

    return result


def _make_compat_class(module) -> type[BangPlugin]:
    """Wrap a duck-typed module in a minimal BangPlugin subclass."""
    class _Compat(BangPlugin):
        NAME = getattr(module, "NAME", module.__name__)
        DESCRIPTION = getattr(module, "DESCRIPTION", "")
        REQUIRES = getattr(module, "REQUIRES", [])

        @classmethod
        def is_active(cls, universe): return module.is_active(universe)

        @classmethod
        def get_files(cls, universe, output): return module.get_files(universe, output)

        @classmethod
        def pip_requirements(cls, universe):
            fn = getattr(module, "pip_requirements", None)
            return fn(universe) if fn else []

    _Compat.__name__ = module.__name__
    return _Compat


# ── Singleton & built-in registration ─────────────────────────────────────────

registry = _Registry()


def _register_builtins() -> None:
    from bigbang.plugins.backend  import BackendPlugin
    from bigbang.plugins.frontend import FrontendPlugin
    from bigbang.plugins.docker   import DockerPlugin
    from bigbang.plugins.docs     import DocsPlugin
    from bigbang.plugins.auth     import AuthPlugin
    from bigbang.plugins.ed25519  import Ed25519Plugin

    for cls in (BackendPlugin, FrontendPlugin, DockerPlugin, DocsPlugin, AuthPlugin, Ed25519Plugin):
        registry.register_class(cls)


_register_builtins()
