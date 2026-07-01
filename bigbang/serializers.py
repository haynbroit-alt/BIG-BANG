"""
JSON serialization helpers for BIG BANG pipeline results.

Converts internal dataclass instances to plain dicts suitable for API responses.
"""
from .diagnostics import Diagnostic
from .pipeline import CompilationResult, PhaseResult
from .universe import (
    AuthConfig, Entity, Flow, Monetization, Plan, Relation,
    Role, Security, Universe, UniverseField,
)


# ── Low-level serializers ─────────────────────────────────────────────────────

def _field(f: UniverseField) -> dict:
    return {"name": f.name, "type": f.type, "required": f.required, "computed": f.computed}


def _relation(r: Relation) -> dict:
    return {"field_name": r.field_name, "target": r.target, "kind": r.kind}


def _entity(e: Entity) -> dict:
    return {
        "name":      e.name,
        "slug":      e.slug,
        "fields":    [_field(f) for f in e.fields],
        "relations": [_relation(r) for r in e.relations],
    }


def _flow(f: Flow) -> dict:
    return {
        "name":    f.name,
        "trigger": f.trigger,
        "steps":   [{"action": s.action} for s in f.steps],
    }


def _role(r: Role) -> dict:
    return {"name": r.name, "permissions": r.permissions}


def _plan(p: Plan) -> dict:
    return {"name": p.name, "price": p.price, "currency": p.currency}


def _auth(a: AuthConfig) -> dict:
    return {"enabled": a.enabled, "provider": a.provider,
            "user_fields": [_field(f) for f in a.user_fields]}


def _security(s: Security) -> dict:
    return {"ed25519": s.ed25519, "ledger": s.ledger}


def _monetization(m: Monetization | None) -> dict | None:
    if m is None:
        return None
    return {"model": m.model, "plans": [_plan(p) for p in m.plans]}


def universe(u: Universe) -> dict:
    return {
        "name":         u.name,
        "name_slug":    u.name_slug,
        "type":         u.type,
        "dsl_version":  u.dsl_version,
        "entities":     [_entity(e) for e in u.entities],
        "topo_order":   u.topo_order,
        "flows":        [_flow(f) for f in u.flows],
        "roles":        [_role(r) for r in u.roles],
        "auth":         _auth(u.auth),
        "security":     _security(u.security),
        "monetization": _monetization(u.monetization),
        "plugins":      u.plugins,
    }


def diagnostic(d: Diagnostic) -> dict:
    out: dict = {"level": d.level.value, "code": d.code, "message": d.message}
    if d.path:
        out["path"] = d.path
    if d.hint:
        out["hint"] = d.hint
    return out


def phase(p: PhaseResult) -> dict:
    return {"name": p.name, "duration_ms": round(p.duration_ms, 2), "note": p.note}


def compilation_result(r: CompilationResult) -> dict:
    return {
        "success":  not r.errors,
        "universe": universe(r.universe) if r.universe else None,
        "phases":   [phase(p) for p in r.phases],
        "written":  r.written,
        "skipped":  r.skipped,
        "errors":   [diagnostic(d) for d in r.errors],
        "warnings": [diagnostic(d) for d in r.warnings],
        "infos":    [diagnostic(d) for d in r.infos],
        "total_ms": round(r.total_ms, 2),
        "diff":     ({"summary": r.diff.summary(), "is_empty": r.diff.is_empty}
                     if r.diff else None),
    }
