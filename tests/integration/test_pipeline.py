"""Integration tests — full pipeline end to end."""
import copy
from pathlib import Path

import pytest

from bigbang import pipeline as pp
from bigbang.pipeline import CompilationResult


# ── Helpers ───────────────────────────────────────────────────────────────────

def phase_names(result: CompilationResult) -> list[str]:
    return [p.name for p in result.phases]


def phase(result: CompilationResult, name: str):
    return next((p for p in result.phases if p.name == name), None)


# ── Error handling ────────────────────────────────────────────────────────────

class TestPipelineErrors:
    def test_missing_genesis_file(self, tmp_output):
        result = pp.compile("/nonexistent/path/genesis.yaml", str(tmp_output))
        assert result.errors
        assert any("E000" in d.code for d in result.errors)
        assert "Parse" in phase_names(result)
        assert "FAILED" in phase(result, "Parse").note

    def test_invalid_genesis_returns_error(self, tmp_path, tmp_output):
        bad = tmp_path / "bad.yaml"
        bad.write_text("universe:\n  type: api\n", encoding="utf-8")  # missing name
        result = pp.compile(str(bad), str(tmp_output))
        assert result.errors


# ── TodoAPI (minimal, no auth, no ed25519) ────────────────────────────────────

class TestTodoAPIPipeline:
    @pytest.fixture(autouse=True)
    def result(self, examples_dir, tmp_output):
        self._result = pp.compile(
            str(examples_dir / "api_minimal.yaml"),
            str(tmp_output),
        )

    def test_no_errors(self):
        assert not self._result.errors

    def test_all_phases_present(self):
        names = phase_names(self._result)
        for expected in ["Parse", "Resolve", "Schedule", "Build", "Transform", "Emit", "Snapshot"]:
            assert expected in names, f"Phase '{expected}' missing"

    def test_no_phase_failed(self):
        for p in self._result.phases:
            assert "FAILED" not in p.note, f"Phase '{p.name}' failed: {p.note}"

    def test_universe_parsed(self):
        u = self._result.universe
        assert u is not None
        assert u.name == "TodoAPI"
        assert len(u.entities) == 2

    def test_graph_built(self):
        g = self._result.graph
        assert g is not None
        assert g.has_node("entity:todo")
        assert g.has_node("entity:tag")

    def test_no_auth_no_identity_node(self):
        assert not self._result.graph.has_identity

    def test_no_ed25519_no_ledger_node(self):
        assert not self._result.graph.has_ledger

    def test_no_billing_node(self):
        assert not self._result.graph.has_billing

    def test_core_files_generated(self):
        written = set(self._result.written)
        for expected in ["backend/app.py", "backend/models.py", "backend/routes.py",
                         "backend/schemas.py", "backend/database.py",
                         "backend/requirements.txt"]:
            assert expected in written, f"Missing: {expected}"

    def test_no_auth_files_generated(self):
        written = set(self._result.written)
        for auth_file in ["backend/auth_models.py", "backend/auth_routes.py",
                          "backend/auth_schemas.py"]:
            assert auth_file not in written, f"Auth file unexpectedly present: {auth_file}"

    def test_no_ledger_files_generated(self):
        written = set(self._result.written)
        assert "backend/ledger.py" not in written
        assert "backend/ledger_routes.py" not in written

    def test_output_files_exist_on_disk(self, tmp_output):
        output = self._result.output_path
        assert (output / "backend" / "app.py").exists()
        assert (output / "backend" / "models.py").exists()

    def test_second_run_is_idempotent(self, examples_dir, tmp_output):
        r1 = self._result
        r2 = pp.compile(str(examples_dir / "api_minimal.yaml"), str(tmp_output))
        assert not r2.errors
        # Same files written on second run (block-merged)
        assert set(r1.written) == set(r2.written)

    def test_transform_phase_runs(self):
        p = phase(self._result, "Transform")
        assert p is not None
        assert "transform(s)" in p.note


# ── SwiftCRM (full: auth + ed25519 + monetization) ───────────────────────────

