"""Integration tests for the BIG BANG HTTP API server."""
import io
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bigbang.server import app

client = TestClient(app)


# ── /health ───────────────────────────────────────────────────────────────────

class TestHealth:
    def test_status_ok(self):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_version_present(self):
        r = client.get("/health")
        assert "version" in r.json()


# ── /plugins ──────────────────────────────────────────────────────────────────

class TestPlugins:
    def test_returns_list(self):
        r = client.get("/plugins")
        assert r.status_code == 200
        data = r.json()
        assert "plugins" in data
        assert isinstance(data["plugins"], list)
        assert data["count"] == len(data["plugins"])

    def test_plugin_shape(self):
        data = client.get("/plugins").json()
        for p in data["plugins"]:
            assert "name" in p
            assert "description" in p
            assert "requires" in p

    def test_builtin_plugins_registered(self):
        names = {p["name"] for p in client.get("/plugins").json()["plugins"]}
        assert "backend" in names
        assert "docker" in names


# ── /validate ─────────────────────────────────────────────────────────────────

MINIMAL_YAML = "universe:\n  name: Test\n  type: api\n"
INVALID_YAML = "universe:\n  type: api\n"   # missing name


class TestValidate:
    def test_valid_yaml_json_body(self):
        r = client.post("/validate", json={"content": MINIMAL_YAML})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True
        assert data["universe"]["name"] == "Test"

    def test_valid_yaml_raw_body(self):
        r = client.post(
            "/validate",
            content=MINIMAL_YAML.encode(),
            headers={"Content-Type": "text/plain"},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_valid_yaml_file_upload(self):
        r = client.post(
            "/validate",
            files={"file": ("genesis.yaml", MINIMAL_YAML.encode(), "text/yaml")},
        )
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_invalid_yaml_returns_error(self):
        r = client.post("/validate", json={"content": INVALID_YAML})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_universe_fields_in_response(self):
        r = client.post("/validate", json={"content": MINIMAL_YAML})
        u = r.json()["universe"]
        assert u["name"] == "Test"
        assert u["type"] == "api"
        assert u["dsl_version"] == "1.0"
        assert "entities" in u
        assert "auth" in u
        assert "security" in u

    def test_warnings_list_present(self):
        r = client.post("/validate", json={"content": MINIMAL_YAML})
        assert "warnings" in r.json()
        assert "infos" in r.json()

    def test_w001_for_unresolved_fk(self):
        yaml_with_fk = (
            "universe:\n"
            "  name: Test\n"
            "  type: api\n"
            "  entities:\n"
            "    - name: Deal\n"
            "      fields:\n"
            "        - name: invoice_id\n"
            "          type: integer\n"
        )
        r = client.post("/validate", json={"content": yaml_with_fk})
        data = r.json()
        assert data["success"] is True   # warning, not error
        warnings = data["warnings"]
        assert any(w["code"] == "W001" for w in warnings)

    def test_missing_content_field(self):
        r = client.post("/validate", json={"other": "field"})
        assert r.status_code == 422

    def test_full_crm_yaml(self, examples_dir):
        content = (examples_dir / "saas_crm.yaml").read_text(encoding="utf-8")
        r = client.post("/validate", json={"content": content})
        data = r.json()
        assert data["success"] is True
        assert data["universe"]["name"] == "SwiftCRM"
        assert data["universe"]["auth"]["enabled"] is True


# ── /compile ──────────────────────────────────────────────────────────────────

class TestCompile:
    def test_successful_compile(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        assert r.status_code == 200
        data = r.json()
        assert data["success"] is True

    def test_phases_in_response(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        names = [p["name"] for p in r.json()["phases"]]
        for expected in ["Parse", "Resolve", "Schedule", "Build", "Transform", "Emit"]:
            assert expected in names

    def test_written_files_listed(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        assert len(r.json()["written"]) > 0

    def test_errors_empty_on_success(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        assert r.json()["errors"] == []

    def test_failed_compile_returns_errors(self):
        r = client.post("/compile", json={"content": INVALID_YAML})
        data = r.json()
        assert data["success"] is False
        assert len(data["errors"]) > 0

    def test_total_ms_positive(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        assert r.json()["total_ms"] > 0

    def test_universe_in_response(self):
        r = client.post("/compile", json={"content": MINIMAL_YAML})
        assert r.json()["universe"]["name"] == "Test"

    def test_full_crm_compile(self, examples_dir):
        content = (examples_dir / "saas_crm.yaml").read_text(encoding="utf-8")
        r = client.post("/compile", json={"content": content})
        data = r.json()
        assert data["success"] is True
        assert data["universe"]["name"] == "SwiftCRM"
        written = set(data["written"])
        assert any("auth" in f for f in written)
        assert any("ledger" in f for f in written)


# ── /compile/dry-run ──────────────────────────────────────────────────────────

class TestDryRun:
    def test_success(self):
        r = client.post("/compile/dry-run", json={"content": MINIMAL_YAML})
        assert r.status_code == 200
        assert r.json()["success"] is True

    def test_written_list_non_empty(self):
        r = client.post("/compile/dry-run", json={"content": MINIMAL_YAML})
        assert len(r.json()["written"]) > 0

    def test_diff_phase_skipped(self):
        r = client.post("/compile/dry-run", json={"content": MINIMAL_YAML})
        phases = {p["name"]: p["note"] for p in r.json()["phases"]}
        assert "Diff" in phases
        assert "skipped" in phases["Diff"]
