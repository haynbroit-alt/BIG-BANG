"""Unit tests for bigbang.resolver — semantic analysis pass."""
import pytest

from bigbang.diagnostics import DiagnosticEngine
from bigbang.resolver import resolve, _find_entity, _topo_sort
from bigbang.universe import Entity, Relation, Universe, UniverseField

from tests.conftest import make_entity, make_field, minimal_universe, crm_universe


# ── _find_entity ──────────────────────────────────────────────────────────────

class TestFindEntity:
    def test_exact_title_case(self):
        assert _find_entity("contact", {"Contact", "Deal"}) == "Contact"

    def test_capitalize(self):
        assert _find_entity("deal", {"Deal"}) == "Deal"

    def test_camel_case_from_snake(self):
        assert _find_entity("sales_rep", {"SalesRep"}) == "SalesRep"

    def test_no_match_returns_none(self):
        assert _find_entity("invoice", {"Contact", "Deal"}) is None

    def test_uppercase(self):
        assert _find_entity("crm", {"CRM"}) == "CRM"


# ── Relation inference ────────────────────────────────────────────────────────

class TestRelationInference:
    def test_contact_id_infers_relation(self, diags):
        deal = make_entity("Deal", fields=[
            make_field("title"),
            make_field("contact_id", "integer"),
        ])
        contact = make_entity("Contact", fields=[make_field("email")])
        u = Universe(name="T", type="api", entities=[contact, deal])

        resolve(u, diags)

        assert len(deal.relations) == 1
        rel = deal.relations[0]
        assert rel.field_name == "contact_id"
        assert rel.target == "Contact"
        assert rel.kind == "many_to_one"

    def test_non_id_field_no_relation(self, diags):
        entity = make_entity("Todo", fields=[make_field("title"), make_field("status")])
        u = Universe(name="T", type="api", entities=[entity])
        resolve(u, diags)
        assert entity.relations == []

    def test_self_referential_id_ignored(self, diags):
        entity = make_entity("Category", fields=[
            make_field("name"),
            make_field("category_id", "integer"),  # self-reference
        ])
        u = Universe(name="T", type="api", entities=[entity])
        resolve(u, diags)
        assert entity.relations == []

    def test_unresolved_id_emits_w001(self, diags):
        entity = make_entity("Deal", fields=[make_field("invoice_id", "integer")])
        u = Universe(name="T", type="api", entities=[entity])
        resolve(u, diags)
        warnings = [d for d in diags.warnings if d.code == "W001"]
        assert len(warnings) == 1
        assert "invoice_id" in warnings[0].message

    def test_resolved_relation_emits_r001(self, diags):
        contact = make_entity("Contact", fields=[make_field("email")])
        deal = make_entity("Deal", fields=[make_field("contact_id", "integer")])
        u = Universe(name="T", type="api", entities=[contact, deal])
        resolve(u, diags)
        infos = [d for d in diags.infos if d.code == "R001"]
        assert len(infos) == 1
        assert "Contact" in infos[0].message

    def test_idempotent(self, diags):
        contact = make_entity("Contact", fields=[make_field("email")])
        deal = make_entity("Deal", fields=[make_field("contact_id", "integer")])
        u = Universe(name="T", type="api", entities=[contact, deal])
        resolve(u, diags)
        resolve(u, diags)
        assert len(deal.relations) == 1

    def test_multiple_relations(self, diags):
        u = crm_universe()
        resolve(u, diags)
        em = u.entity_map
        assert len(em["Activity"].relations) == 2
        targets = {r.target for r in em["Activity"].relations}
        assert targets == {"Deal", "Contact"}


# ── Topological sort ──────────────────────────────────────────────────────────

class TestTopoSort:
    def test_linear_chain(self, diags):
        # Contact ← Deal ← Activity
        graph = {"Contact": [], "Deal": ["Contact"], "Activity": ["Deal"]}
        order = _topo_sort(graph, diags)
        assert order.index("Contact") < order.index("Deal")
        assert order.index("Deal") < order.index("Activity")
        assert not diags.has_errors

    def test_no_dependencies(self, diags):
        graph = {"A": [], "B": [], "C": []}
        order = _topo_sort(graph, diags)
        assert set(order) == {"A", "B", "C"}
        assert not diags.has_errors

    def test_cycle_emits_e010(self, diags):
        graph = {"A": ["B"], "B": ["A"]}
        order = _topo_sort(graph, diags)
        assert set(order) == {"A", "B"}
        errors = [d for d in diags.errors if d.code == "E010"]
        assert len(errors) == 1

    def test_diamond_dependency(self, diags):
        # B and C both depend on A; D depends on B and C
        graph = {"A": [], "B": ["A"], "C": ["A"], "D": ["B", "C"]}
        order = _topo_sort(graph, diags)
        assert order.index("A") < order.index("B")
        assert order.index("A") < order.index("C")
        assert order.index("B") < order.index("D")
        assert order.index("C") < order.index("D")

    def test_resolve_sets_topo_order(self, diags):
        u = crm_universe()
        resolve(u, diags)
        assert "Contact" in u.topo_order
        assert "Deal" in u.topo_order
        assert "Activity" in u.topo_order
        assert u.topo_order.index("Contact") < u.topo_order.index("Deal")
        assert u.topo_order.index("Deal") < u.topo_order.index("Activity")

    def test_ordered_entities_follows_topo_order(self, diags):
        u = crm_universe()
        resolve(u, diags)
        ordered = u.ordered_entities()
        names = [e.name for e in ordered]
        assert names.index("Contact") < names.index("Deal")
        assert names.index("Deal") < names.index("Activity")
