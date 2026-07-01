from pathlib import Path

NAME = "frontend"
DESCRIPTION = "Single-page dashboard: HTML, vanilla JS, dark-theme CSS — no build step"


def is_active(universe: dict) -> bool:
    return True


def get_files(universe: dict, output: Path, ctx: dict) -> list[tuple[str, Path]]:
    f = output / "frontend"
    return [
        ("frontend/index.html.j2",      f / "index.html"),
        ("frontend/app.js.j2",          f / "static" / "app.js"),
        ("frontend/styles.css.j2",      f / "static" / "styles.css"),
    ]
