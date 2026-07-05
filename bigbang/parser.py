"""
Genesis parser — YAML → Universe IR.

This is the front-end of the BIG BANG compiler.
"""
import yaml
from pathlib import Path

from bigbang.universe import (
    AuthConfig, Entity, Flow, FlowStep, Monetization,
    Plan, Role, Security, Universe, UniverseField,
)

VALID_FIELD_TYPES = {"string", "integer", "float", "boolean", "text", "datetime"}
VALID_AUTH_PROVIDERS = {"jwt"}


def parse(genesis_file: str) -> Universe:
    path = Path(genesis_file)
    if not path.exists():
        raise FileNotFoundError(f"Genesis file not found: {genesis_file}")

    with open(path, "r", encoding="utf-8") as f:
        try:
            spec = yaml.safe_load(f)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML in {genesis_file}: {exc}") from exc

    if not isinstance(spec, dict) or "universe" not in spec:
        got = "an empty file" if spec is None else f"a {type(spec).__name__}"
        raise ValueError(
            f"Invalid genesis file: expected a top-level 'universe' key, got {got}"
        )

    raw = spec["universe"]
    if not isinstance(raw, dict):
        raise ValueError(f"'universe' must be a mapping, got a {type(raw).__name__}")
    _validate_raw(raw)
    return _build(raw)


# ── Validation ─────────────────────────────────────────────────────────────

def _validate_raw(raw: dict) -> None:
    if "name" not in raw:
        raise ValueError("Universe must have a 'name'")
    if "type" not in raw:
        raise ValueError("Universe must have a 'type'")

    seen_entity_names: set[str] = set()
    for entity in raw.get("entities", []):
        if "name" not in entity:
            raise ValueError("Each entity must have a 'name'")
        if entity["name"] in seen_entity_names:
            raise ValueError(
                f"Duplicate entity name: '{entity['name']}' — entity names must be unique"
            )
        seen_entity_names.add(entity["name"])
        for field in entity.get("fields", []):
            if "name" not in field:
                raise ValueError(f"Field in entity '{entity['name']}' is missing 'name'")
            ftype = field.get("type", "string")
            if ftype not in VALID_FIELD_TYPES:
                raise ValueError(
                    f"Invalid field type '{ftype}' for "
                    f"'{entity['name']}.{field['name']}'. "
                    f"Valid: {', '.join(sorted(VALID_FIELD_TYPES))}"
                )

    for flow in raw.get("flows", []):
        if "name" not in flow:
            raise ValueError("Each flow must have a 'name'")
        if not flow.get("steps"):
            raise ValueError(f"Flow '{flow['name']}' must have at least one step")

    for role in raw.get("roles", []):
        if "name" not in role:
            raise ValueError("Each role must have a 'name'")

    monetization = raw.get("monetization")
    if monetization:
        for plan in monetization.get("plans", []):
            if "name" not in plan:
                raise ValueError("Each monetization plan must have a 'name'")
            if "price" not in plan:
                raise ValueError(f"Monetization plan '{plan['name']}' is missing 'price'")

    auth = raw.get("auth", {})
    if auth.get("enabled"):
        provider = auth.get("provider", "jwt")
        if provider not in VALID_AUTH_PROVIDERS:
            raise ValueError(
                f"Unknown auth provider '{provider}'. "
                f"Valid: {', '.join(sorted(VALID_AUTH_PROVIDERS))}"
            )
    for field in auth.get("user_fields", []):
        if "name" not in field:
            raise ValueError("Each auth.user_fields entry must have a 'name'")
        ftype = field.get("type", "string")
        if ftype not in VALID_FIELD_TYPES:
            raise ValueError(
                f"Invalid field type '{ftype}' for auth.user_fields.'{field['name']}'. "
                f"Valid: {', '.join(sorted(VALID_FIELD_TYPES))}"
            )


# ── Builder: raw dict → Universe IR ────────────────────────────────────

def _build(raw: dict) -> Universe:
    return Universe(
        name=raw["name"],
        type=raw["type"],
        entities=[_build_entity(e) for e in raw.get("entities", [])],
        flows=[_build_flow(f) for f in raw.get("flows", [])],
        roles=[_build_role(r) for r in raw.get("roles", [])],
        monetization=_build_monetization(raw.get("monetization")),
        auth=_build_auth(raw.get("auth", {})),
        security=_build_security(raw.get("security", {})),
        plugins=raw.get("plugins", []),
    )


def _build_entity(raw: dict) -> Entity:
    return Entity(
        name=raw["name"],
        fields=[_build_field(f) for f in raw.get("fields", [])],
    )


def _build_field(raw: dict) -> UniverseField:
    return UniverseField(
        name=raw["name"],
        type=raw.get("type", "string"),
        required=raw.get("required", True),
        computed=raw.get("computed", False),
    )


def _build_flow(raw: dict) -> Flow:
    return Flow(
        name=raw["name"],
        trigger=raw.get("trigger", "manual"),
        steps=[FlowStep(action=s.get("action", "noop")) for s in raw.get("steps", [])],
    )


def _build_monetization(raw: dict | None) -> Monetization | None:
    if not raw:
        return None
    return Monetization(
        model=raw.get("model", "subscription"),
        plans=[
            Plan(name=p["name"], price=p["price"], currency=p.get("currency", "USD"))
            for p in raw.get("plans", [])
        ],
    )


def _build_auth(raw: dict) -> AuthConfig:
    return AuthConfig(
        enabled=bool(raw.get("enabled", False)),
        provider=raw.get("provider", "jwt"),
        user_fields=[_build_field(f) for f in raw.get("user_fields", [])],
    )


def _build_role(raw: dict) -> Role:
    return Role(
        name=raw["name"],
        permissions=raw.get("permissions", ["read", "create"]),
    )


def _build_security(raw: dict) -> Security:
    return Security(
        ed25519=bool(raw.get("ed25519", False)),
        ledger=bool(raw.get("ledger", False)),
    )
