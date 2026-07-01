"""
BIG BANG Universe Differ — Phase 5 of the compilation pipeline.

Computes a structural diff between two Universe IR snapshots so the emitter
can skip unchanged files (incremental compilation).
"""
from dataclasses import dataclass, field
from typing import Literal, Optional

from bigbang.universe import Entity, Universe, UniverseField


@dataclass
class FieldDelta:
    name: str
    kind: Literal["added", "removed", "modified"]
    before: Optional[UniverseField] = None
    after: Optional[UniverseField] = None


@dataclass
class EntityDelta:
    name: str
    kind: Literal["added", "removed", "modified"]
    field_deltas: list[FieldDelta] = field(default_factory=list)


@dataclass
class UniverseDiff:
    entity_deltas: list[EntityDelta] = field(default_factory=list)
    flows_changed: bool = False
    auth_changed: bool = False
    security_changed: bool = False
    monetization_changed: bool = False
    plugins_changed: bool = False

    @property
    def is_empty(self) -> bool:
        return not any([
            self.entity_deltas,
            self.flows_changed,
            self.auth_changed,
            self.security_changed,
            self.monetization_changed,
            self.plugins_changed,
        ])

    @property
    def affected_templates(self) -> set[str]:
        """Relative output paths likely affected by this diff."""
        out: set[str] = set()
        if self.entity_deltas:
            out |= {"backend/models.py", "backend/schemas.py", "backend/routes.py"}
        if self.flows_changed:
            out.add("backend/routes.py")
        if self.auth_changed:
            out |= {"backend/auth_models.py", "backend/auth_routes.py", "backend/auth_schemas.py"}
        if self.security_changed:
            out |= {"backend/ledger.py", "backend/ledger_routes.py", "backend/app.py"}
        if self.monetization_changed:
            out |= {"backend/routes.py", "backend/app.py"}
        return out

    def summary(self) -> str:
        parts: list[str] = []
        added    = [d for d in self.entity_deltas if d.kind == "added"]
        removed  = [d for d in self.entity_deltas if d.kind == "removed"]
        modified = [d for d in self.entity_deltas if d.kind == "modified"]
        if added:
            parts.append(f"+{len(added)} entity({', '.join(d.name for d in added)})")
        if removed:
            parts.append(f"-{len(removed)} entity({', '.join(d.name for d in removed)})")
        if modified:
            field_count = sum(len(d.field_deltas) for d in modified)
            parts.append(f"~{len(modified)} entity, {field_count} field change(s)")
        if self.flows_changed:
            parts.append("flows")
        if self.auth_changed:
            parts.append("auth")
        if self.security_changed:
            parts.append("security")
        if self.monetization_changed:
            parts.append("monetization")
        return "; ".join(parts) if parts else "no changes"


def diff(old: Universe, new: Universe) -> UniverseDiff:
    """Return a structural diff between two Universe snapshots."""
    result = UniverseDiff()

    old_ents = {e.name: e for e in old.entities}
    new_ents = {e.name: e for e in new.entities}

    for name in new_ents:
        if name not in old_ents:
            result.entity_deltas.append(EntityDelta(name=name, kind="added"))

    for name in old_ents:
        if name not in new_ents:
            result.entity_deltas.append(EntityDelta(name=name, kind="removed"))

    for name in old_ents.keys() & new_ents.keys():
        delta = _diff_entity(old_ents[name], new_ents[name])
        if delta.field_deltas:
            result.entity_deltas.append(delta)

    result.flows_changed = (
        {f.name for f in old.flows} != {f.name for f in new.flows}
    )
    result.auth_changed = (
        old.auth.enabled != new.auth.enabled
        or old.auth.provider != new.auth.provider
    )
    result.security_changed = (
        old.security.ed25519 != new.security.ed25519
        or old.security.ledger != new.security.ledger
    )
    result.monetization_changed = bool(old.monetization) != bool(new.monetization)
    result.plugins_changed = set(old.plugins) != set(new.plugins)

    return result


def _diff_entity(old: Entity, new: Entity) -> EntityDelta:
    delta = EntityDelta(name=old.name, kind="modified")
    old_fields = {f.name: f for f in old.fields}
    new_fields = {f.name: f for f in new.fields}

    for name in new_fields:
        if name not in old_fields:
            delta.field_deltas.append(FieldDelta(name=name, kind="added", after=new_fields[name]))

    for name in old_fields:
        if name not in new_fields:
            delta.field_deltas.append(FieldDelta(name=name, kind="removed", before=old_fields[name]))

    for name in old_fields.keys() & new_fields.keys():
        of, nf = old_fields[name], new_fields[name]
        if of.type != nf.type or of.required != nf.required or of.computed != nf.computed:
            delta.field_deltas.append(
                FieldDelta(name=name, kind="modified", before=of, after=nf)
            )

    return delta
