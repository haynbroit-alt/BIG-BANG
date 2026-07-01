#!/usr/bin/env python3
import sys

import click

from . import parser
from . import pipeline as pp
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
    """BIG BANG — Universe as Code. One YAML file. Infinite worlds."""


@cli.command()
@click.argument("genesis_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=".", show_default=True, help="Output directory")
@click.option("--force", "-f", is_flag=True, help="Overwrite all files, including user edits")
@click.option("--dry-run", "-n", is_flag=True, help="Preview files without writing them")
@click.option("--verbose", "-v", is_flag=True, help="Show all diagnostics (including info)")
def bang(genesis_file: str, output: str, force: bool, dry_run: bool, verbose: bool) -> None:
    """Compile a genesis.yaml into a deployable universe.

    \b
    First run   — all files generated from scratch.
    Subsequent  — block-merged files regenerated; user-edited files preserved.
    --force     — overwrite everything, including user edits.

    \b
    Examples:
      big-bang bang genesis.yaml
      big-bang bang examples/saas_crm.yaml --output ./projects
      big-bang bang genesis.yaml --dry-run
      big-bang bang genesis.yaml --force
    """
    click.secho(BANNER, fg="magenta", bold=True)
    click.secho("  Universe as Code — One file. Infinite worlds.\n", fg="white")

    if dry_run:
        click.secho("  DRY RUN — no files will be written\n", fg="yellow")

    click.echo(f"  {click.style('Compiling', fg='cyan')} {genesis_file} ...\n")

    # Run the full compilation pipeline
    result = pp.compile(genesis_file, output, force=force, dry_run=dry_run)

    # ── Errors & warnings ─────────────────────────────────────────────────────
    for d in result.warnings:
        click.secho(d.coloured(), fg="yellow")
    if result.warnings:
        click.echo()

    if result.errors:
        for d in result.errors:
            click.secho(d.coloured(), fg="red")
        click.echo()
        click.secho("  Compilation failed.", fg="red", bold=True)
        sys.exit(1)

    # ── Universe summary (available after parse phase) ─────────────────────────
    u = result.universe
    if u:
        click.echo(f"  Universe  : {click.style(u.name, fg='yellow', bold=True)}")
        click.echo(f"  Type      : {u.type}")
        entity_line = ", ".join(e.name for e in u.ordered_entities()) or "none"
        click.echo(f"  Entities  : {entity_line}")
        click.echo(f"  Flows     : {', '.join(f.name for f in u.flows) or 'none'}")
        if u.auth.enabled:
            click.echo(f"  Auth      : {u.auth.provider.upper()}")
        if u.security.ed25519:
            click.echo(f"  Security  : Ed25519 proof ledger")
        if u.monetization:
            click.echo(f"  Plans     : {', '.join(p.name for p in u.monetization.plans)}")
        # Relation summary
        total_rels = sum(len(e.relations) for e in u.entities)
        if total_rels:
            click.echo(f"  Relations : {total_rels} inferred")
        click.echo()

    # ── Phase timeline ────────────────────────────────────────────────────────
    click.secho("  Compilation phases:", fg="white", bold=True)
    for phase in result.phases:
        failed = "FAILED" in phase.note
        colour = "red" if failed else "green"
        tick   = "✗" if failed else "✓"
        note   = f"  {phase.note}" if phase.note else ""
        click.echo(
            f"  {click.style(tick, fg=colour)}  "
            f"{click.style(phase.name, bold=True):<12}"
            f"  {phase.duration_ms:5.0f}ms"
            f"{click.style(note, fg='white' if not failed else 'red', dim=not failed)}"
        )
    click.echo()

    # ── Verbose info diagnostics ──────────────────────────────────────────────
    if verbose and result.infos:
        click.secho("  Diagnostics:", fg="white", bold=True)
        for d in result.infos:
            click.echo(d.coloured())
        click.echo()

    # ── Diff summary (incremental) ────────────────────────────────────────────
    if result.diff and not result.diff.is_empty:
        click.secho("  Changes detected:", fg="cyan", bold=True)
        for ed in result.diff.entity_deltas:
            sym = {"added": "+", "removed": "-", "modified": "~"}[ed.kind]
            parts = f" ({len(ed.field_deltas)} field change(s))" if ed.field_deltas else ""
            click.echo(f"    {sym} {ed.name}{parts}")
        click.echo()

    if dry_run:
        click.secho("  Files that would be generated:", fg="cyan", bold=True)
        for f in result.written:
            click.echo(f"    {f}")
        click.echo()
        click.secho(
            f"  {len(result.written)} files total. Run without --dry-run to generate.",
            fg="white",
        )
        return

    if result.skipped:
        click.secho(f"  Preserved {len(result.skipped)} user-edited file(s):", fg="yellow")
        for f in result.skipped:
            click.echo(f"    ~ {f}")
        click.echo()

    click.secho(
        f"  ✨ Universe compiled — {len(result.written)} file(s) in {result.total_ms:.0f}ms.",
        fg="magenta",
        bold=True,
    )
    click.echo(f"  Output    : {click.style(str(result.output_path), fg='cyan', bold=True)}")
    click.echo()
    click.secho("  Next steps:", fg="white", bold=True)
    click.echo(f"  1.  cd {result.output_path}")
    click.echo(f"  2.  cp .env.example .env")
    click.echo(f"  3.  docker-compose up -d")
    click.echo()
    click.secho("  API  → http://localhost:8000/docs", fg="cyan")
    click.secho("  App  → http://localhost:3000", fg="cyan")
    click.echo()


@cli.command(name="plugins")
def list_plugins() -> None:
    """List all registered plugins with their dependency declarations."""
    click.secho("\n  Registered plugins:\n", fg="white", bold=True)
    for p in registry.all():
        name = click.style(p["name"], fg="cyan", bold=True)
        requires = f"  requires: [{', '.join(p['requires'])}]" if p.get("requires") else ""
        click.echo(f"  {name}{requires}")
        if p["description"]:
            click.echo(f"    {p['description']}")
    click.echo()


# Keep `python -m bigbang.cli genesis.yaml` working as a shortcut for `bang`
bang.name = "bang"
cli.add_command(bang)


if __name__ == "__main__":
    cli()
