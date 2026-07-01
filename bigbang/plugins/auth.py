from pathlib import Path

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

NAME = "auth"
DESCRIPTION = "JWT auth: User model, register/login/me endpoints, bcrypt passwords, role guards"


class AuthPlugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION
    REQUIRES = ["backend"]

    @classmethod
    def is_active(cls, universe: Universe) -> bool:
        return universe.auth.enabled

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        b = output / "backend"
        return [
            ("backend/auth_models.py.j2",  b / "auth_models.py"),
            ("backend/auth_schemas.py.j2", b / "auth_schemas.py"),
            ("backend/auth_routes.py.j2",  b / "auth_routes.py"),
        ]

    @classmethod
    def pip_requirements(cls, universe: Universe) -> list[str]:
        return ["python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4"]


is_active = AuthPlugin.is_active
get_files = AuthPlugin.get_files
pip_requirements = AuthPlugin.pip_requirements
