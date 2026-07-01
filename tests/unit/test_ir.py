"""Unit tests for bigbang.ir — IRNode, IREdge, UniverseGraph."""
import pytest

from bigbang.ir import IREdge, IRNode, UniverseGraph


# ── IRNode ────────────────────────────────────────────────────────────────────

class TestIRNode:
    def test_basic_creation(self):
        n = IRNode(id="entity:foo", kind="entity", data={"name": "Foo"})
        assert n.id == "entity:foo"
        assert n.kind == "entity"
        assert n.data == {"name": "Foo"}

    def test_get_existing_key(self):
        n = IRNode(id="x", kind="entity", data={"name": "X", "count": 3})
        assert n.get("name") == "X"
        assert n.get("count") == 3

    def test_get_missing_key_default(self):
        n = IRNode(id="x", kind="entity")
        assert n.get("missing") is None
        assert n.get("missing", 42) == 42

    def test_getitem(self):
        n = IRNode(id="x", kind="entity", data={"slug": "x_slug"})
        assert n["slug"] == "x_slug"

    def test_getitem_missing_raises(self):
        n = IRNode(id="x", kind="entity")
        with pytest.raises(KeyError):
            _ = n["nonexistent"]

    def test_default_data_is_empty_dict(self):
        n = IRNode(id="x", kind="entity")
        assert n.data == {}


# ── IREdge ────────────────────────────────────────────────────────────────────

class TestIREdge:
    def test_basic_creation(self):
        e = IREdge(source="entity:a", target="entity:b", kind="relation")
        assert e.source == "entity:a"
        assert e.target == "entity:b"
        assert e.kind == "relation"
        assert e.attrs == {}

    def test_attrs(self):
        e = IREdge(source="a", target="b", kind="signs",
                   attrs={"algorithm": "Ed25519"})
        assert e.attrs["algorithm"] == "Ed25519"


# ── UniverseGraph ─────────────────────────────────────────────────────────────

class TestUniverseGraph:
    def _graph(self):
        return UniverseGraph(name="Test", kind="api")

    def test_empty_graph(self):
        g = self._graph()
        assert g.name == "Test"
        assert g.kind == "api"
        assert g.all_nodes() == []
        assert g.edges_of_kind("relation") == []

    def test_add_node_returns_self(self):
        g = self._graph()
        n = IRNode(id="entity:foo", kind="entity")
        result = g.add_node(n)
        assert result is g

    def test_add_node_stores_node(self):
        g = self._graph()
        n = IRNode(id="entity:foo", kind="entity", data={"name": "Foo"})
        g.add_node(n)
        assert g.node("entity:foo") is n

    def test_add_node_last_write_wins(self):
        g = self._graph()
        g.add_node(IRNode(id="entity:foo", kind="entity", data={"v": 1}))
        g.add_node(IRNode(id="entity:foo", kind="entity", data={"v": 2}))
        assert g.node("entity:foo").data["v"] == 2

    def test_has_node(self):
        g = self._graph()
        g.add_node(IRNode(id="entity:foo", kind="entity"))
        assert g.has_node("entity:foo")
        assert not g.has_node("entity:bar")

    def test_add_edge_returns_self(self):
        g = self._graph()
        e = IREdge(source="a", target="b", kind="relation")
        result = g.add_edge(e)
        assert result is g

    def test_edges_of_kind(self):
        g = self._graph()
        g.add_edge(IREdge(source="a", target="b", kind="relation"))
        g.add_edge(IREdge(source="c", target="d", kind="signs"))
        g.add_edge(IREdge(source="e", target="f", kind="relation"))

        relations = g.edges_of_kind("relation")
        assert len(relations) == 2
        assert all(e.kind == "relation" for e in relations)

        signs = g.edges_of_kind("signs")
        assert len(signs) == 1

    def test_edges_from(self):
        g = self._graph()
        g.add_edge(IREdge(source="a", target="b", kind="relation"))
        g.add_edge(IREdge(source="a", target="c", kind="owns"))
        g.add_edge(IREdge(source="x", target="b", kind="relation"))

        edges = g.edges_from("a")
        assert len(edges) == 2

        filtered = g.edges_from("a", kind="owns")
        assert len(filtered) == 1
        assert filtered[0].target == "c"

    def test_edges_to(self):
        g = self._graph()
        g.add_edge(IREdge(source="a", target="z", kind="relation"))
        g.add_edge(IREdge(source="b", target="z", kind="relation"))
        g.add_edge(IREdge(source="c", target="y", kind="relation"))

        edges = g.edges_to("z")
        assert len(edges) == 2
        edges_kind = g.edges_to("z", kind="signs")
        assert len(edges_kind) == 0

    def test_nodes_of_kind(self):
        g = self._graph()
        g.add_node(IRNode(id="entity:a", kind="entity"))
        g.add_node(IRNode(id="entity:b", kind="entity"))
        g.add_node(IRNode(id="identity:user", kind="identity"))

        entities = g.nodes_of_kind("entity")
        assert len(entities) == 2

        identities = g.nodes_of_kind("identity")
        assert len(identities) == 1

    def test_entity_nodes_property(self):
        g = self._graph()
        g.add_node(IRNode(id="entity:x", kind="entity"))
        g.add_node(IRNode(id="service:api", kind="service"))
        assert len(g.entity_nodes) == 1
        assert g.entity_nodes[0].id == "entity:x"


# ── Semantic predicates ───────────────────────────────────────────────────────

class TestUniverseGraphPredicates:
    def _graph(self):
        return UniverseGraph(name="Test", kind="api")

    def test_has_identity_false_by_default(self):
        assert not self._graph().has_identity

    def test_has_identity_true_after_adding_identity_node(self):
        g = self._graph()
        g.add_node(IRNode(id="identity:user", kind="identity"))
        assert g.has_identity

    def test_has_ledger_false_by_default(self):
        assert not self._graph().has_ledger

    def test_has_ledger_true_after_adding_proof_ledger(self):
        g = self._graph()
        g.add_node(IRNode(id="security:ledger", kind="proof_ledger"))
        assert g.has_ledger

    def test_has_billing_false_by_default(self):
        assert not self._graph().has_billing

    def test_has_billing_true_after_adding_subscription(self):
        g = self._graph()
        g.add_node(IRNode(id="billing:subscription", kind="subscription"))
        assert g.has_billing

    def test_name_slug_from_meta(self):
        g = UniverseGraph(name="SwiftCRM", kind="saas", meta={"name_slug": "swift_crm"})
        assert g.name_slug == "swift_crm"

    def test_name_slug_fallback(self):
        g = UniverseGraph(name="My App", kind="api")
        assert g.name_slug == "my_app"

    def test_set_meta(self):
        g = self._graph()
        g.set_meta("version", "1.0")
        assert g.meta["version"] == "1.0"

    def test_repr(self):
        g = self._graph()
        g.add_node(IRNode(id="x", kind="entity"))
        g.add_edge(IREdge(source="x", target="y", kind="relation"))
        r = repr(g)
        assert "nodes=1" in r
        assert "edges=1" in r
