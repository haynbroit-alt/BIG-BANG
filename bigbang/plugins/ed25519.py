from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

if TYPE_CHECKING:
    from bigbang.ir import UniverseGraph

NAME = "ed25519"
DESCRIPTION = "Cryptographic proof ledger: Ed25519 signatures, action timestamping, verification API"


class Ed25519Plugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION
    REQUIRES = ["backend"]

    @classmethod
    def is_active(cls, universe: Universe) -> bool:
        return universe.security.ed25519

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        b = output / "backend"
        return [
            ("backend/ledger.py.j2",        b / "ledger.py"),
            ("backend/ledger_routes.py.j2", b / "ledger_routes.py"),
        ]

    @classmethod
    def transform(cls, graph: "UniverseGraph") -> None:
        """
        Add cryptographic proof infrastructure to the graph.

        Creates a "proof_ledger" node encoding the Ed25519 signing scheme
        and signing edges to every entity node. Emitters check
        graph.has_ledger to decide whether to generate ledger files.
        """
        from bigbang.ir import IREdge, IRNode

        graph.add_node(IRNode(
            id="security:ledger",
            kind="proof_ledger",
            data={
                "algorithm":   "Ed25519",
                "key_file":    f"{graph.name_slug}.key",
                "ledger_file": f"{graph.name_slug}.ledger.jsonl",
                "endpoints": [
                    "POST /ledger/sign",
                    "POST /ledger/verify",
                    "GET  /ledger/entries",
                    "GET  /ledger/public-key",
                ],
            },
        ))
        # The ledger signs every entity action
        for entity_node in graph.nodes_of_kind("entity"):
            graph.add_edge(IREdge(
                source="security:ledger",
                target=entity_node.id,
                kind="signs",
            ))

    @classmethod
    def pip_requirements(cls, universe: Universe) -> list[str]:
        return ["cryptography>=42.0.0"]


is_active = Ed25519Plugin.is_active
get_files = Ed25519Plugin.get_files
pip_requirements = Ed25519Plugin.pip_requirements
