"""
Docs Emitter — generates human-readable documentation from the IR graph.

Reads entity nodes, flow nodes, and billing nodes to produce a README
with API reference, entity schema, flow diagram, and pricing table.
"""
from pathlib import Path

from bigbang.emitter import BangEmitter
from bigbang.ir import UniverseGraph


class DocsEmitter(BangEmitter):
    NAME = "docs"
    DESCRIPTION = "README.md with API reference, entity schema, flow steps, pricing table"

    @classmethod
    def get_pairs(cls, graph: UniverseGraph, output: Path) -> list[tuple[str, Path]]:
        return [("docs/README.md.j2", output / "README.md")]
