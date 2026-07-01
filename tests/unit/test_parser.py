"""Unit tests for bigbang.parser — genesis YAML parsing and validation."""
import textwrap
from pathlib import Path

import pytest

from bigbang.parser import parse


def _write_yaml(tmp_path: Path, content: str) -> str:
    p = tmp_path / "genesis.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


# ── File errors ───────────────────────────────────────────────────────────────

class TestFileErrors:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="Genesis file not found"):
            parse(str(tmp_path / "nonexistent.yaml"))

    def test_missing_universe_key_raises(self, tmp_path):
        f = _write_yaml(tmp_path, "name: bad\ntype: api\n")
        with pytest.raises(ValueError, match="missing top-level 'universe' key"):
            parse(f)

    def test_empty_file_raises(self, tmp_path):
        f = _write_yaml(tmp_path, "")
        with pytest.raises(ValueError):
            parse(f)


# ── Validation errors ─────────────────────────────────────────────────────────

class TestValidationErrors:
    def test_missing_universe_name_raises(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  type: api\n")
        with pytest.raises(ValueError, match="must have a 'name'"):
            parse(f)

    def test_missing_universe_type_raises(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  name: Test\n")
        with pytest.raises(ValueError, match="must have a 'type'"):
            parse(f)

    def test_entity_missing_name_raises(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              entities:
                - fields:
                    - name: title
                      type: string
        """)
        with pytest.raises(ValueError, match="entity must have a 'name'"):
            parse(f)

    def test_field_missing_name_raises(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              entities:
                - name: Todo
                  fields:
                    - type: string
        """)
        with pytest.raises(ValueError, match="missing 'name'"):
            parse(f)

    def test_invalid_field_type_raises(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              entities:
                - name: Todo
                  fields:
                    - name: title
                      type: fancy_type
        """)
        with pytest.raises(ValueError, match="Invalid field type"):
            parse(f)

    def test_invalid_auth_provider_raises(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              auth:
                enabled: true
                provider: oauth2
        """)
        with pytest.raises(ValueError, match="Unknown auth provider"):
            parse(f)

    def test_flow_without_steps_raises(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              flows:
                - name: empty_flow
        """)
        with pytest.raises(ValueError, match="must have at least one step"):
            parse(f)


# ── Successful parsing ────────────────────────────────────────────────────────

class TestSuccessfulParsing:
    def test_minimal_valid_universe(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  name: Test\n  type: api\n")
        u = parse(f)
        assert u.name == "Test"
        assert u.type == "api"
        assert u.entities == []

    def test_entities_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              entities:
                - name: Todo
                  fields:
                    - name: title
                      type: string
                      required: true
                    - name: done
                      type: boolean
                      required: false
        """)
        u = parse(f)
        assert len(u.entities) == 1
        todo = u.entities[0]
        assert todo.name == "Todo"
        assert len(todo.fields) == 2
        assert todo.fields[0].name == "title"
        assert todo.fields[0].type == "string"
        assert todo.fields[0].required is True
        assert todo.fields[1].name == "done"
        assert todo.fields[1].required is False

    def test_all_valid_field_types(self, tmp_path):
        valid_types = ["string", "integer", "float", "boolean", "text", "datetime"]
        fields_yaml = "\n".join(
            f"                    - name: f_{t}\n                      type: {t}"
            for t in valid_types
        )
        f = _write_yaml(tmp_path, f"""
            universe:
              name: Test
              type: api
              entities:
                - name: AllTypes
                  fields:
{fields_yaml}
        """)
        u = parse(f)
        parsed_types = [fld.type for fld in u.entities[0].fields]
        assert parsed_types == valid_types

    def test_auth_config_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              auth:
                enabled: true
                provider: jwt
                user_fields:
                  - name: email
                    type: string
        """)
        u = parse(f)
        assert u.auth.enabled is True
        assert u.auth.provider == "jwt"
        assert len(u.auth.user_fields) == 1
        assert u.auth.user_fields[0].name == "email"

    def test_auth_disabled_by_default(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  name: T\n  type: api\n")
        u = parse(f)
        assert u.auth.enabled is False

    def test_security_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              security:
                ed25519: true
                ledger: true
        """)
        u = parse(f)
        assert u.security.ed25519 is True
        assert u.security.ledger is True

    def test_monetization_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              monetization:
                model: subscription
                plans:
                  - name: starter
                    price: 29
                    currency: USD
        """)
        u = parse(f)
        assert u.monetization is not None
        assert u.monetization.model == "subscription"
        assert len(u.monetization.plans) == 1
        assert u.monetization.plans[0].name == "starter"
        assert u.monetization.plans[0].price == 29

    def test_no_monetization_is_none(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  name: T\n  type: api\n")
        u = parse(f)
        assert u.monetization is None

    def test_flows_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              flows:
                - name: on_signup
                  trigger: user_registered
                  steps:
                    - action: send_welcome_email
                    - action: create_default_settings
        """)
        u = parse(f)
        assert len(u.flows) == 1
        flow = u.flows[0]
        assert flow.name == "on_signup"
        assert flow.trigger == "user_registered"
        assert len(flow.steps) == 2

    def test_roles_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              roles:
                - name: admin
                  permissions: [read, write, delete]
        """)
        u = parse(f)
        assert len(u.roles) == 1
        assert u.roles[0].name == "admin"
        assert "delete" in u.roles[0].permissions

    def test_name_slug(self, tmp_path):
        f = _write_yaml(tmp_path, "universe:\n  name: 'My Cool App'\n  type: api\n")
        u = parse(f)
        assert u.name_slug == "my_cool_app"

    def test_plugins_list_parsed(self, tmp_path):
        f = _write_yaml(tmp_path, """
            universe:
              name: Test
              type: api
              plugins:
                - my_custom_plugin
        """)
        u = parse(f)
        assert u.plugins == ["my_custom_plugin"]

    def test_examples_saas_crm(self, examples_dir):
        u = parse(str(examples_dir / "saas_crm.yaml"))
        assert u.name == "SwiftCRM"
        assert u.type == "saas"
        assert len(u.entities) == 3
        assert u.auth.enabled is True
        assert u.security.ed25519 is True
        assert u.monetization is not None
        assert len(u.monetization.plans) == 3

    def test_examples_api_minimal(self, examples_dir):
        u = parse(str(examples_dir / "api_minimal.yaml"))
        assert u.name == "TodoAPI"
        assert u.type == "api"
        assert len(u.entities) == 2
        assert u.auth.enabled is False
        assert u.security.ed25519 is False
        assert u.monetization is None
