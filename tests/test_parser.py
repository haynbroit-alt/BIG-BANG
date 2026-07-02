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
