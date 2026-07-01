"""Unit tests for bigbang.differ — Universe diff computation."""
import copy

import pytest

from bigbang.differ import diff, FieldDelta, EntityDelta, UniverseDiff
from bigbang.universe import AuthConfig, Flow, FlowStep, Monetization, Plan, Security

from tests.conftest import make_entity, make_field, minimal_universe, crm_universe


# ── Empty diff ────────────────────────────────────────────────────────────────

class TestEmptyDiff:
    def test_identical_universes_are_empty(self):
        u = minimal_universe()
        d = diff(u, copy.deepcopy(u))
        assert d.is_empty
        assert d.summary() == "no changes"

    def test_empty_diff_has_no_entity_deltas(self):
        u = minimal_universe()
        d = diff(u, copy.deepcopy(u))
        assert d.entity_deltas == []

    def test_empty_diff_flags_all_false(self):
        u = minimal_universe()
        d = diff(u, copy.deepcopy(u))
        assert not d.flows_changed
        assert not d.auth_changed
        assert not d.security_changed
        assert not d.monetization_changed
        assert not d.plugins_changed


# ── Entity-level changes ──────────────────────────────────────────────────────

class TestEntityDeltas:
    def test_added_entity(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entities.append(make_entity("Invoice", [make_field("amount", "float")]))
        d = diff(old, new)
        added = [e for e in d.entity_deltas if e.kind == "added"]
        assert len(added) == 1
        assert added[0].name == "Invoice"
        assert not d.is_empty

    def test_removed_entity(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entities = [e for e in new.entities if e.name != "Tag"]
        d = diff(old, new)
        removed = [e for e in d.entity_deltas if e.kind == "removed"]
        assert len(removed) == 1
        assert removed[0].name == "Tag"

    def test_unchanged_entity_produces_no_delta(self):
        u = minimal_universe()
        d = diff(u, copy.deepcopy(u))
        names = [e.name for e in d.entity_deltas]
        assert "Todo" not in names
        assert "Tag" not in names


# ── Field-level changes ───────────────────────────────────────────────────────

class TestFieldDeltas:
    def test_added_field(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entity_map["Todo"].fields.append(make_field("priority", "integer"))
        d = diff(old, new)
        modified = [e for e in d.entity_deltas if e.kind == "modified" and e.name == "Todo"]
        assert len(modified) == 1
        added_fields = [f for f in modified[0].field_deltas if f.kind == "added"]
        assert any(f.name == "priority" for f in added_fields)

    def test_removed_field(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entity_map["Todo"].fields = [f for f in new.entity_map["Todo"].fields if f.name != "done"]
        d = diff(old, new)
        modified = [e for e in d.entity_deltas if e.name == "Todo"]
        assert len(modified) == 1
        removed_fields = [f for f in modified[0].field_deltas if f.kind == "removed"]
        assert any(f.name == "done" for f in removed_fields)

    def test_modified_field_type(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        for f in new.entity_map["Todo"].fields:
            if f.name == "done":
                f.type = "string"  # was boolean
        d = diff(old, new)
        modified_entity = next(e for e in d.entity_deltas if e.name == "Todo")
        modified_fields = [f for f in modified_entity.field_deltas if f.kind == "modified"]
        assert any(f.name == "done" for f in modified_fields)

    def test_modified_field_required_flag(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        for f in new.entity_map["Todo"].fields:
            if f.name == "title":
                f.required = False
        d = diff(old, new)
        modified_entity = next(e for e in d.entity_deltas if e.name == "Todo")
        assert any(f.name == "title" for f in modified_entity.field_deltas)


# ── Cross-cutting changes ─────────────────────────────────────────────────────

class TestCrossCuttingChanges:
    def test_flows_changed(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.flows.append(Flow(name="new_flow", trigger="on_create",
                              steps=[FlowStep(action="notify")]))
        d = diff(old, new)
        assert d.flows_changed

    def test_auth_enabled_changed(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.auth = AuthConfig(enabled=True, provider="jwt")
        d = diff(old, new)
        assert d.auth_changed

    def test_auth_provider_changed(self):
        old = minimal_universe()
        old.auth = AuthConfig(enabled=True, provider="jwt")
        new = copy.deepcopy(old)
        new.auth.provider = "jwt"  # same
        d = diff(old, new)
        assert not d.auth_changed

    def test_security_changed(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.security = Security(ed25519=True)
        d = diff(old, new)
        assert d.security_changed

    def test_monetization_added(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.monetization = Monetization(model="subscription",
                                        plans=[Plan("starter", 29, "USD")])
        d = diff(old, new)
        assert d.monetization_changed

    def test_plugins_changed(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.plugins = ["custom_plugin"]
        d = diff(old, new)
        assert d.plugins_changed


# ── Summary ───────────────────────────────────────────────────────────────────

class TestDiffSummary:
    def test_summary_no_changes(self):
        u = minimal_universe()
        assert diff(u, copy.deepcopy(u)).summary() == "no changes"

    def test_summary_added_entity(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entities.append(make_entity("Invoice"))
        s = diff(old, new).summary()
        assert "+1" in s
        assert "Invoice" in s

    def test_summary_removed_entity(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entities = [e for e in new.entities if e.name != "Tag"]
        s = diff(old, new).summary()
        assert "-1" in s
        assert "Tag" in s

    def test_summary_flows_changed(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.flows.append(Flow("f", "t", [FlowStep("a")]))
        s = diff(old, new).summary()
        assert "flows" in s


# ── affected_templates ────────────────────────────────────────────────────────

class TestAffectedTemplates:
    def test_entity_change_affects_backend(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.entities.append(make_entity("Invoice"))
        d = diff(old, new)
        assert "backend/models.py" in d.affected_templates
        assert "backend/routes.py" in d.affected_templates

    def test_auth_change_affects_auth_files(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.auth = AuthConfig(enabled=True)
        d = diff(old, new)
        assert "backend/auth_routes.py" in d.affected_templates

    def test_security_change_affects_ledger(self):
        old = minimal_universe()
        new = copy.deepcopy(old)
        new.security = Security(ed25519=True)
        d = diff(old, new)
        assert "backend/ledger.py" in d.affected_templates

    def test_empty_diff_no_affected_templates(self):
        u = minimal_universe()
        d = diff(u, copy.deepcopy(u))
        assert d.affected_templates == set()
