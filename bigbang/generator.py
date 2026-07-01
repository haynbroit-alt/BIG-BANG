import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from bigbang import lock
from bigbang.plugins import registry

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
    universe: dict,
    output_dir: str = ".",
    force: bool = False,
    dry_run: bool = False,
) -> tuple[Path, list[str], list[str]]:
    """
    Generate universe files from spec.

    Returns (output_path, written_files, skipped_files).
    skipped_files are files the user has modified since last generation.
    """
    name_slug = universe["name"].lower().replace(" ", "_").replace("-", "_")
    output = Path(output_dir) / f"universe_{name_slug}"

    if output.exists() and force and not dry_run:
        shutil.rmtree(output)
    elif not output.exists() and not dry_run:
        pass  # will be created below

    if not dry_run:
        _make_dirs(output, universe)

    env = _make_env()
    ctx = {"universe": universe, "name_slug": name_slug}

    # Load external plugins declared in genesis.yaml
    for plugin_name in universe.get("plugins", []):
        registry.load_external(plugin_name)

    # Collect all (template, dest) pairs from active plugins
    pairs: list[tuple[str, Path]] = []
    for plugin in registry.active_for(universe):
        pairs.extend(plugin["get_files"](universe, output, ctx))

    if dry_run:
        return output, [str(dest) for _, dest in pairs], []

    # Load existing lock to detect user modifications
    lock_data = {} if force else lock.load(output)

    written: list[Path] = []
    skipped: list[str] = []

    for template_name, dest in pairs:
        rel = str(dest.relative_to(output))
        if not force and lock.is_user_modified(output, rel, lock_data):
            skipped.append(rel)
            continue
        dest.parent.mkdir(parents=True, exist_ok=True)
        template = env.get_template(template_name)
        dest.write_text(template.render(**ctx), encoding="utf-8")
        written.append(dest)

    lock.save(output, universe["name"], written)
    return output, [str(p.relative_to(output)) for p in written], skipped


def _make_dirs(output: Path, universe: dict) -> None:
    dirs = [output / "backend", output / "frontend" / "static"]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["py_type"] = lambda t: _PY_TYPES.get(t, "str")
    env.filters["sa_type"] = lambda t: _SA_TYPES.get(t, "String(255)")
    env.filters["slug"] = lambda s: s.lower().replace(" ", "_").replace("-", "_")
    env.filters["plural"] = lambda s: s.lower() + "s"
    return env
