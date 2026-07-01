from pathlib import Path

NAME = "docker"
DESCRIPTION = "docker-compose.yml (SQLite default; Postgres when monetization is defined), .env.example"


def is_active(universe: dict) -> bool:
    return True


def get_files(universe: dict, output: Path, ctx: dict) -> list[tuple[str, Path]]:
    return [
        ("docker/docker-compose.yml.j2", output / "docker-compose.yml"),
        ("docker/env.example.j2",        output / ".env.example"),
    ]
