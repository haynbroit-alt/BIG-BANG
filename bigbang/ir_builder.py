"""
BIG BANG IR Builder — converts the parsed Universe IR to an UniverseGraph.

This runs once, after Parse + Resolve, before the Plugin Transform phase.
It seeds the graph with the entities, relations, flows, roles, and universe
metadata declared in genesis.yaml. Plugins then enrich the graph further.
"""
from bigbang.ir import IREdge, IRNode, UniverseGraph
from bigbang.universe import Universe


def build_graph(universe: Universe) -> UniverseGraph:
    """
    Construct the initial UniverseGraph from a resolved Universe.
    The graph is returned in a raw state — plugin transforms haven't run yet.
    """
    g = UniverseGraph(
        name=universe.name,
        kind=universe.type,
        meta={
            "name_slug":   universe.name_slug,
            "auth": {
                "enabled":    universe.auth.enabled,
                "provider":   universe.auth.provider,
                "user_fields": [
                    {"name": f.name, "type": f.type, "required": f.required}
                    for f in universe.auth.user_fields
                ],
            },
            "security": {
                "ed25519": universe.security.ed25519,
                "ledger":  universe.security.ledger,
            },
            "monetization": (
                {
                    "model": universe.monetization.model,
                    "plans": [
                        {"name": p.name, "price": p.price, "currency": p.currency}
                        for p in universe.monetization.plans
                    ],
                }
                if universe.monetization else None
            ),
            "plugins": list(universe.plugins),
            "topo_order": list(universe.topo_order),
        },
    )

    # ── Entity nodes (topological order — dependencies first) ─────────────────
    for entity in universe.ordered_entities():
        g.add_node(IRNode(
            id=f"entity:{entity.slug}",
            kind="entity",
            data={
                "name":      entity.name,
                "slug":      entity.slug,
                "fields":    [
                    {
                        "name":     f.name,
                        "type":     f.type,
                        "required": f.required,
                        "computed": f.computed,
                    }
                    for f in entity.fields
                ],
            },
        ))

    # ── Relation edges ─────────────────────────────────────────────────────────
    for entity in universe.entities:
        for rel in entity.relations:
            target_slug = rel.target.lower().replace(" ", "_").replace("-", "_")
            g.add_edge(IREdge(
                source=f"entity:{entity.slug}",
                target=f"entity:{target_slug}",
                kind="relation",
                attrs={"field": rel.field_name, "cardinality": rel.kind},
            ))

    # ── Flow nodes ────────────────────────────────────────────────────────────
    for flow in universe.flows:
        g.add_node(IRNode(
            id=f"flow:{flow.slug}",
            kind="flow",
            data={
                "name":    flow.name,
                "slug":    flow.slug,
                "trigger": flow.trigger,
                "steps":   [{"action": s.action} for s in flow.steps],
            },
        ))

    # ── Role nodes + permission edges ─────────────────────────────────────────
    for role in universe.roles:
        g.add_node(IRNode(
            id=f"role:{role.name}",
            kind="role",
            data={"name": role.name, "permissions": role.permissions},
        ))
        for perm in role.permissions:
            for entity in universe.entities:
                g.add_edge(IREdge(
                    source=f"role:{role.name}",
                    target=f"entity:{entity.slug}",
                    kind="permission",
                    attrs={"action": perm},
                ))

    # ── Monetization node ─────────────────────────────────────────────────────
    if universe.monetization:
        g.add_node(IRNode(
            id="billing:subscription",
            kind="subscription",
            data={
                "model": universe.monetization.model,
                "plans": [
                    {"name": p.name, "price": p.price, "currency": p.currency}
                    for p in universe.monetization.plans
                ],
            },
        ))

    return g
