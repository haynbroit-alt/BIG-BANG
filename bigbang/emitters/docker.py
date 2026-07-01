"""
Docker Emitter — generates container runtime configuration from the IR graph.

Reads the runtime:docker node (added by DockerPlugin.transform()) and
the billing:subscription node to decide whether to include Postgres.
"""
from pathlib import Path

from bigbang.emitter import BangEmitter
from bigbang.ir import UniverseGraph


class DockerEmitter(BangEmitter):
    NAME = "docker"
    DESCRIPTION = "docker-compose.yml (SQLite default; Postgres with billing), .env.example"

    @classmethod
    def get_pairs(cls, graph: UniverseGraph, output: Path) -> list[tuple[str, Path]]:
        return [
            ("docker/docker-compose.yml.j2", output / "docker-compose.yml"),
            ("docker/env.example.j2",        output / ".env.example"),
        ]
