from pathlib import Path

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

NAME = "docker"
DESCRIPTION = "docker-compose.yml (SQLite default; Postgres with monetization), .env.example"


class DockerPlugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        return [
            ("docker/docker-compose.yml.j2", output / "docker-compose.yml"),
            ("docker/env.example.j2",        output / ".env.example"),
        ]


is_active = DockerPlugin.is_active
get_files = DockerPlugin.get_files
pip_requirements = DockerPlugin.pip_requirements
