"""
BIG BANG Compilation Pipeline — multi-pass compiler orchestration.

Phases
------
1. Parse      YAML → Universe IR
2. Resolve    Semantic analysis: relations, dependency graph, topo sort
3. Schedule   Plugin dependency resolution, topological load order
4. Build      Universe IR → UniverseGraph (raw)
5. Transform  Plugin passes: each plugin enriches the graph (IR → IR)
6. Diff       Compare to previous snapshot (incremental compilation)
7. Emit       Emitters read the final graph → (template, path) pairs → files
8. Snapshot   Persist Universe IR for the next run

Architecture contract
---------------------
- Plugins   : format-agnostic IR transformations   (add nodes/edges)
- Emitters  : format-specific output generators    (read graph → files)
- Templates : receive both `universe` and `graph` in context

This separation guarantees: adding a NestJS backend requires only a new
emitter, zero changes to any plugin.
"""
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from bigbang import lock, merger, snapshot
from bigbang.diagnostics import Diagnostic, DiagnosticEngine
from bigbang.differ import UniverseDiff
from bigbang.differ import diff as compute_diff
from bigbang.emitters import emitter_registry
from bigbang.ir import UniverseGraph
from bigbang.ir_builder import build_graph
from bigbang.parser import parse as _parse
from bigbang.plugins import registry
from bigbang.resolver import resolve
from bigbang.universe import Universe
from jinja2 import Environment, FileSystemLoader

TEMPLATES_DIR = Path(__file__).parent / "templates"

_PY_TYPES = {
    "string": "str", "integer": "int", "float": "float",
    "boolean": "bool", "text": "str", "datetime": "datetime",
}
_SA_TYPES = {
    "string": "String(255)", "integer": "Integer", "float": "Float",
    "boolean": "Boolean", "text": "Text", "datetime": "DateTime",
}


# ── Result types ──────────────────────────────────────────────────────────────

@dataclass
class PhaseResult:
    name: str
    duration_ms: float
    note: str = ""


@dataclass
class CompilationResult:
    output_path: Path
    universe: Optional[Universe] = None
    graph: Optional[UniverseGraph] = None
    written: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    diagnostics: list[Diagnostic] = field(default_factory=list)
    diff: Optional[UniverseDiff] = None
    phases: list[PhaseResult] = field(default_factory=list)
    total_ms: float = 0.0

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level.value == "error"]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level.value == "warning"]

    @property
    def infos(self) -> list[Diagnostic]:
        return [d for d in self.diagnostics if d.level.value == "info"]


# ── Pipeline ──────────────────────────────────────────────────────────────────

