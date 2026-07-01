"""
BIG BANG Universe IR — the single source of truth.

The UniverseGraph is a typed, mutable directed graph that flows through
the compiler pipeline:

    genesis.yaml → Universe (parsed) → UniverseGraph (raw)
                                              ↓
                                    Plugin.transform()  ×N
                                              ↓
                                    UniverseGraph (enriched)
                                              ↓
                                    Emitter.get_pairs()  ×N
                                              ↓
                                    Filesystem output

Everything passes through one graph. Plugins add nodes and edges.
Emitters read the final graph and decide what to generate.
No plugin knows about FastAPI, React, or Docker. No emitter knows
about auth or billing. Isolation is structural, not conventional.
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class IRNode:
    """
    A node in the universe graph.

    kind   — semantic type (e.g. "entity", "identity", "proof_ledger",
              "subscription", "service", "runtime", "flow", "role")
    data   — arbitrary payload, structure defined by the producer
    """
    id: str
    kind: str
    data: dict = field(default_factory=dict)

    def get(self, key: str, default=None):
        return self.data.get(key, default)

    def __getitem__(self, key: str):
        return self.data[key]


@dataclass
class IREdge:
    """
    A directed edge between two nodes.

    kind — semantic relationship (e.g. "relation", "permission",
           "signs", "owns", "depends_on", "provides")
    """
    source: str
    target: str
    kind: str
    attrs: dict = field(default_factory=dict)


class UniverseGraph:
    """
    Mutable IR graph — the only object that crosses phase boundaries.

    Plugins mutate it (transform phase).
    Emitters read it (emit phase).
    The graph is the contract between the two.
    """

    def __init__(self, name: str, kind: str, meta: dict | None = None) -> None:
        self.name = name
        self.kind = kind            # universe type: "saas", "api", etc.
        self.meta: dict = meta or {}
        self._nodes: dict[str, IRNode] = {}
        self._edges: list[IREdge] = []

    # ── Mutation API (plugins write here) ─────────────────────────────────────

    def add_node(self, node: IRNode) -> "UniverseGraph":
        self._nodes[node.id] = node
        return self

    def add_edge(self, edge: IREdge) -> "UniverseGraph":
        self._edges.append(edge)
        return self

    def set_meta(self, key: str, value) -> "UniverseGraph":
        self.meta[key] = value
        return self

    # ── Query API (emitters read here) ────────────────────────────────────────

    def node(self, node_id: str) -> Optional[IRNode]:
        return self._nodes.get(node_id)

    def has_node(self, node_id: str) -> bool:
        return node_id in self._nodes

    def nodes_of_kind(self, kind: str) -> list[IRNode]:
        return [n for n in self._nodes.values() if n.kind == kind]

    def all_nodes(self) -> list[IRNode]:
        return list(self._nodes.values())

    def edges_of_kind(self, kind: str) -> list[IREdge]:
        return [e for e in self._edges if e.kind == kind]

    def edges_from(self, source: str, kind: str | None = None) -> list[IREdge]:
        return [e for e in self._edges
                if e.source == source and (kind is None or e.kind == kind)]

    def edges_to(self, target: str, kind: str | None = None) -> list[IREdge]:
        return [e for e in self._edges
                if e.target == target and (kind is None or e.kind == kind)]

    # ── Semantic shortcuts (emitters use these predicates) ────────────────────

    @property
    def entity_nodes(self) -> list[IRNode]:
        return self.nodes_of_kind("entity")

    @property
    def has_identity(self) -> bool:
        """True after AuthPlugin.transform() runs."""
        return bool(self.nodes_of_kind("identity"))

    @property
    def has_ledger(self) -> bool:
        """True after Ed25519Plugin.transform() runs."""
        return bool(self.nodes_of_kind("proof_ledger"))

    @property
    def has_billing(self) -> bool:
        """True after BillingPlugin.transform() runs."""
        return bool(self.nodes_of_kind("subscription"))

    @property
    def name_slug(self) -> str:
        return self.meta.get("name_slug", self.name.lower().replace(" ", "_").replace("-", "_"))

    def __repr__(self) -> str:
        n = len(self._nodes)
        e = len(self._edges)
        return f"UniverseGraph({self.name!r}, nodes={n}, edges={e})"
