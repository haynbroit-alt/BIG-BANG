from pathlib import Path

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

NAME = "frontend"
DESCRIPTION = "Single-page dashboard: HTML, vanilla JS, dark-theme CSS — no build step"


class FrontendPlugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        f = output / "frontend"
        return [
            ("frontend/index.html.j2",   f / "index.html"),
            ("frontend/app.js.j2",       f / "static" / "app.js"),
            ("frontend/styles.css.j2",   f / "static" / "styles.css"),
        ]


is_active = FrontendPlugin.is_active
get_files = FrontendPlugin.get_files
pip_requirements = FrontendPlugin.pip_requirements
