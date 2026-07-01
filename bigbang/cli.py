#!/usr/bin/env python3
import sys
import time

import click

from . import parser, generator


BANNER = r"""
  ██████╗ ██╗ ██████╗     ██████╗  █████╗ ███╗   ██╗ ██████╗
  ██╔══██╗██║██╔════╝     ██╔══██╗██╔══██╗████╗  ██║██╔════╝
  ██████╔╝██║██║  ███╗    ██████╔╝███████║██╔██╗ ██║██║  ███╗
  ██╔══██╗██║██║   ██║    ██╔══██╗██╔══██║██║╚██╗██║██║   ██║
  ██████╔╝██║╚██████╔╝    ██████╔╝██║  ██║██║ ╚████║╚██████╔╝
  ╚═════╝ ╚═╝ ╚═════╝     ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═══╝ ╚═════╝
"""

STEPS = [
    ("Backend", "FastAPI + SQLAlchemy + Pydantic"),
    ("Frontend", "Dashboard + JavaScript + CSS"),
    ("Deployment", "Docker Compose + Dockerfile"),
    ("Documentation", "README + API reference"),
]


@click.command()
@click.argument("genesis_file", type=click.Path(exists=True))
@click.option("--output", "-o", default=".", show_default=True, help="Output directory")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing universe directory")
def bang(genesis_file: str, output: str, force: bool) -> None:
    """💥 BIG BANG — Create a universe from a genesis.yaml file.

    \b
    Examples:
      big-bang genesis.yaml
      big-bang genesis.yaml --output ./projects --force
    """
    click.secho(BANNER, fg="magenta", bold=True)
    click.secho("  The Universe Generator — One file. Infinite worlds.\n", fg="white")

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

    click.echo(f"\n  Universe  : {click.style(name, fg='yellow', bold=True)}")
    click.echo(f"  Type      : {universe.get('type', 'unknown')}")
    click.echo(f"  Entities  : {', '.join(e['name'] for e in entities) or 'none'}")
    click.echo(f"  Flows     : {', '.join(f['name'] for f in flows) or 'none'}")
    if monetization:
        plans = monetization.get("plans", [])
        click.echo(f"  Plans     : {', '.join(p['name'] for p in plans)}")
    click.echo()

    for label, detail in STEPS:
        click.echo(f"  {click.style('>', fg='green', bold=True)} Generating {label} ({detail}) ...")
        time.sleep(0.08)

    click.echo()

    try:
        output_path = generator.generate(universe, output, force=force)
    except FileExistsError as exc:
        click.secho(f"  ERROR: {exc}", fg="red", bold=True)
        click.secho("  Use --force to overwrite.", fg="yellow")
        sys.exit(1)
    except Exception as exc:
        click.secho(f"  ERROR: Unexpected failure — {exc}", fg="red", bold=True)
        sys.exit(1)

    click.secho(f"  ✨ BIG BANG complete!", fg="magenta", bold=True)
    click.echo(f"  Universe born in: {click.style(str(output_path), fg='cyan', bold=True)}")
    click.echo()
    click.secho("  Next steps:", fg="white", bold=True)
    click.echo(f"  1.  cd {output_path}")
    click.echo(f"  2.  cp .env.example .env     # configure environment")
    click.echo(f"  3.  docker-compose up -d     # ignite the universe")
    click.echo()
    click.secho(f"  API  → http://localhost:8000/docs", fg="cyan")
    click.secho(f"  App  → http://localhost:3000", fg="cyan")
    click.echo()


if __name__ == "__main__":
    bang()
