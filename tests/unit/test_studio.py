"""Unit tests for bigbang.studio — Anthropic SDK is fully mocked."""
import io
import os
import sys
from unittest.mock import MagicMock, patch

import pytest

from bigbang import studio

_SIMPLE_YAML = """\
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


def _mock_stream(text: str):
    """Build a mock context-manager stream that yields *text* as a single chunk."""
    m = MagicMock()
    m.__enter__ = MagicMock(return_value=m)
    m.__exit__ = MagicMock(return_value=False)
    m.text_stream = iter([text])
    return m


def _mock_anthropic(text: str = _SIMPLE_YAML):
    """Return a mock anthropic module + patched client that streams *text*."""
    client = MagicMock()
    client.messages.stream.return_value = _mock_stream(text)
    mod = MagicMock()
    mod.Anthropic.return_value = client
    return mod, client


# ── _require_api_key ──────────────────────────────────────────────────────────

class TestRequireApiKey:
    def test_returns_key_when_set(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-test"}):
            assert studio._require_api_key() == "sk-test"

    def test_raises_when_missing(self):
        env = {k: v for k, v in os.environ.items() if k != "ANTHROPIC_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                studio._require_api_key()

    def test_raises_when_empty(self):
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "   "}):
            with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
                studio._require_api_key()


# ── _require_anthropic ────────────────────────────────────────────────────────

class TestRequireAnthropic:
    def test_returns_module(self):
        mod = studio._require_anthropic()
        assert mod is not None

    def test_raises_when_unavailable(self):
        with patch.dict(sys.modules, {"anthropic": None}):
            with pytest.raises(ImportError, match="anthropic"):
                studio._require_anthropic()


# ── _clean_yaml ───────────────────────────────────────────────────────────────

class TestCleanYaml:
    def test_strips_yaml_fence(self):
        raw = "```yaml\nuniverse:\n  name: T\n```"
        assert studio._clean_yaml(raw) == "universe:\n  name: T\n"

    def test_strips_plain_fence(self):
        raw = "```\nuniverse:\n  name: T\n```"
        assert studio._clean_yaml(raw) == "universe:\n  name: T\n"

    def test_no_fence_unchanged(self):
        raw = "universe:\n  name: T"
        assert studio._clean_yaml(raw) == "universe:\n  name: T\n"

    def test_always_newline_terminated(self):
        raw = "universe:\n  name: T"
        assert studio._clean_yaml(raw).endswith("\n")

    def test_strips_leading_trailing_whitespace(self):
        raw = "\n\n  universe:\n    name: T\n\n"
        result = studio._clean_yaml(raw)
        assert result.startswith("universe:")


# ── generate ──────────────────────────────────────────────────────────────────

class TestGenerate:
    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_returns_yaml_string(self, mock_anthro, _mock_key):
        mod, _ = _mock_anthropic()
        mock_anthro.return_value = mod
        result = studio.generate("A simple todo list API")
        assert "universe:" in result
        assert result.endswith("\n")

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_strips_markdown_fences(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        client.messages.stream.return_value = _mock_stream(f"```yaml\n{_SIMPLE_YAML}```")
        mock_anthro.return_value = mod
        result = studio.generate("some app")
        assert not result.startswith("```")
        assert "universe:" in result

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_default_model_is_opus(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        mock_anthro.return_value = mod
        studio.generate("an app")
        kw = client.messages.stream.call_args.kwargs
        assert kw["model"] == "claude-opus-4-8"

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_custom_model_passed_to_api(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        mock_anthro.return_value = mod
        studio.generate("an app", model="claude-haiku-4-5")
        kw = client.messages.stream.call_args.kwargs
        assert kw["model"] == "claude-haiku-4-5"

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_thinking_adaptive(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        mock_anthro.return_value = mod
        studio.generate("an app")
        kw = client.messages.stream.call_args.kwargs
        assert kw.get("thinking") == {"type": "adaptive"}

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_system_prompt_used(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        mock_anthro.return_value = mod
        studio.generate("an app")
        kw = client.messages.stream.call_args.kwargs
        assert "BIG BANG" in kw["system"]

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_description_in_messages(self, mock_anthro, _mock_key):
        mod, client = _mock_anthropic()
        mock_anthro.return_value = mod
        studio.generate("Build me a CRM")
        kw = client.messages.stream.call_args.kwargs
        assert kw["messages"][0]["content"] == "Build me a CRM"

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_stream_to_receives_chunks(self, mock_anthro, _mock_key):
        mod, _ = _mock_anthropic()
        mock_anthro.return_value = mod
        buf = io.StringIO()
        studio.generate("an app", stream_to=buf)
        assert "universe:" in buf.getvalue()

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_stream_to_none_is_fine(self, mock_anthro, _mock_key):
        mod, _ = _mock_anthropic()
        mock_anthro.return_value = mod
        result = studio.generate("an app", stream_to=None)
        assert result

    @patch("bigbang.studio._require_api_key", return_value="sk-test")
    @patch("bigbang.studio._require_anthropic")
    def test_multiple_chunks_joined(self, mock_anthro, _mock_key):
        chunks = ["universe:\n", "  name: Chunky\n", "  type: api\n"]
        mod, client = _mock_anthropic()
        m = MagicMock()
        m.__enter__ = MagicMock(return_value=m)
        m.__exit__ = MagicMock(return_value=False)
        m.text_stream = iter(chunks)
        client.messages.stream.return_value = m
        mock_anthro.return_value = mod
        result = studio.generate("an app")
        assert "name: Chunky" in result
