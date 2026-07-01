from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

if TYPE_CHECKING:
    from bigbang.ir import UniverseGraph

NAME = "backend"
DESCRIPTION = "FastAPI app, SQLAlchemy models, Pydantic schemas, CRUD + flow routes, Dockerfile"


class BackendPlugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION

    @classmethod
    def transform(cls, graph: "UniverseGraph") -> None:
        from bigbang.ir import IRNode
        graph.add_node(IRNode(
            id="service:api",
            kind="service",
            data={"framework": "fastapi", "language": "python", "port": 8000},
        ))

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        b = output / "backend"
        return [
            ("backend/app.py.j2",           b / "app.py"),
            ("backend/database.py.j2",      b / "database.py"),
            ("backend/models.py.j2",        b / "models.py"),
            ("backend/schemas.py.j2",       b / "schemas.py"),
            ("backend/routes.py.j2",        b / "routes.py"),
            ("backend/requirements.txt.j2", b / "requirements.txt"),
            ("backend/Dockerfile.j2",       b / "Dockerfile"),
        ]


# Module-level aliases so the registry can import without instantiating
is_active = BackendPlugin.is_active
get_files = BackendPlugin.get_files
pip_requirements = BackendPlugin.pip_requirements
