"""Unit tests for DSL versioning support in the parser."""
import textwrap
from pathlib import Path

import pytest

from bigbang.parser import DSL_VERSION, parse


def _write(tmp_path: Path, content: str) -> str:
    p = tmp_path / "genesis.yaml"
    p.write_text(textwrap.dedent(content), encoding="utf-8")
    return str(p)


class TestDSLVersioning:
    def test_default_version_when_absent(self, tmp_path):
        f = _write(tmp_path, "universe:\n  name: T\n  type: api\n")
        u = parse(f)
        assert u.dsl_version == "1.0"

    def test_explicit_version_1_0(self, tmp_path):
        f = _write(tmp_path, """
            bigbang: "1.0"
            universe:
              name: T
              type: api
        """)
        u = parse(f)
        assert u.dsl_version == "1.0"

    def test_unsupported_version_raises(self, tmp_path):
        f = _write(tmp_path, """
            bigbang: "99.0"
            universe:
              name: T
              type: api
        """)
        with pytest.raises(ValueError, match="Unsupported DSL version"):
            parse(f)

    def test_dsl_version_constant_is_string(self):
        assert isinstance(DSL_VERSION, str)
        assert DSL_VERSION == "1.0"

    def test_version_stored_on_universe(self, tmp_path):
        f = _write(tmp_path, """
            bigbang: "1.0"
            universe:
              name: Versioned
              type: api
        """)
        u = parse(f)
        assert u.dsl_version == "1.0"
        assert u.name == "Versioned"

    def test_examples_parse_with_version(self, examples_dir):
        u = parse(str(examples_dir / "api_minimal.yaml"))
        assert u.dsl_version == "1.0"
        u2 = parse(str(examples_dir / "saas_crm.yaml"))
        assert u2.dsl_version == "1.0"
