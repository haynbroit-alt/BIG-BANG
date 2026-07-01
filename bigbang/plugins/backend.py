from pathlib import Path

NAME = "backend"
DESCRIPTION = "FastAPI app, SQLAlchemy models, Pydantic schemas, CRUD + flow routes, Dockerfile"


def is_active(universe: dict) -> bool:
    return True


def get_files(universe: dict, output: Path, ctx: dict) -> list[tuple[str, Path]]:
    b = output / "backend"
    return [
        ("backend/app.py.j2",          b / "app.py"),
        ("backend/database.py.j2",     b / "database.py"),
        ("backend/models.py.j2",       b / "models.py"),
        ("backend/schemas.py.j2",      b / "schemas.py"),
        ("backend/routes.py.j2",       b / "routes.py"),
        ("backend/requirements.txt.j2", b / "requirements.txt"),
        ("backend/Dockerfile.j2",      b / "Dockerfile"),
    ]
