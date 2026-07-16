"""Integration tests for POST /studio/generate."""
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from bigbang.server import app

client = TestClient(app)

_VALID_YAML = """\
universe:
  name: TodoAPI
  type: api
  entities:
    - name: Todo
      fields:
        - name: title
          type: string
          required: true
  flows: []
  roles: []
  auth:
    enabled: false
  security:
    ed25519: false
    ledger: false
  monetization: ~
  plugins: []
"""

_INVALID_YAML = "universe:\n  type: api\n"   # missing name → parse error


def _patch_generate(yaml: str = _VALID_YAML):
    return patch("bigbang.studio.generate", return_value=yaml)


# ── success path ──────────────────────────────────────────────────────────────

class TestStudioGenerateSuccess:
    def test_status_200(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        assert r.status_code == 200

    def test_success_true(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        assert r.json()["success"] is True

    def test_yaml_returned(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        assert "universe:" in r.json()["yaml"]

    def test_universe_parsed_and_returned(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        u = r.json()["universe"]
        assert u["name"] == "TodoAPI"
        assert u["type"] == "api"

    def test_errors_empty_on_success(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        assert r.json()["errors"] == []

    def test_warnings_present_in_response(self):
        with _patch_generate():
            r = client.post("/studio/generate", json={"description": "A todo API"})
        assert "warnings" in r.json()

    def test_custom_model_forwarded(self):
        with patch("bigbang.studio.generate", return_value=_VALID_YAML) as mock_gen:
            client.post("/studio/generate", json={
                "description": "An app",
                "model": "claude-haiku-4-5",
            })
        mock_gen.assert_called_once_with("An app", model="claude-haiku-4-5")

    def test_default_model_is_opus(self):
        with patch("bigbang.studio.generate", return_value=_VALID_YAML) as mock_gen:
            client.post("/studio/generate", json={"description": "An app"})
        _, call_kw = mock_gen.call_args
        assert call_kw["model"] == "claude-opus-4-8"

    def test_description_forwarded(self):
        with patch("bigbang.studio.generate", return_value=_VALID_YAML) as mock_gen:
            client.post("/studio/generate", json={"description": "Build me a CRM"})
        call_args, _ = mock_gen.call_args
        assert call_args[0] == "Build me a CRM"


# ── validation failure path ───────────────────────────────────────────────────

class TestStudioGenerateValidationFailure:
    def test_success_false_when_yaml_invalid(self):
        with _patch_generate(_INVALID_YAML):
            r = client.post("/studio/generate", json={"description": "broken"})
        assert r.json()["success"] is False

    def test_raw_yaml_still_returned_on_failure(self):
        with _patch_generate(_INVALID_YAML):
            r = client.post("/studio/generate", json={"description": "broken"})
        assert r.json()["yaml"] == _INVALID_YAML

    def test_errors_non_empty_on_failure(self):
        with _patch_generate(_INVALID_YAML):
            r = client.post("/studio/generate", json={"description": "broken"})
        assert len(r.json()["errors"]) > 0

    def test_universe_none_on_failure(self):
        with _patch_generate(_INVALID_YAML):
            r = client.post("/studio/generate", json={"description": "broken"})
        assert r.json()["universe"] is None


# ── service error path ────────────────────────────────────────────────────────

class TestStudioGenerateServiceErrors:
    def test_missing_api_key_returns_503(self):
        with patch("bigbang.studio.generate",
                   side_effect=ValueError("ANTHROPIC_API_KEY not set")):
            r = client.post("/studio/generate", json={"description": "any"})
        assert r.status_code == 503

    def test_anthropic_unavailable_returns_503(self):
        with patch("bigbang.studio.generate",
                   side_effect=ImportError("anthropic package required")):
            r = client.post("/studio/generate", json={"description": "any"})
        assert r.status_code == 503

    def test_503_success_false(self):
        with patch("bigbang.studio.generate",
                   side_effect=ValueError("ANTHROPIC_API_KEY not set")):
            r = client.post("/studio/generate", json={"description": "any"})
        assert r.json()["success"] is False

    def test_503_error_message_present(self):
        with patch("bigbang.studio.generate",
                   side_effect=ValueError("ANTHROPIC_API_KEY not set")):
            r = client.post("/studio/generate", json={"description": "any"})
        assert len(r.json()["errors"]) > 0

    def test_unexpected_exception_returns_500(self):
        with patch("bigbang.studio.generate",
                   side_effect=RuntimeError("unexpected crash")):
            r = client.post("/studio/generate", json={"description": "any"})
        assert r.status_code == 500


# ── request validation ────────────────────────────────────────────────────────

class TestStudioGenerateRequestValidation:
    def test_missing_description_422(self):
        r = client.post("/studio/generate", json={})
        assert r.status_code == 422

    def test_empty_body_422(self):
        r = client.post("/studio/generate")
        assert r.status_code == 422

    def test_description_required(self):
        r = client.post("/studio/generate", json={"model": "claude-opus-4-8"})
        assert r.status_code == 422
