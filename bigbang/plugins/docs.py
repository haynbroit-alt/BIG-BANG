from pathlib import Path

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

NAME = "docs"
DESCRIPTION = "README.md with API reference, entity schema, flow steps, pricing table"


class DocsPlugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        return [("docs/README.md.j2", output / "README.md")]


is_active = DocsPlugin.is_active
get_files = DocsPlugin.get_files
pip_requirements = DocsPlugin.pip_requirements
