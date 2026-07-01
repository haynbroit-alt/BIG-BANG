"""
BIG BANG compiler back-end.

Pipeline:
    Universe IR  →  Plugin Registry  →  Template Engine  →  Merger  →  Filesystem
"""
import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from bigbang import lock, merger
from bigbang.plugins import registry
from bigbang.universe import Universe

TEMPLATES_DIR = Path(__file__).parent / "templates"

_PY_TYPES = {
    "string": "str", "integer": "int", "float": "float",
    "boolean": "bool", "text": "str", "datetime": "datetime",
}
_SA_TYPES = {
    "string": "String(255)", "integer": "Integer", "float": "Float",
    "boolean": "Boolean", "text": "Text", "datetime": "DateTime",
}


def generate(
    universe: Universe,
    output_dir: str = ".",
    force: bool = False,
    dry_run: bool = False,
) -> tuple[Path, list[str], list[str]]:
    """
    Run the compiler for the given universe.

    Returns
    -------
    output_path  : Path
    written      : list of relative paths written / block-merged
    skipped      : list of relative paths skipped (user-modified, no --force)
    """
    output = Path(output_dir) / f"universe_{universe.name_slug}"

    if output.exists() and force and not dry_run:
        shutil.rmtree(output)

    if not dry_run:
        _make_dirs(output, universe)

    env = _make_env()
    ctx = {"universe": universe, "name_slug": universe.name_slug}

    # Load external plugins declared in genesis.yaml
    for plugin_name in universe.plugins:
        registry.load_external(plugin_name)

    # Collect (template, dest) from every active plugin
    pairs: list[tuple[str, Path]] = []
    for plugin in registry.active_for(universe):
        pairs.extend(plugin["get_files"](universe, output))

    if dry_run:
        return output, [str(d) for _, d in pairs], []

    lock_data = {} if force else lock.load(output)
    written: list[Path] = []
    skipped: list[str] = []

    for template_name, dest in pairs:
        rel = str(dest.relative_to(output))
        generated = env.get_template(template_name).render(**ctx)

        dest.parent.mkdir(parents=True, exist_ok=True)

        if merger.has_blocks(generated):
            # Block-level merge: BIG BANG owns the marked regions,
            # the user owns everything outside them.
            if dest.exists():
                existing = dest.read_text(encoding="utf-8")
                merged_content, updated, appended = merger.merge(existing, generated)
                dest.write_text(merged_content, encoding="utf-8")
            else:
                dest.write_text(generated, encoding="utf-8")
            written.append(dest)

        else:
            # File-level lock: skip files the user has edited since last run.
            if not force and lock.is_user_modified(output, rel, lock_data):
                skipped.append(rel)
                continue
            dest.write_text(generated, encoding="utf-8")
            written.append(dest)

    lock.save(output, universe.name, written)

    # Let active plugins do any post-processing
    for plugin in registry.active_for(universe):
        post = plugin.get("post_generate")
        if callable(post):
            post(universe, output)

    return (
        output,
        [str(p.relative_to(output)) for p in written],
        skipped,
    )


def _make_dirs(output: Path, universe: Universe) -> None:
    for d in [output / "backend", output / "frontend" / "static"]:
        d.mkdir(parents=True, exist_ok=True)


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["py_type"]  = lambda t: _PY_TYPES.get(t, "str")
    env.filters["sa_type"]  = lambda t: _SA_TYPES.get(t, "String(255)")
    env.filters["slug"]     = lambda s: s.lower().replace(" ", "_").replace("-", "_")
    env.filters["plural"]   = lambda s: s.lower() + "s"
    return env
