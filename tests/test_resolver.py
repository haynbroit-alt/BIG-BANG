"""Semantic resolver tests — relation inference, topo sort, cycle detection."""
from bigbang.diagnostics import DiagnosticEngine
from bigbang.resolver import resolve
from bigbang.universe import Entity, Universe, UniverseField


def _universe(entities: list[Entity]) -> Universe:
    return Universe(name="T", type="api", entities=entities)


def _entity(name: str, *field_names: str) -> Entity:
    return Entity(name=name, fields=[UniverseField(name=f, type="integer") for f in field_names])


def test_infers_many_to_one_relation():
    u = _universe([_entity("Site", "url"), _entity("Report", "site_id")])
    diags = DiagnosticEngine()
    resolve(u, diags)

    report = next(e for e in u.entities if e.name == "Report")
    assert len(report.relations) == 1
    rel = report.relations[0]
    assert rel.target == "Site"
    assert rel.field_name == "site_id"
    assert rel.kind == "many_to_one"


def test_topo_order_puts_dependency_first():
    u = _universe([_entity("Report", "site_id"), _entity("Site", "url")])
    resolve(u, DiagnosticEngine())
    assert u.topo_order.index("Site") < u.topo_order.index("Report")


def test_unmatched_foreign_key_warns():
    u = _universe([_entity("Report", "ghost_id")])
    diags = DiagnosticEngine()
    resolve(u, diags)

    warnings = [d for d in diags.all if d.level.value == "warning"]
    assert any(d.code == "W001" for d in warnings)
    assert not u.entities[0].relations


def test_cycle_is_detected():
    u = _universe([_entity("A", "b_id"), _entity("B", "a_id")])
    diags = DiagnosticEngine()
    resolve(u, diags)

    errors = [d for d in diags.all if d.level.value == "error"]
    assert any(d.code == "E010" for d in errors)
    # All entities still appear in topo_order so emission can proceed
    assert set(u.topo_order) == {"A", "B"}


def test_resolve_is_idempotent():
    u = _universe([_entity("Site", "url"), _entity("Report", "site_id")])
    resolve(u, DiagnosticEngine())
    resolve(u, DiagnosticEngine())

    report = next(e for e in u.entities if e.name == "Report")
    assert len(report.relations) == 1


def test_snake_case_target_matching():
    u = _universe([Entity(name="UserProfile", fields=[]), _entity("Post", "user_profile_id")])
    resolve(u, DiagnosticEngine())
    post = next(e for e in u.entities if e.name == "Post")
    assert post.relations and post.relations[0].target == "UserProfile"
