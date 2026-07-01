#!/usr/bin/env python3
import sys
import time

import click

from . import parser, generator
from .plugins import registry

BANNER = r"""
  ██████╗ ██╗ ██████╗     ██████╗  █████╗ ███╗   ██╗ ██████╗
  ██╔══██╗██║██╔════╝     ██╔══██╗██╔══██╗████╗  ██║██╔════╝
  ██████╔╝██║██║  ███╗    ██████╔╝███████║██╔██╗ ██║██║  ███╗
  ██╔══██╗██║██║   ██║    ██╔══██╗██╔══██║██║╚██╗██║██║   ██║
  ██████╔╝██║╚██████╔╝    ██████╔╝██║  ██║██║ ╚████║╚██████╔╝
  ╚═════╝ ╚═╝ ╚═════╝     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
"""


@click.group()
def cli():
    """💥 BIG BANG — Universe as Code. One YAML file. Infinite worlds."""


@cli.command()
@click.argument("genesis_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=".", show_default=True, help="Output directory")
@click.option("--force", "-f", is_flag=True, help="Overwrite all files, including user edits")
@click.option("--dry-run", "-n", is_flag=True, help="Preview files that would be generated")
def bang(genesis_file: str, output: str, force: bool, dry_run: bool) -> None:
    """Create or update a universe from a genesis.yaml file.

    \b
    On first run, all files are generated.
    On subsequent runs, files you have edited are preserved — only
    unmodified generated files are updated. Use --force to overwrite all.

    \b
    Examples:
      big-bang bang genesis.yaml
      big-bang bang genesis.yaml --output ./projects
      big-bang bang genesis.yaml --dry-run
      big-bang bang genesis.yaml --force
    """
    click.secho(BANNER, fg="magenta", bold=True)
    click.secho("  Universe as Code — One file. Infinite worlds.\n", fg="white")

    if dry_run:
        click.secho("  DRY RUN — no files will be written\n", fg="yellow")

    click.echo(f"  {click.style('Parsing', fg='cyan')} {genesis_file} ...")

    try:
        universe = parser.parse(genesis_file)
    except (FileNotFoundError, ValueError) as exc:
        click.secho(f"\n  ERROR: {exc}", fg="red", bold=True)
        sys.exit(1)

    name = universe["name"]
    entities = universe.get("entities", [])
    flows = universe.get("flows", [])
    monetization = universe.get("monetization")
    auth_cfg = universe.get("auth", {})

    click.echo(f"\n  Universe  : {click.style(name, fg='yellow', bold=True)}")
    click.echo(f"  Type      : {universe.get('type', 'unknown')}")
    click.echo(f"  Entities  : {', '.join(e['name'] for e in entities) or 'none'}")
    click.echo(f"  Flows     : {', '.join(f['name'] for f in flows) or 'none'}")
    if auth_cfg.get("enabled"):
        click.echo(f"  Auth      : {auth_cfg.get('provider', 'jwt').upper()}")
    if monetization:
        plans = monetization.get("plans", [])
        click.echo(f"  Plans     : {', '.join(p['name'] for p in plans)}")

    active = registry.active_for(universe)
    click.echo(f"\n  Plugins   : {', '.join(p['name'] for p in active)}")
    click.echo()

    for plugin in active:
        click.echo(f"  {click.style('>', fg='green', bold=True)} {plugin['name']} — {plugin['description']}")
        time.sleep(0.06)

    click.echo()

    try:
        output_path, written, skipped = generator.generate(
            universe, output, force=force, dry_run=dry_run
        )
    except Exception as exc:
        click.secho(f"  ERROR: {exc}", fg="red", bold=True)
        sys.exit(1)

    if dry_run:
        click.secho("  Files that would be generated:", fg="cyan", bold=True)
        for f in written:
            click.echo(f"    {f}")
        click.echo()
        click.secho(f"  {len(written)} files total. Run without --dry-run to create them.", fg="white")
        return

    if skipped:
        click.secho(f"  Preserved {len(skipped)} user-edited file(s):", fg="yellow")
        for f in skipped:
            click.echo(f"    ~ {f}")
        click.echo()

    click.secho(f"  ✨ BIG BANG complete! {len(written)} file(s) written.", fg="magenta", bold=True)
    click.echo(f"  Universe  : {click.style(str(output_path), fg='cyan', bold=True)}")
    click.echo()
    click.secho("  Next steps:", fg="white", bold=True)
    click.echo(f"  1.  cd {output_path}")
    click.echo(f"  2.  cp .env.example .env")
    click.echo(f"  3.  docker-compose up -d")
    click.echo()
    click.secho(f"  API  → http://localhost:8000/docs", fg="cyan")
    click.secho(f"  App  → http://localhost:3000", fg="cyan")
    click.echo()


@cli.command(name="plugins")
def list_plugins() -> None:
    """List all registered plugins."""
    click.secho("\n  Registered plugins:\n", fg="white", bold=True)
    for p in registry.all():
        click.echo(f"  {click.style(p['name'], fg='cyan', bold=True)}")
        if p["description"]:
            click.echo(f"    {p['description']}")
    click.echo()


# Keep `python -m bigbang.cli genesis.yaml` working as a shortcut for `bang`
bang.name = "bang"
cli.add_command(bang)

# Convenience: `big-bang genesis.yaml` (no subcommand) falls through to `bang`
@click.command(hidden=True)
@click.pass_context
def _compat(ctx):
    pass


if __name__ == "__main__":
    cli()