class TestSwiftCRMPipeline:
    @pytest.fixture(autouse=True)
    def result(self, examples_dir, tmp_output):
        self._result = pp.compile(
            str(examples_dir / "saas_crm.yaml"),
            str(tmp_output),
        )

    def test_no_errors(self):
        assert not self._result.errors

    def test_all_phases_present(self):
        names = phase_names(self._result)
        for expected in ["Parse", "Resolve", "Schedule", "Build",
                         "Transform", "Diff", "Emit", "Snapshot"]:
            assert expected in names

    def test_universe_parsed(self):
        u = self._result.universe
        assert u.name == "SwiftCRM"
        assert len(u.entities) == 3
        assert u.auth.enabled is True
        assert u.security.ed25519 is True

    def test_graph_has_identity_node(self):
        assert self._result.graph.has_identity

    def test_graph_has_ledger_node(self):
        assert self._result.graph.has_ledger

    def test_graph_has_billing_node(self):
        assert self._result.graph.has_billing

    def test_auth_files_generated(self):
        written = set(self._result.written)
        for f in ["backend/auth_models.py", "backend/auth_routes.py", "backend/auth_schemas.py"]:
            assert f in written, f"Missing auth file: {f}"

    def test_ledger_files_generated(self):
        written = set(self._result.written)
        assert "backend/ledger.py" in written
        assert "backend/ledger_routes.py" in written

    def test_relations_resolved(self):
        u = self._result.universe
        em = u.entity_map
        assert len(em["Deal"].relations) == 1
        assert em["Deal"].relations[0].target == "Contact"
        assert len(em["Activity"].relations) == 2

    def test_topo_order_respected(self):
        u = self._result.universe
        order = u.topo_order
        assert order.index("Contact") < order.index("Deal")
        assert order.index("Deal") < order.index("Activity")

    def test_relation_edges_in_graph(self):
        g = self._result.graph
        rel_edges = g.edges_of_kind("relation")
        assert len(rel_edges) >= 3  # deal→contact + activity→deal + activity→contact

    def test_signing_edges_in_graph(self):
        g = self._result.graph
        signs_edges = g.edges_of_kind("signs")
        assert len(signs_edges) == 3  # one per entity

    def test_snapshot_file_created(self, tmp_output):
        snap = self._result.output_path / ".bigbang.snapshot.json"
        assert snap.exists()

    def test_more_files_than_minimal(self, examples_dir, tmp_output2):
        result_minimal = pp.compile(
            str(examples_dir / "api_minimal.yaml"), str(tmp_output2)
        )
        assert len(self._result.written) > len(result_minimal.written)

    @pytest.fixture
    def tmp_output2(self, tmp_path):
        return tmp_path / "output2"


# ── Dry run ───────────────────────────────────────────────────────────────────

class TestDryRun:
    def test_dry_run_no_files_written(self, examples_dir, tmp_output):
        result = pp.compile(
            str(examples_dir / "api_minimal.yaml"),
            str(tmp_output),
            dry_run=True,
        )
        assert not result.errors
        # tmp_output directory should not exist (nothing written)
        assert not tmp_output.exists() or not any(tmp_output.rglob("*.py"))

    def test_dry_run_lists_would_be_files(self, examples_dir, tmp_output):
        result = pp.compile(
            str(examples_dir / "api_minimal.yaml"),
            str(tmp_output),
            dry_run=True,
        )
        assert len(result.written) > 0

    def test_dry_run_diff_phase_skipped(self, examples_dir, tmp_output):
        result = pp.compile(
            str(examples_dir / "api_minimal.yaml"),
            str(tmp_output),
            dry_run=True,
        )
        diff_phase = phase(result, "Diff")
        assert diff_phase is not None
        assert "skipped" in diff_phase.note


# ── Incremental diff ──────────────────────────────────────────────────────────

class TestIncrementalDiff:
    def test_second_run_shows_no_changes(self, examples_dir, tmp_output):
        pp.compile(str(examples_dir / "api_minimal.yaml"), str(tmp_output))
        r2 = pp.compile(str(examples_dir / "api_minimal.yaml"), str(tmp_output))
        assert r2.diff is not None
        assert r2.diff.is_empty

    def test_first_run_no_diff(self, examples_dir, tmp_output):
        r1 = pp.compile(str(examples_dir / "api_minimal.yaml"), str(tmp_output))
        assert r1.diff is None


# ── Determinism ───────────────────────────────────────────────────────────────

class TestDeterminism:
    def test_same_input_same_output(self, examples_dir, tmp_path):
        out1 = tmp_path / "run1"
        out2 = tmp_path / "run2"
        r1 = pp.compile(str(examples_dir / "api_minimal.yaml"), str(out1))
        r2 = pp.compile(str(examples_dir / "api_minimal.yaml"), str(out2))

        assert set(r1.written) == set(r2.written)

        out1_path = r1.output_path
        out2_path = r2.output_path

        for rel in r1.written:
            f1 = (out1_path / rel).read_text(encoding="utf-8")
            f2 = (out2_path / rel).read_text(encoding="utf-8")
            assert f1 == f2, f"Non-deterministic output for: {rel}"

    def test_crm_determinism(self, examples_dir, tmp_path):
        out1 = tmp_path / "crm1"
        out2 = tmp_path / "crm2"
        r1 = pp.compile(str(examples_dir / "saas_crm.yaml"), str(out1))
        r2 = pp.compile(str(examples_dir / "saas_crm.yaml"), str(out2))

        out1_path = r1.output_path
        out2_path = r2.output_path

        for rel in r1.written:
            f1 = (out1_path / rel).read_text(encoding="utf-8")
            f2 = (out2_path / rel).read_text(encoding="utf-8")
            assert f1 == f2, f"Non-deterministic output for: {rel}"