class Pipeline:
    """
    Stateless compiler pipeline.  One instance can compile multiple universes.
    Holds only the pre-built Jinja2 environment (expensive to construct).
    """

    def __init__(self) -> None:
        self._env = _make_env()

    def compile(
        self,
        genesis_file: str,
        output_dir: str = ".",
        force: bool = False,
        dry_run: bool = False,
    ) -> CompilationResult:
        t_start = time.perf_counter()
        diags = DiagnosticEngine()
        phases: list[PhaseResult] = []

        # ── Phase 1: Parse ────────────────────────────────────────────────────
        universe, output = self._phase_parse(genesis_file, output_dir, diags, phases, t_start)
        if universe is None:
            return CompilationResult(output_path=output, diagnostics=diags.all,
                                     phases=phases, total_ms=_ms(t_start))

        # ── Phase 2: Resolve ──────────────────────────────────────────────────
        self._phase_resolve(universe, diags, phases)
        if diags.has_errors:
            return CompilationResult(output_path=output, universe=universe,
                                     diagnostics=diags.all, phases=phases,
                                     total_ms=_ms(t_start))

        # ── Phase 3: Schedule ─────────────────────────────────────────────────
        active_plugins = self._phase_schedule(universe, diags, phases)
        if diags.has_errors:
            return CompilationResult(output_path=output, universe=universe,
                                     diagnostics=diags.all, phases=phases,
                                     total_ms=_ms(t_start))

        # ── Phase 4: Build graph ──────────────────────────────────────────────
        graph = self._phase_build(universe, phases)

        # ── Phase 5: Transform (plugin passes) ───────────────────────────────
        self._phase_transform(active_plugins, graph, phases)

        # ── Phase 6: Diff ─────────────────────────────────────────────────────
        udiff = self._phase_diff(universe, output, dry_run, phases)

        if dry_run:
            active_emitters = emitter_registry.active_for(graph)
            pairs = [p for em in active_emitters for p in em.get_pairs(graph, output)]
            return CompilationResult(
                output_path=output, universe=universe, graph=graph,
                written=[str(d) for _, d in pairs],
                diagnostics=diags.all, diff=udiff, phases=phases,
                total_ms=_ms(t_start),
            )

        # ── Phase 7: Emit ─────────────────────────────────────────────────────
        written, skipped = self._phase_emit(universe, graph, output, force, phases)

        # ── Phase 8: Snapshot ─────────────────────────────────────────────────
        self._phase_snapshot(universe, output, phases)

        return CompilationResult(
            output_path=output,
            universe=universe,
            graph=graph,
            written=[str(p.relative_to(output)) for p in written],
            skipped=skipped,
            diagnostics=diags.all,
            diff=udiff,
            phases=phases,
            total_ms=_ms(t_start),
        )

    # ── Phase implementations ─────────────────────────────────────────────────

    def _phase_parse(
        self,
        genesis_file: str,
        output_dir: str,
        diags: DiagnosticEngine,
        phases: list,
        t_start: float,
    ) -> tuple[Optional[Universe], Path]:
        t = time.perf_counter()
        try:
            universe = _parse(genesis_file)
        except (FileNotFoundError, ValueError) as exc:
            diags.error("E000", str(exc), hint="Check your genesis.yaml for syntax errors")
            phases.append(PhaseResult("Parse", _ms(t), "FAILED"))
            return None, Path(output_dir)

        output = Path(output_dir) / f"universe_{universe.name_slug}"
        n = len(universe.entities)
        phases.append(PhaseResult(
            "Parse", _ms(t),
            f"{universe.name} · {universe.type} · {n} entit{'y' if n == 1 else 'ies'}",
        ))
        return universe, output

    def _phase_resolve(self, universe: Universe, diags: DiagnosticEngine, phases: list) -> None:
        t = time.perf_counter()
        resolve(universe, diags)
        rel_count = sum(len(e.relations) for e in universe.entities)
        note = f"{rel_count} relation(s) inferred" if rel_count else "no relations"
        if universe.topo_order:
            note += f" · order: {' → '.join(universe.topo_order)}"
        phases.append(PhaseResult("Resolve", _ms(t), note))

    def _phase_schedule(
        self,
        universe: Universe,
        diags: DiagnosticEngine,
        phases: list,
    ) -> list[dict]:
        t = time.perf_counter()
        try:
            active = registry.resolve_order(universe)
        except ValueError as exc:
            diags.error("E020", str(exc))
            phases.append(PhaseResult("Schedule", _ms(t), "FAILED"))
            return []

        load_order = " → ".join(p["name"] for p in active)
        phases.append(PhaseResult("Schedule", _ms(t), f"{len(active)} plugin(s): {load_order}"))
        return active

    def _phase_build(self, universe: Universe, phases: list) -> UniverseGraph:
        t = time.perf_counter()
        graph = build_graph(universe)
        n_nodes = len(graph.all_nodes())
        n_edges = len(graph.edges_of_kind("relation")) + len(graph.edges_of_kind("permission"))
        phases.append(PhaseResult(
            "Build", _ms(t),
            f"{n_nodes} node(s), {n_edges} edge(s)",
        ))
        return graph

    def _phase_transform(self, active_plugins: list[dict], graph: UniverseGraph, phases: list) -> None:
        t = time.perf_counter()
        transforms_run = 0
        nodes_before = len(graph.all_nodes())

        for plugin in active_plugins:
            transform_fn = plugin.get("transform")
            if callable(transform_fn):
                transform_fn(graph)
                transforms_run += 1

        nodes_added = len(graph.all_nodes()) - nodes_before
        phases.append(PhaseResult(
            "Transform", _ms(t),
            f"{transforms_run} transform(s) · +{nodes_added} node(s) added",
        ))

    def _phase_diff(
        self,
        universe: Universe,
        output: Path,
        dry_run: bool,
        phases: list,
    ) -> Optional[UniverseDiff]:
        t = time.perf_counter()
        if dry_run:
            phases.append(PhaseResult("Diff", _ms(t), "skipped (dry-run)"))
            return None
        old = snapshot.load(output)
        if old is None:
            phases.append(PhaseResult("Diff", _ms(t), "first compilation — full emit"))
            return None
        udiff = compute_diff(old, universe)
        phases.append(PhaseResult("Diff", _ms(t), udiff.summary()))
        return udiff

    def _phase_emit(
        self,
        universe: Universe,
        graph: UniverseGraph,
        output: Path,
        force: bool,
        phases: list,
    ) -> tuple[list[Path], list[str]]:
        t = time.perf_counter()
        output.mkdir(parents=True, exist_ok=True)
        for d in [output / "backend", output / "frontend" / "static"]:
            d.mkdir(parents=True, exist_ok=True)

        # Emitters read the final graph — plugins have already transformed it
        active_emitters = emitter_registry.active_for(graph)
        pairs: list[tuple[str, Path]] = []
        for emitter in active_emitters:
            pairs.extend(emitter.get_pairs(graph, output))

        # Template context: both universe (backward compat) and graph (new)
        ctx = {"universe": universe, "graph": graph, "name_slug": universe.name_slug}
        lock_data = {} if force else lock.load(output)
        written: list[Path] = []
        skipped: list[str] = []

        for template_name, dest in pairs:
            rel = str(dest.relative_to(output))
            generated = self._env.get_template(template_name).render(**ctx)
            dest.parent.mkdir(parents=True, exist_ok=True)

            if merger.has_blocks(generated):
                if dest.exists():
                    existing = dest.read_text(encoding="utf-8")
                    merged, _, _ = merger.merge(existing, generated)
                    dest.write_text(merged, encoding="utf-8")
                else:
                    dest.write_text(generated, encoding="utf-8")
                written.append(dest)
            else:
                if not force and lock.is_user_modified(output, rel, lock_data):
                    skipped.append(rel)
                    continue
                dest.write_text(generated, encoding="utf-8")
                written.append(dest)

        lock.save(output, universe.name, written)

        # Post-emit hooks
        for emitter in active_emitters:
            emitter.post_emit(graph, output)

        note = f"{len(written)} written"
        if skipped:
            note += f", {len(skipped)} preserved"
        phases.append(PhaseResult("Emit", _ms(t), note))
        return written, skipped

    def _phase_snapshot(self, universe: Universe, output: Path, phases: list) -> None:
        t = time.perf_counter()
        snapshot.save(output, universe)
        phases.append(PhaseResult("Snapshot", _ms(t), ".bigbang.snapshot.json"))


# ── Helpers ───────────────────────────────────────────────────────────────────

def _ms(t_start: float) -> float:
    return (time.perf_counter() - t_start) * 1000


def _make_env() -> Environment:
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        trim_blocks=True,
        lstrip_blocks=True,
        keep_trailing_newline=True,
    )
    env.filters["py_type"] = lambda t: _PY_TYPES.get(t, "str")
    env.filters["sa_type"] = lambda t: _SA_TYPES.get(t, "String(255)")
    env.filters["slug"]    = lambda s: s.lower().replace(" ", "_").replace("-", "_")
    env.filters["plural"]  = lambda s: s.lower() + "s"
    return env


# ── Module-level singleton ────────────────────────────────────────────────────

_pipeline = Pipeline()


def compile(
    genesis_file: str,
    output_dir: str = ".",
    force: bool = False,
    dry_run: bool = False,
) -> CompilationResult:
    """Compile a genesis.yaml into a universe. Module-level convenience wrapper."""
    return _pipeline.compile(genesis_file, output_dir, force=force, dry_run=dry_run)
