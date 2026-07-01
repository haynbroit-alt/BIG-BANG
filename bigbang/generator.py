import shutil
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"

_PY_TYPES = {
    "string": "str",
    "integer": "int",
    "float": "float",
    "boolean": "bool",
    "text": "str",
    "datetime": "datetime",
}

_SA_TYPES = {
    "string": "String(255)",
    "integer": "Integer",
    "float": "Float",
    "boolean": "Boolean",
    "text": "Text",
    "datetime": "DateTime",
}


def generate(universe: dict, output_dir: str = ".", force: bool = False) -> Path:
    name_slug = universe["name"].lower().replace(" ", "_").replace("-", "_")
    output = Path(output_dir) / f"universe_{name_slug}"

    if output.exists():
        if not force:
            raise FileExistsError(
                f"Directory '{output}' already exists."
            )
        shutil.rmtree(output)

    _make_dirs(output)

    env = _make_env()
    ctx = {"universe": universe, "name_slug": name_slug}

    _render_all(env, output, ctx)
    return output


def _make_dirs(output: Path) -> None:
    for d in [
        output / "backend",
        output / "frontend" / "static",
    ]:
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


def _render(env: Environment, template_name: str, output_path: Path, ctx: dict) -> None:
    template = env.get_template(template_name)
    output_path.write_text(template.render(**ctx), encoding="utf-8")


def _render_all(env: Environment, output: Path, ctx: dict) -> None:
    pairs = [
        ("backend/app.py.j2",             output / "backend" / "app.py"),
        ("backend/database.py.j2",         output / "backend" / "database.py"),
        ("backend/models.py.j2",           output / "backend" / "models.py"),
        ("backend/schemas.py.j2",          output / "backend" / "schemas.py"),
        ("backend/routes.py.j2",           output / "backend" / "routes.py"),
        ("backend/requirements.txt.j2",    output / "backend" / "requirements.txt"),
        ("backend/Dockerfile.j2",          output / "backend" / "Dockerfile"),
        ("frontend/index.html.j2",         output / "frontend" / "index.html"),
        ("frontend/app.js.j2",             output / "frontend" / "static" / "app.js"),
        ("frontend/styles.css.j2",         output / "frontend" / "static" / "styles.css"),
        ("docker/docker-compose.yml.j2",   output / "docker-compose.yml"),
        ("docker/env.example.j2",          output / ".env.example"),
        ("docs/README.md.j2",              output / "README.md"),
    ]
    for template_name, dest in pairs:
        _render(env, template_name, dest, ctx)
