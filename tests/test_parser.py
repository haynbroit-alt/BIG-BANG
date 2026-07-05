"""Parser tests — YAML front-end of the compiler."""
import pytest

from bigbang import parser

from conftest import write_genesis


def test_parse_minimal_example(examples_dir):
    u = parser.parse(str(examples_dir / "api_minimal.yaml"))
    assert u.name
    assert u.type
    assert u.entities


def test_parse_saas_example(examples_dir):
    u = parser.parse(str(examples_dir / "saas_crm.yaml"))
    assert u.entities
    assert all(e.name for e in u.entities)


def test_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        parser.parse(str(tmp_path / "nope.yaml"))


def test_missing_universe_key(tmp_path):
    path = write_genesis(tmp_path, "not_universe: {}")
    with pytest.raises(ValueError, match="universe"):
        parser.parse(path)


def test_missing_name(tmp_path):
    path = write_genesis(tmp_path, "universe:\n  type: api")
    with pytest.raises(ValueError, match="name"):
        parser.parse(path)


def test_missing_type(tmp_path):
    path = write_genesis(tmp_path, "universe:\n  name: X")
    with pytest.raises(ValueError, match="type"):
        parser.parse(path)


def test_invalid_field_type(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  entities:
    - name: Thing
      fields:
        - name: blob
          type: varchar
""",
    )
    with pytest.raises(ValueError, match="varchar"):
        parser.parse(path)


def test_unknown_auth_provider(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  auth:
    enabled: true
    provider: oauth99
""",
    )
    with pytest.raises(ValueError, match="oauth99"):
        parser.parse(path)


def test_flow_requires_steps(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  flows:
    - name: empty_flow
""",
    )
    with pytest.raises(ValueError, match="empty_flow"):
        parser.parse(path)


def test_field_defaults(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  entities:
    - name: Thing
      fields:
        - name: label
""",
    )
    u = parser.parse(path)
    f = u.entities[0].fields[0]
    assert f.type == "string"
    assert f.required is True
    assert f.computed is False


# --- Every genesis.yaml issue gets a clear diagnostic, not a raw traceback ---


def test_invalid_yaml_syntax_raises_a_clear_value_error(tmp_path):
    # Unbalanced brackets — a raw yaml.YAMLError, not a ValueError, would
    # otherwise slip past the pipeline's `except (FileNotFoundError, ValueError)`.
    path = write_genesis(tmp_path, "universe: [name: X, type: api")
    with pytest.raises(ValueError, match="Invalid YAML"):
        parser.parse(path)


def test_scalar_top_level_document_raises_a_clear_error(tmp_path):
    # A bare scalar document (no mapping at all) must not raise a bare
    # TypeError from `"universe" not in spec`.
    path = write_genesis(tmp_path, "42")
    with pytest.raises(ValueError, match="universe"):
        parser.parse(path)


def test_universe_key_not_a_mapping_raises_a_clear_error(tmp_path):
    path = write_genesis(tmp_path, "universe: [1, 2, 3]")
    with pytest.raises(ValueError, match="mapping"):
        parser.parse(path)


def test_duplicate_entity_name_raises(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  entities:
    - name: Thing
    - name: Thing
""",
    )
    with pytest.raises(ValueError, match="Duplicate entity"):
        parser.parse(path)


def test_monetization_plan_missing_name_raises(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  monetization:
    plans:
      - price: 10
""",
    )
    with pytest.raises(ValueError, match="must have a 'name'"):
        parser.parse(path)


def test_monetization_plan_missing_price_raises(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  monetization:
    plans:
      - name: Pro
""",
    )
    with pytest.raises(ValueError, match="missing 'price'"):
        parser.parse(path)


def test_role_missing_name_raises(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  roles:
    - permissions: [read]
""",
    )
    with pytest.raises(ValueError, match="Each role must have a 'name'"):
        parser.parse(path)


def test_auth_user_field_invalid_type_raises(tmp_path):
    path = write_genesis(
        tmp_path,
        """
universe:
  name: X
  type: api
  auth:
    enabled: true
    user_fields:
      - name: avatar
        type: varchar
""",
    )
    with pytest.raises(ValueError, match="varchar"):
        parser.parse(path)
