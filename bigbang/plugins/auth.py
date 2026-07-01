from pathlib import Path

NAME = "auth"
DESCRIPTION = "JWT authentication: User model, register/login/me endpoints, password hashing, Bearer tokens"


def is_active(universe: dict) -> bool:
    return bool(universe.get("auth", {}).get("enabled"))


def get_files(universe: dict, output: Path, ctx: dict) -> list[tuple[str, Path]]:
    b = output / "backend"
    return [
        ("backend/auth_models.py.j2",  b / "auth_models.py"),
        ("backend/auth_schemas.py.j2", b / "auth_schemas.py"),
        ("backend/auth_routes.py.j2",  b / "auth_routes.py"),
    ]
