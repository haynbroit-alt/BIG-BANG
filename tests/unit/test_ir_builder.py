"""Unit tests for bigbang.ir_builder — Universe → UniverseGraph seeding."""
import pytest

from bigbang.ir import IREdge, IRNode, UniverseGraph
from bigbang.ir_builder import build_graph
from bigbang.universe import (
    AuthConfig, Flow, FlowStep, Monetization, Plan,
    Relation, Role, Security,
)

from tests.conftest import make_entity, make_field, minimal_universe, crm_universe


# ── Basic structure ───────────────────────────────────────────────────────────

class TestBuildGraphBasic:
    def test_returns_universe_graph(self):
        g = build_graph(minimal_universe())
        assert isinstance(g, UniverseGraph)

    def test_name_and_kind_set(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.name == u.name
        assert g.kind == u.type

    def test_name_slug_in_meta(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.meta["name_slug"] == u.name_slug


# ── Entity nodes ──────────────────────────────────────────────────────────────

class TestEntityNodes:
    def test_entity_nodes_created(self):
        u = minimal_universe()
        g = build_graph(u)
        entity_nodes = g.nodes_of_kind("entity")
        assert len(entity_nodes) == 2

    def test_entity_node_ids(self):
        u = minimal_universe()
        g = build_graph(u)
        ids = {n.id for n in g.nodes_of_kind("entity")}
        assert "entity:todo" in ids
        assert "entity:tag" in ids

    def test_entity_node_data(self):
        u = minimal_universe()
        g = build_graph(u)
        todo_node = g.node("entity:todo")
        assert todo_node is not None
        assert todo_node.data["name"] == "Todo"
        assert todo_node.data["slug"] == "todo"
        fields = todo_node.data["fields"]
        field_names = [f["name"] for f in fields]
        assert "title" in field_names
        assert "done" in field_names

    def test_field_metadata_preserved(self):
        u = minimal_universe()
        g = build_graph(u)
        todo_node = g.node("entity:todo")
        title_field = next(f for f in todo_node.data["fields"] if f["name"] == "title")
        assert title_field["type"] == "string"
        assert title_field["required"] is True
        assert title_field["computed"] is False

    def test_no_entity_nodes_for_empty_universe(self):
        from bigbang.universe import Universe
        u = Universe(name="Empty", type="api")
        g = build_graph(u)
        assert g.nodes_of_kind("entity") == []


# ── Relation edges ────────────────────────────────────────────────────────────

class TestRelationEdges:
    def test_relation_edges_created(self):
        from bigbang.diagnostics import DiagnosticEngine
        from bigbang.resolver import resolve
        u = crm_universe()
        resolve(u, DiagnosticEngine())
        g = build_graph(u)
        relations = g.edges_of_kind("relation")
        assert len(relations) > 0

    def test_deal_to_contact_relation(self):
        from bigbang.diagnostics import DiagnosticEngine
        from bigbang.resolver import resolve
        u = crm_universe()
        resolve(u, DiagnosticEngine())
        g = build_graph(u)
        deal_edges = g.edges_from("entity:deal", kind="relation")
        targets = {e.target for e in deal_edges}
        assert "entity:contact" in targets

    def test_relation_edge_attrs(self):
        from bigbang.diagnostics import DiagnosticEngine
        from bigbang.resolver import resolve
        u = crm_universe()
        resolve(u, DiagnosticEngine())
        g = build_graph(u)
        deal_edges = g.edges_from("entity:deal", kind="relation")
        contact_edge = next(e for e in deal_edges if e.target == "entity:contact")
        assert contact_edge.attrs["field"] == "contact_id"
        assert contact_edge.attrs["cardinality"] == "many_to_one"

    def test_no_relation_edges_without_resolver(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.edges_of_kind("relation") == []


# ── Flow nodes ────────────────────────────────────────────────────────────────

class TestFlowNodes:
    def test_flow_nodes_created(self):
        u = crm_universe()
        g = build_graph(u)
        flow_nodes = g.nodes_of_kind("flow")
        assert len(flow_nodes) == len(u.flows)

    def test_flow_node_data(self):
        u = crm_universe()
        g = build_graph(u)
        flow = next(n for n in g.nodes_of_kind("flow") if "qualify" in n.id)
        assert flow.data["name"] == "qualify_lead"
        assert "steps" in flow.data
        assert len(flow.data["steps"]) > 0

    def test_no_flow_nodes_for_empty_flows(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.nodes_of_kind("flow") == []


# ── Role nodes & permission edges ─────────────────────────────────────────────

class TestRoleNodes:
    def test_role_nodes_created(self):
        u = crm_universe()
        g = build_graph(u)
        role_nodes = g.nodes_of_kind("role")
        assert len(role_nodes) == len(u.roles)

    def test_role_node_data(self):
        u = crm_universe()
        g = build_graph(u)
        admin_node = g.node("role:admin")
        assert admin_node is not None
        assert "delete" in admin_node.data["permissions"]

    def test_permission_edges_created(self):
        u = crm_universe()
        g = build_graph(u)
        perm_edges = g.edges_of_kind("permission")
        assert len(perm_edges) > 0

    def test_permission_edge_structure(self):
        u = crm_universe()
        g = build_graph(u)
        admin_edges = g.edges_from("role:admin", kind="permission")
        assert len(admin_edges) > 0
        for e in admin_edges:
            assert e.target.startswith("entity:")

    def test_no_role_nodes_for_empty_roles(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.nodes_of_kind("role") == []


# ── Monetization node ─────────────────────────────────────────────────────────

class TestMonetizationNode:
    def test_subscription_node_created_when_monetization_set(self):
        u = crm_universe()
        g = build_graph(u)
        assert g.has_billing
        sub_nodes = g.nodes_of_kind("subscription")
        assert len(sub_nodes) == 1

    def test_subscription_node_data(self):
        u = crm_universe()
        g = build_graph(u)
        sub = g.node("billing:subscription")
        assert sub.data["model"] == "subscription"
        assert len(sub.data["plans"]) == 2
        assert sub.data["plans"][0]["name"] == "starter"

    def test_no_subscription_node_when_no_monetization(self):
        u = minimal_universe()
        g = build_graph(u)
        assert not g.has_billing
        assert g.nodes_of_kind("subscription") == []


# ── Meta: auth & security ─────────────────────────────────────────────────────

class TestGraphMeta:
    def test_auth_meta_stored(self):
        u = crm_universe()
        g = build_graph(u)
        assert g.meta["auth"]["enabled"] is True
        assert g.meta["auth"]["provider"] == "jwt"

    def test_security_meta_stored(self):
        u = crm_universe()
        g = build_graph(u)
        assert g.meta["security"]["ed25519"] is True

    def test_no_auth_meta_defaults(self):
        u = minimal_universe()
        g = build_graph(u)
        assert g.meta["auth"]["enabled"] is False

    def test_plugins_meta_stored(self):
        u = minimal_universe()
        u.plugins = ["my_plugin"]
        g = build_graph(u)
        assert "my_plugin" in g.meta["plugins"]


# ── IR predicates before plugin transforms ────────────────────────────────────

class TestPreTransformPredicates:
    def test_has_identity_false_before_auth_plugin(self):
        u = crm_universe()
        g = build_graph(u)
        assert not g.has_identity

    def test_has_ledger_false_before_ed25519_plugin(self):
        u = crm_universe()
        g = build_graph(u)
        assert not g.has_ledger
