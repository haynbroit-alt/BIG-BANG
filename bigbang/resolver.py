"""
BIG BANG Semantic Resolver — Phase 3 of the compilation pipeline.

Responsibilities:
  - Infer entity relations from *_id fields (e.g. contact_id → Contact)
  - Build the entity dependency graph
  - Topological-sort entities so dependencies are emitted first
  - Emit diagnostics for unresolved references and cycles
"""
import re
from collections import deque

from bigbang.diagnostics import DiagnosticEngine
from bigbang.universe import Entity, Relation, Universe

_ID_RE = re.compile(r"^(.+)_id$")


def resolve(universe: Universe, diags: DiagnosticEngine) -> Universe:
    """
    Semantic analysis pass — mutates `universe` in place, returns it.
    Safe to call multiple times (idempotent: clears relations before re-inferring).
    """
    entity_names = {e.name for e in universe.entities}

    # ── Phase A: infer relations ──────────────────────────────────────────────
    for entity in universe.entities:
        entity.relations.clear()
        for f in entity.fields:
            m = _ID_RE.match(f.name)
            if not m:
                continue
            target = _find_entity(m.group(1), entity_names)
            if target and target != entity.name:
                entity.relations.append(
                    Relation(field_name=f.name, target=target, kind="many_to_one")
                )
                diags.info(
                    "R001",
                    f"Relation inferred: {entity.name}.{f.name} → {target}",
                    path=f"entities[{entity.name}].fields[{f.name}]",
                )
            elif not target:
                diags.warn(
                    "W001",
                    f"'{f.name}' looks like a foreign key but no matching entity found",
                    path=f"entities[{entity.name}].fields[{f.name}]",
                    hint=f"Add an entity named '{m.group(1).title()}' or rename the field",
                )

    # ── Phase B: build dependency graph ──────────────────────────────────────
    graph: dict[str, list[str]] = {e.name: [] for e in universe.entities}
    for entity in universe.entities:
        for rel in entity.relations:
            if rel.target in graph:
                graph[entity.name].append(rel.target)

    # ── Phase C: topological sort (Kahn's algorithm) ─────────────────────────
    universe.topo_order = _topo_sort(graph, diags)
    return universe


def _find_entity(raw: str, entity_names: set[str]) -> str | None:
    """Try several capitalisation conventions to match an entity name."""
    candidates = [
        raw.title(),
        raw.capitalize(),
        "".join(w.title() for w in raw.split("_")),
        raw.upper(),
        raw,
    ]
    for c in candidates:
        if c in entity_names:
            return c
    return None


def _topo_sort(graph: dict[str, list[str]], diags: DiagnosticEngine) -> list[str]:
    """
    Kahn's algorithm.  graph[A] = [B] means A depends on B (B must come first).
    Returns entities in dependency-first order.
    """
    # Reverse the dependency edges: if A→B (A depends on B), add rev edge B→A
    rev: dict[str, list[str]] = {n: [] for n in graph}
    in_degree: dict[str, int] = {n: 0 for n in graph}

    for node, deps in graph.items():
        for dep in deps:
            if dep in rev:
                rev[dep].append(node)
                in_degree[node] += 1

    queue = deque(n for n, deg in in_degree.items() if deg == 0)
    result: list[str] = []

    while queue:
        n = queue.popleft()
        result.append(n)
        for dependent in rev[n]:
            in_degree[dependent] -= 1
            if in_degree[dependent] == 0:
                queue.append(dependent)

    if len(result) < len(graph):
        cycle_nodes = [n for n in graph if n not in set(result)]
        diags.error(
            "E010",
            f"Circular entity dependency detected: {', '.join(cycle_nodes)}",
            hint="Check *_id fields for circular foreign-key references",
        )
        result.extend(cycle_nodes)

    return result
