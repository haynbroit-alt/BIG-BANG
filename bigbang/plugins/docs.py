from pathlib import Path

NAME = "docs"
DESCRIPTION = "README.md with API reference table, entity schema, flow steps, pricing"


def is_active(universe: dict) -> bool:
    return True


def get_files(universe: dict, output: Path, ctx: dict) -> list[tuple[str, Path]]:
    return [
        ("docs/README.md.j2", output / "README.md"),
    ]
