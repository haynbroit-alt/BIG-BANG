"""
BIG BANG API Server — HTTP interface to the compiler pipeline.

Endpoints
---------
GET  /health                — liveness probe
GET  /plugins               — registered plugins
POST /validate              — parse + resolve only, no file output
POST /compile               — full 8-phase compilation
POST /compile/dry-run       — compile without writing files (returns would-be paths)
POST /studio/generate       — natural language → genesis.yaml via Claude

Transport
---------
All POST endpoints accept genesis YAML in two forms:
  • Multipart file upload  — field name: "file"
  • JSON body              — { "content": "<yaml string>" }
"""
import tempfile
from pathlib import Path
from typing import Annotated, Optional

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from . import pipeline as pp
from . import serializers as ser
from . import studio
from .plugins import registry
from .parser import parse as _parse
from .resolver import resolve
from .diagnostics import DiagnosticEngine

_VERSION = "0.5.0"

app = FastAPI(
    title="BIG BANG",
    description="Universe as Code — One YAML file. Infinite worlds.",
    version=_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok", "version": _VERSION}


# ── Plugins ───────────────────────────────────────────────────────────────────

@app.get("/plugins", tags=["meta"])
async def list_plugins() -> dict:
    plugins = [
        {
            "name":        p["name"],
            "description": p["description"],
            "requires":    p["requires"],
        }
        for p in registry.all()
    ]
    return {"plugins": plugins, "count": len(plugins)}


# ── Shared YAML extraction ────────────────────────────────────────────────────

async def _extract_yaml(request: Request) -> str:
    """Accept YAML as multipart file OR as JSON { content: '...' }."""
    ct = request.headers.get("content-type", "")
    if "multipart/form-data" in ct:
        form = await request.form()
        f = form.get("file")
        if f is None:
            raise HTTPException(422, detail="Multipart field 'file' is required")
        return (await f.read()).decode("utf-8")
    elif "application/json" in ct or "application/x-yaml" in ct or "text/" in ct:
        body = await request.body()
        if "application/json" in ct:
            import json
            try:
                data = json.loads(body)
            except json.JSONDecodeError as exc:
                raise HTTPException(422, detail=f"Invalid JSON: {exc}") from exc
            if "content" not in data:
                raise HTTPException(422, detail="JSON body must include 'content' field")
            return data["content"]
        return body.decode("utf-8")
    else:
        body = await request.body()
        if body:
            return body.decode("utf-8")
        raise HTTPException(
            422,
            detail="Send genesis YAML as: multipart file upload, "
                   "JSON { content: '...' }, or raw text/YAML body",
        )


def _write_temp(content: str) -> str:
    """Write YAML content to a temp file and return its path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", encoding="utf-8", delete=False
    )
    tmp.write(content)
    tmp.flush()
    tmp.close()
    return tmp.name


# ── Validate ─────────────────────────────────────────────────────────────────

@app.post("/validate", tags=["compiler"])
async def validate(request: Request) -> JSONResponse:
    """Parse and semantically resolve a genesis.yaml. No files are written."""
    content = await _extract_yaml(request)
    tmp_path = _write_temp(content)
    try:
        universe = _parse(tmp_path)
    except FileNotFoundError as exc:
        return JSONResponse({"success": False, "errors": [{"code": "E000", "message": str(exc)}]})
    except ValueError as exc:
        return JSONResponse({"success": False, "errors": [{"code": "E000", "message": str(exc)}]})
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    diags = DiagnosticEngine()
    resolve(universe, diags)

    return JSONResponse({
        "success":  not diags.has_errors,
        "universe": ser.universe(universe),
        "errors":   [ser.diagnostic(d) for d in diags.errors],
        "warnings": [ser.diagnostic(d) for d in diags.warnings],
        "infos":    [ser.diagnostic(d) for d in diags.infos],
    })


# ── Compile ───────────────────────────────────────────────────────────────────

@app.post("/compile", tags=["compiler"])
async def compile_universe(request: Request) -> JSONResponse:
    """Full 8-phase compilation. Files are written to a temporary directory."""
    content = await _extract_yaml(request)
    tmp_input = _write_temp(content)
    tmp_output = tempfile.mkdtemp(prefix="bigbang_out_")
    try:
        result = pp.compile(tmp_input, tmp_output)
    finally:
        Path(tmp_input).unlink(missing_ok=True)

    return JSONResponse(ser.compilation_result(result))


# ── Compile / dry-run ─────────────────────────────────────────────────────────

@app.post("/compile/dry-run", tags=["compiler"])
async def compile_dry_run(request: Request) -> JSONResponse:
    """Compile without writing any files. Returns the list of would-be paths."""
    content = await _extract_yaml(request)
    tmp_input = _write_temp(content)
    tmp_output = tempfile.mkdtemp(prefix="bigbang_dry_")
    try:
        result = pp.compile(tmp_input, tmp_output, dry_run=True)
    finally:
        Path(tmp_input).unlink(missing_ok=True)

    return JSONResponse(ser.compilation_result(result))


# ── Studio ────────────────────────────────────────────────────────────────────

class _StudioRequest(BaseModel):
    description: str
    model: str = "claude-opus-4-8"


@app.post("/studio/generate", tags=["studio"])
async def studio_generate(body: _StudioRequest) -> JSONResponse:
    """Generate a genesis.yaml from a natural-language description via Claude.

    Requires the ``anthropic`` package and an ``ANTHROPIC_API_KEY`` env var.
    The generated YAML is automatically validated through the compiler pipeline.
    """
    try:
        yaml_content = studio.generate(body.description, model=body.model)
    except (ImportError, ValueError) as exc:
        return JSONResponse(
            {"success": False, "yaml": None, "universe": None, "warnings": [],
             "errors": [{"code": "E000", "message": str(exc)}]},
            status_code=503,
        )
    except Exception as exc:
        return JSONResponse(
            {"success": False, "yaml": None, "universe": None, "warnings": [],
             "errors": [{"code": "E000", "message": str(exc)}]},
            status_code=500,
        )

    tmp_path = _write_temp(yaml_content)
    try:
        universe = _parse(tmp_path)
        diags = DiagnosticEngine()
        resolve(universe, diags)
        return JSONResponse({
            "success": True,
            "yaml": yaml_content,
            "universe": ser.universe(universe),
            "warnings": [ser.diagnostic(d) for d in diags.warnings],
            "errors": [],
        })
    except (ValueError, KeyError, Exception) as exc:
        return JSONResponse({
            "success": False,
            "yaml": yaml_content,
            "universe": None,
            "warnings": [],
            "errors": [{"code": "E000",
                        "message": f"Generated YAML failed validation: {exc}"}],
        })
    finally:
        Path(tmp_path).unlink(missing_ok=True)
