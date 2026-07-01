import yaml
from pathlib import Path

VALID_FIELD_TYPES = {"string", "integer", "float", "boolean", "text", "datetime"}
VALID_AUTH_PROVIDERS = {"jwt"}
VALID_ROLE_PERMISSIONS = {"*", "read", "create", "update", "delete"}


def parse(genesis_file: str) -> dict:
    path = Path(genesis_file)
    if not path.exists():
        raise FileNotFoundError(f"Genesis file not found: {genesis_file}")

    with open(path, "r", encoding="utf-8") as f:
        spec = yaml.safe_load(f)

    if not spec or "universe" not in spec:
        raise ValueError("Invalid genesis file: missing top-level 'universe' key")

    universe = spec["universe"]
    _validate(universe)
    _normalize(universe)
    return universe


def _validate(universe: dict) -> None:
    if "name" not in universe:
        raise ValueError("Universe must have a 'name'")
    if "type" not in universe:
        raise ValueError("Universe must have a 'type'")

    for entity in universe.get("entities", []):
        if "name" not in entity:
            raise ValueError("Each entity must have a 'name'")
        for field in entity.get("fields", []):
            if "name" not in field:
                raise ValueError(f"Field in entity '{entity['name']}' is missing 'name'")
            ftype = field.get("type")
            if ftype not in VALID_FIELD_TYPES:
                raise ValueError(
                    f"Invalid field type '{ftype}' for '{entity['name']}.{field['name']}'. "
                    f"Valid types: {', '.join(sorted(VALID_FIELD_TYPES))}"
                )

    for flow in universe.get("flows", []):
        if "name" not in flow:
            raise ValueError("Each flow must have a 'name'")
        if not flow.get("steps"):
            raise ValueError(f"Flow '{flow['name']}' must have at least one step")

    auth = universe.get("auth", {})
    if auth.get("enabled"):
        provider = auth.get("provider", "jwt")
        if provider not in VALID_AUTH_PROVIDERS:
            raise ValueError(
                f"Invalid auth provider '{provider}'. "
                f"Valid providers: {', '.join(sorted(VALID_AUTH_PROVIDERS))}"
            )
        for field in auth.get("user_fields", []):
            if "name" not in field:
                raise ValueError("Each auth.user_fields entry must have a 'name'")
            ftype = field.get("type", "string")
            if ftype not in VALID_FIELD_TYPES:
                raise ValueError(
                    f"Invalid type '{ftype}' for auth user field '{field['name']}'"
                )

    for role in universe.get("roles", []):
        if "name" not in role:
            raise ValueError("Each role must have a 'name'")


def _normalize(universe: dict) -> None:
    universe.setdefault("entities", [])
    universe.setdefault("flows", [])
    universe.setdefault("roles", [])
    universe.setdefault("plugins", [])

    for entity in universe["entities"]:
        entity.setdefault("fields", [])
        for field in entity["fields"]:
            field.setdefault("required", True)
            field.setdefault("computed", False)

    for flow in universe["flows"]:
        flow.setdefault("trigger", "manual")
        for step in flow.get("steps", []):
            step.setdefault("action", "noop")

    auth = universe.get("auth", {})
    if auth:
        auth.setdefault("enabled", False)
        auth.setdefault("provider", "jwt")
        auth.setdefault("user_fields", [])
        for field in auth["user_fields"]:
            field.setdefault("type", "string")
            field.setdefault("required", False)
        universe["auth"] = auth

    for role in universe["roles"]:
        role.setdefault("permissions", ["read", "create"])

    security = universe.get("security", {})
    security.setdefault("ed25519", False)
    security.setdefault("ledger", False)
    universe["security"] = security
