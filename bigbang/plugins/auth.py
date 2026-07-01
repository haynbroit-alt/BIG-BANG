from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

if TYPE_CHECKING:
    from bigbang.ir import UniverseGraph

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
    def transform(cls, graph: "UniverseGraph") -> None:
        """
        Add identity infrastructure to the graph.

        Creates an "identity" node representing the user model and an
        "auth_token" node representing the JWT token scheme. Emitters
        check graph.has_identity to decide whether to generate auth files.
        """
        from bigbang.ir import IREdge, IRNode

        auth_meta = graph.meta.get("auth", {})
        graph.add_node(IRNode(
            id="identity:user",
            kind="identity",
            data={
                "provider": auth_meta.get("provider", "jwt"),
                "fields":   auth_meta.get("user_fields", []),
            },
        ))
        graph.add_node(IRNode(
            id="identity:token",
            kind="auth_token",
            data={"algorithm": "HS256", "expiry_minutes": 30},
        ))
        # The user identity owns all domain entities
        for entity_node in graph.nodes_of_kind("entity"):
            graph.add_edge(IREdge(
                source="identity:user",
                target=entity_node.id,
                kind="owns",
            ))

    @classmethod
    def pip_requirements(cls, universe: Universe) -> list[str]:
        return ["python-jose[cryptography]>=3.3.0", "passlib[bcrypt]>=1.7.4"]


is_active = AuthPlugin.is_active
get_files = AuthPlugin.get_files
pip_requirements = AuthPlugin.pip_requirements
