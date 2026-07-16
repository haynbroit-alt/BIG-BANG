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

    # ── Universe summary ──────────────────────────────────────────────────────
    u = result.universe
    g = result.graph
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
        total_rels = sum(len(e.relations) for e in u.entities)
        if total_rels:
            click.echo(f"  Relations : {total_rels} inferred")
    if g:
        n_nodes = len(g.all_nodes())
        n_edges = sum(1 for _ in g.edges_of_kind("relation")) + \
                  sum(1 for _ in g.edges_of_kind("signs")) + \
                  sum(1 for _ in g.edges_of_kind("owns"))
        click.echo(f"  IR Graph  : {n_nodes} nodes · {n_edges} edges")
    if u or g:
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


@cli.command(name="serve")
@click.option("--host", default="127.0.0.1", show_default=True, help="Bind address")
@click.option("--port", default=7432, show_default=True, help="TCP port")
@click.option("--reload", is_flag=True, help="Auto-reload on code changes (dev mode)")
def serve(host: str, port: int, reload: bool) -> None:
    """Start the BIG BANG HTTP API server.

    \b
    Exposes the compiler pipeline over REST:
      GET  /health          — liveness probe
      GET  /plugins         — registered plugins
      POST /validate        — parse + resolve, no output
      POST /compile         — full 8-phase compilation
      POST /compile/dry-run — list would-be files, no write

    \b
    Examples:
      big-bang serve
      big-bang serve --host 0.0.0.0 --port 8080
      big-bang serve --reload
    """
    try:
        import uvicorn
    except ImportError:
        click.secho("  uvicorn is required: pip install uvicorn", fg="red")
        sys.exit(1)

    click.secho(BANNER, fg="magenta", bold=True)
    click.secho("  Universe as Code — API mode\n", fg="white")
    click.secho(f"  Listening on  http://{host}:{port}", fg="cyan", bold=True)
    click.secho(f"  Docs          http://{host}:{port}/docs\n", fg="cyan")

    uvicorn.run(
        "bigbang.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


@cli.command(name="studio")
@click.argument("description")
@click.option("--output", "-o", default=None, help="Write genesis.yaml to this path (default: stdout)")
@click.option("--model", default="claude-opus-4-8", show_default=True, help="Claude model to use")
def studio_cmd(description: str, output: str | None, model: str) -> None:
    """Generate a genesis.yaml from a natural-language description.

    \b
    Requires ANTHROPIC_API_KEY environment variable.

    \b
    Examples:
      big-bang studio "A SaaS CRM with deals, contacts, and email flows"
      big-bang studio "A todo API with tags and priorities" -o genesis.yaml
      big-bang studio "An e-commerce platform with subscriptions" --model claude-haiku-4-5
    """
    from . import studio as _studio

    click.secho(BANNER, fg="magenta", bold=True)
    click.secho("  Studio — natural language → genesis.yaml\n", fg="white")
    click.secho(f"  Generating universe for: {click.style(description[:60], fg='cyan')}\n", fg="white")

    try:
        buf = None
        if output is None:
            import io
            buf = io.StringIO()
            yaml_content = _studio.generate(description, model=model, stream_to=None)
        else:
            yaml_content = _studio.generate(description, model=model)
    except (ImportError, ValueError) as exc:
        click.secho(f"  Error: {exc}", fg="red")
        sys.exit(1)
    except Exception as exc:
        click.secho(f"  Unexpected error: {exc}", fg="red")
        sys.exit(1)

    if output:
        from pathlib import Path
        Path(output).write_text(yaml_content, encoding="utf-8")
        click.secho(f"  ✨ genesis.yaml written to {click.style(output, fg='cyan', bold=True)}", fg="magenta", bold=True)
        click.secho("\n  Next steps:", fg="white", bold=True)
        click.echo(f"  1.  big-bang bang {output}")
        click.echo()
    else:
        click.echo(yaml_content)


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
