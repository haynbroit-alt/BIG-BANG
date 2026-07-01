"""
Static Frontend Emitter — generates the single-page dashboard from the IR graph.

Produces HTML, vanilla JS, and CSS — no build step required.
The templates read entity and flow data from the universe context to
generate a functional dashboard for the compiled universe.
"""
from pathlib import Path

from bigbang.emitter import BangEmitter
from bigbang.ir import UniverseGraph


class StaticFrontendEmitter(BangEmitter):
    NAME = "static-frontend"
    DESCRIPTION = "Single-page dashboard: HTML, vanilla JS, dark-theme CSS — no build step"

    @classmethod
    def get_pairs(cls, graph: UniverseGraph, output: Path) -> list[tuple[str, Path]]:
        f = output / "frontend"
        return [
            ("frontend/index.html.j2", f / "index.html"),
            ("frontend/app.js.j2",     f / "static" / "app.js"),
            ("frontend/styles.css.j2", f / "static" / "styles.css"),
        ]
