"""
BIG BANG Snapshot — Universe IR persistence for incremental compilation.

Serialises the Universe to JSON after each successful compilation and
deserialises it on the next run so the differ can compute what changed.
"""
import json
from pathlib import Path
from typing import Optional

from bigbang.universe import (
    AuthConfig, Entity, Flow, FlowStep, Monetization,
    Plan, Role, Security, Universe, UniverseField,
)

_SNAPSHOT_FILE = ".bigbang.snapshot.json"


# ── Public API ────────────────────────────────────────────────────────────────

def save(output: Path, universe: Universe) -> None:
    """Persist the compiled Universe IR to <output>/.bigbang.snapshot.json."""
    path = output / _SNAPSHOT_FILE
    path.write_text(json.dumps(_ser(universe), indent=2, ensure_ascii=False), encoding="utf-8")


def load(output: Path) -> Optional[Universe]:
    """Return the previous Universe IR, or None if no snapshot exists."""
    path = output / _SNAPSHOT_FILE
    if not path.exists():
        return None
    try:
        return _deser(json.loads(path.read_text(encoding="utf-8")))
    except Exception:
        return None


# ── Serialisation ─────────────────────────────────────────────────────────────

def _ser(u: Universe) -> dict:
    return {
        "name": u.name,
        "type": u.type,
        "entities": [_ser_entity(e) for e in u.entities],
        "flows": [
            {"name": f.name, "trigger": f.trigger,
             "steps": [{"action": s.action} for s in f.steps]}
            for f in u.flows
        ],
        "roles": [{"name": r.name, "permissions": r.permissions} for r in u.roles],
        "auth": {
            "enabled": u.auth.enabled,
            "provider": u.auth.provider,
            "user_fields": [_ser_field(f) for f in u.auth.user_fields],
        },
        "security": {"ed25519": u.security.ed25519, "ledger": u.security.ledger},
        "monetization": (
            {
                "model": u.monetization.model,
                "plans": [
                    {"name": p.name, "price": p.price, "currency": p.currency}
                    for p in u.monetization.plans
                ],
            }
            if u.monetization else None
        ),
        "plugins": u.plugins,
    }


def _ser_entity(e: Entity) -> dict:
    return {"name": e.name, "fields": [_ser_field(f) for f in e.fields]}


def _ser_field(f: UniverseField) -> dict:
    return {"name": f.name, "type": f.type, "required": f.required, "computed": f.computed}


# ── Deserialisation ───────────────────────────────────────────────────────────

def _deser(d: dict) -> Universe:
    mon_raw = d.get("monetization")
    auth_raw = d.get("auth", {})
    sec_raw = d.get("security", {})
    return Universe(
        name=d["name"],
        type=d["type"],
        entities=[
            Entity(
                name=e["name"],
                fields=[
                    UniverseField(
                        name=f["name"], type=f["type"],
                        required=f.get("required", True),
                        computed=f.get("computed", False),
                    )
                    for f in e.get("fields", [])
                ],
            )
            for e in d.get("entities", [])
        ],
        flows=[
            Flow(
                name=f["name"],
                trigger=f.get("trigger", ""),
                steps=[FlowStep(action=s["action"]) for s in f.get("steps", [])],
            )
            for f in d.get("flows", [])
        ],
        roles=[
            Role(name=r["name"], permissions=r.get("permissions", []))
            for r in d.get("roles", [])
        ],
        auth=AuthConfig(
            enabled=auth_raw.get("enabled", False),
            provider=auth_raw.get("provider", "jwt"),
            user_fields=[
                UniverseField(name=f["name"], type=f["type"],
                              required=f.get("required", True))
                for f in auth_raw.get("user_fields", [])
            ],
        ),
        security=Security(
            ed25519=sec_raw.get("ed25519", False),
            ledger=sec_raw.get("ledger", False),
        ),
        monetization=(
            Monetization(
                model=mon_raw["model"],
                plans=[
                    Plan(name=p["name"], price=p["price"], currency=p["currency"])
                    for p in mon_raw.get("plans", [])
                ],
            )
            if mon_raw else None
        ),
        plugins=d.get("plugins", []),
    )
