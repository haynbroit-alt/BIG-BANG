"""
BIG BANG Emitter Registry — manages the output layer of the compiler.

Emitters are the only components that know about output formats.
Plugins add semantic nodes to the IR graph.
Emitters read the final graph and produce (template, path) pairs.

Registered emitters run in declaration order. To add a NestJS backend,
register a NestJSEmitter that reads the same graph — zero plugin changes.
"""
from bigbang.emitter import BangEmitter
from bigbang.ir import UniverseGraph


class _EmitterRegistry:
    def __init__(self) -> None:
        self._emitters: dict[str, type[BangEmitter]] = {}

    def register(self, cls: type[BangEmitter]) -> None:
        self._emitters[cls.NAME] = cls

    def active_for(self, graph: UniverseGraph) -> list[type[BangEmitter]]:
        return [cls for cls in self._emitters.values() if cls.should_emit(graph)]

    def all(self) -> list[type[BangEmitter]]:
        return list(self._emitters.values())

    def collect_requirements(self, graph: UniverseGraph) -> list[str]:
        return [
            req
            for cls in self.active_for(graph)
            for req in cls.pip_requirements(graph)
        ]


emitter_registry = _EmitterRegistry()


def _register_builtins() -> None:
    from bigbang.emitters.fastapi   import FastAPIEmitter
    from bigbang.emitters.frontend  import StaticFrontendEmitter
    from bigbang.emitters.docker    import DockerEmitter
    from bigbang.emitters.docs      import DocsEmitter

    for cls in (FastAPIEmitter, StaticFrontendEmitter, DockerEmitter, DocsEmitter):
        emitter_registry.register(cls)


_register_builtins()
