"""CLI tests — the commands behave as their own help text advertises."""
from pathlib import Path

from click.testing import CliRunner

from bigbang.cli import cli

EXAMPLE = str(Path(__file__).parent.parent / "examples" / "api_minimal.yaml")


def test_cli_group_exposes_subcommands():
    result = CliRunner().invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "bang" in result.output
    assert "plugins" in result.output


def test_bang_dry_run(tmp_path):
    result = CliRunner().invoke(cli, ["bang", EXAMPLE, "--output", str(tmp_path), "--dry-run"])
    assert result.exit_code == 0, result.output
    assert "DRY RUN" in result.output


def test_bang_compiles_example(tmp_path):
    result = CliRunner().invoke(cli, ["bang", EXAMPLE, "--output", str(tmp_path)])
    assert result.exit_code == 0, result.output
    out_dirs = list(tmp_path.glob("universe_*"))
    assert out_dirs, result.output


def test_plugins_command_lists_registry():
    result = CliRunner().invoke(cli, ["plugins"])
    assert result.exit_code == 0
