"""Unit tests for bigbang.serializers."""
import pytest

from bigbang import pipeline as pp
from bigbang import serializers as ser
from bigbang.diagnostics import Diagnostic, DiagnosticEngine, Level
from bigbang.pipeline import CompilationResult, PhaseResult
from bigbang.universe import (
    AuthConfig, Entity, Flow, FlowStep, Monetization, Plan,
    Relation, Role, Security, Universe, UniverseField,
)

from tests.conftest import make_entity, make_field, minimal_universe, crm_universe


# ── diagnostic ────────────────────────────────────────────────────────────────

class TestDiagnosticSerializer:
    def test_info(self):
        d = Diagnostic(Level.INFO, "R001", "Relation inferred")
        out = ser.diagnostic(d)
        assert out["level"] == "info"
        assert out["code"] == "R001"
        assert out["message"] == "Relation inferred"
        assert "path" not in out
        assert "hint" not in out

    def test_warning_with_path(self):
        d = Diagnostic(Level.WARNING, "W001", "Unresolved FK", path="entities[Deal]")
        out = ser.diagnostic(d)
        assert out["level"] == "warning"
        assert out["path"] == "entities[Deal]"

    def test_error_with_hint(self):
        d = Diagnostic(Level.ERROR, "E000", "Parse failed", hint="Check YAML syntax")
        out = ser.diagnostic(d)
        assert out["level"] == "error"
        assert out["hint"] == "Check YAML syntax"


# ── universe ──────────────────────────────────────────────────────────────────

class TestUniverseSerializer:
    def test_basic_fields(self):
        u = minimal_universe()
        out = ser.universe(u)
        assert out["name"] == "TestApp"
        assert out["name_slug"] == "testapp"
        assert out["type"] == "api"
        assert out["dsl_version"] == "1.0"

    def test_entities(self):
        u = minimal_universe()
        out = ser.universe(u)
        assert len(out["entities"]) == 2
        todo = next(e for e in out["entities"] if e["name"] == "Todo")
        assert todo["slug"] == "todo"
        assert len(todo["fields"]) >= 2

    def test_field_metadata(self):
        u = minimal_universe()
        out = ser.universe(u)
        todo = next(e for e in out["entities"] if e["name"] == "Todo")
        title = next(f for f in todo["fields"] if f["name"] == "title")
        assert title["type"] == "string"
        assert title["required"] is True
        assert title["computed"] is False

    def test_relations_empty_before_resolver(self):
        u = minimal_universe()
        out = ser.universe(u)
        for e in out["entities"]:
            assert e["relations"] == []

    def test_relations_after_resolver(self):
        from bigbang.resolver import resolve
        u = crm_universe()
        resolve(u, DiagnosticEngine())
        out = ser.universe(u)
        deal = next(e for e in out["entities"] if e["name"] == "Deal")
        assert len(deal["relations"]) == 1
        rel = deal["relations"][0]
        assert rel["target"] == "Contact"
        assert rel["kind"] == "many_to_one"
        assert rel["field_name"] == "contact_id"

    def test_auth(self):
        u = crm_universe()
        out = ser.universe(u)
        assert out["auth"]["enabled"] is True
        assert out["auth"]["provider"] == "jwt"

    def test_security(self):
        u = crm_universe()
        out = ser.universe(u)
        assert out["security"]["ed25519"] is True

    def test_monetization(self):
        u = crm_universe()
        out = ser.universe(u)
        m = out["monetization"]
        assert m is not None
        assert m["model"] == "subscription"
        assert len(m["plans"]) == 2
        assert m["plans"][0]["name"] == "starter"

    def test_no_monetization_is_none(self):
        u = minimal_universe()
        out = ser.universe(u)
        assert out["monetization"] is None

    def test_flows(self):
        u = crm_universe()
        out = ser.universe(u)
        assert len(out["flows"]) > 0
        flow = out["flows"][0]
        assert "name" in flow
        assert "steps" in flow

    def test_topo_order_empty_before_resolver(self):
        u = minimal_universe()
        out = ser.universe(u)
        assert out["topo_order"] == []


# ── phase ─────────────────────────────────────────────────────────────────────

class TestPhaseSerializer:
    def test_basic(self):
        p = PhaseResult("Parse", 12.345, "TodoAPI · api · 2 entities")
        out = ser.phase(p)
        assert out["name"] == "Parse"
        assert out["duration_ms"] == 12.35
        assert "TodoAPI" in out["note"]

    def test_empty_note(self):
        p = PhaseResult("Build", 1.0)
        out = ser.phase(p)
        assert out["note"] == ""


# ── compilation_result ────────────────────────────────────────────────────────

class TestCompilationResultSerializer:
    @pytest.fixture(autouse=True)
    def _compile(self, examples_dir, tmp_output):
        self._result = pp.compile(str(examples_dir / "api_minimal.yaml"), str(tmp_output))

    def test_success_true(self):
        out = ser.compilation_result(self._result)
        assert out["success"] is True

    def test_phases_present(self):
        out = ser.compilation_result(self._result)
        names = [p["name"] for p in out["phases"]]
        assert "Parse" in names
        assert "Emit" in names

    def test_written_list(self):
        out = ser.compilation_result(self._result)
        assert len(out["written"]) > 0
        assert all(isinstance(f, str) for f in out["written"])

    def test_errors_empty(self):
        out = ser.compilation_result(self._result)
        assert out["errors"] == []

    def test_universe_included(self):
        out = ser.compilation_result(self._result)
        assert out["universe"]["name"] == "TodoAPI"  # from api_minimal.yaml

    def test_total_ms(self):
        out = ser.compilation_result(self._result)
        assert out["total_ms"] > 0

    def test_failure_result(self, tmp_output):
        result = pp.compile("/nonexistent/genesis.yaml", str(tmp_output))
        out = ser.compilation_result(result)
        assert out["success"] is False
        assert len(out["errors"]) > 0
        assert out["universe"] is None
