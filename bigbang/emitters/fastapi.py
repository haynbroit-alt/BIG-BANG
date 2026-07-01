"""
FastAPI Emitter — generates the Python backend from the IR graph.

Reads the final graph to decide which files to include:
- Core backend files always emitted (entities, schemas, routes, app)
- Identity infrastructure included when graph.has_identity (AuthPlugin ran)
- Proof ledger included when graph.has_ledger (Ed25519Plugin ran)
- Billing routes included when graph.has_billing (subscriptions in graph)
"""
from pathlib import Path

from bigbang.emitter import BangEmitter
from bigbang.ir import UniverseGraph


class FastAPIEmitter(BangEmitter):
    NAME = "fastapi"
    DESCRIPTION = "FastAPI app, SQLAlchemy models, Pydantic schemas, CRUD routes, Dockerfile"

    @classmethod
    def get_pairs(cls, graph: UniverseGraph, output: Path) -> list[tuple[str, Path]]:
        b = output / "backend"
        pairs: list[tuple[str, Path]] = [
            ("backend/app.py.j2",           b / "app.py"),
            ("backend/database.py.j2",      b / "database.py"),
            ("backend/models.py.j2",        b / "models.py"),
            ("backend/schemas.py.j2",       b / "schemas.py"),
            ("backend/routes.py.j2",        b / "routes.py"),
            ("backend/requirements.txt.j2", b / "requirements.txt"),
            ("backend/Dockerfile.j2",       b / "Dockerfile"),
        ]

        # Auth infrastructure — added to graph by AuthPlugin.transform()
        if graph.has_identity:
            pairs += [
                ("backend/auth_models.py.j2",  b / "auth_models.py"),
                ("backend/auth_schemas.py.j2", b / "auth_schemas.py"),
                ("backend/auth_routes.py.j2",  b / "auth_routes.py"),
            ]

        # Proof ledger — added to graph by Ed25519Plugin.transform()
        if graph.has_ledger:
            pairs += [
                ("backend/ledger.py.j2",        b / "ledger.py"),
                ("backend/ledger_routes.py.j2", b / "ledger_routes.py"),
            ]

        return pairs

    @classmethod
    def pip_requirements(cls, graph: UniverseGraph) -> list[str]:
        reqs = [
            "fastapi>=0.111.0",
            "uvicorn[standard]>=0.29.0",
            "sqlalchemy>=2.0.30",
            "pydantic>=2.7.0",
            "pydantic[email]>=2.7.0",
            "python-multipart>=0.0.9",
            "python-dotenv>=1.0.1",
        ]
        if graph.has_identity:
            reqs += ["python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4"]
        if graph.has_ledger:
            reqs.append("cryptography>=42.0.0")
        if graph.has_billing:
            reqs.append("stripe>=9.12.0")
        return reqs
