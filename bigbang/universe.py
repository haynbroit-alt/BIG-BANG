"""
Universe IR — typed intermediate representation of a parsed genesis.yaml.

This is the AST that flows through the compiler pipeline:
    genesis.yaml → Parser → Universe → Resolver → Plugin Engine → Emitter → Output
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class UniverseField:
    name: str
    type: str
    required: bool = True
    computed: bool = False


@dataclass
class Relation:
    """A resolved foreign-key relation inferred by the semantic resolver."""
    field_name: str   # e.g. "contact_id"
    target: str       # e.g. "Contact"  (target entity name)
    kind: str = "many_to_one"


@dataclass
class Entity:
    name: str
    fields: list[UniverseField] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)  # populated by resolver

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "_").replace("-", "_")

    @property
    def writable_fields(self) -> list[UniverseField]:
        return [f for f in self.fields if not f.computed]

    @property
    def computed_fields(self) -> list[UniverseField]:
        return [f for f in self.fields if f.computed]


@dataclass
class FlowStep:
    action: str


@dataclass
class Flow:
    name: str
    trigger: str
    steps: list[FlowStep] = field(default_factory=list)

    @property
    def slug(self) -> str:
        return self.name.lower().replace(" ", "_").replace("-", "_")


@dataclass
class Plan:
    name: str
    price: int | float
    currency: str


@dataclass
class Monetization:
    model: str
    plans: list[Plan] = field(default_factory=list)


@dataclass
class AuthConfig:
    enabled: bool = False
    provider: str = "jwt"
    user_fields: list[UniverseField] = field(default_factory=list)


@dataclass
class Role:
    name: str
    permissions: list[str] = field(default_factory=list)


@dataclass
class Security:
    ed25519: bool = False
    ledger: bool = False


@dataclass
class Universe:
    name: str
    type: str
    entities: list[Entity] = field(default_factory=list)
    flows: list[Flow] = field(default_factory=list)
    roles: list[Role] = field(default_factory=list)
    monetization: Optional[Monetization] = None
    auth: AuthConfig = field(default_factory=AuthConfig)
    security: Security = field(default_factory=Security)
    plugins: list[str] = field(default_factory=list)
    topo_order: list[str] = field(default_factory=list)  # entity names, dependencies first

    @property
    def name_slug(self) -> str:
        return self.name.lower().replace(" ", "_").replace("-", "_")

    @property
    def entity_map(self) -> dict[str, Entity]:
        return {e.name: e for e in self.entities}

    def ordered_entities(self) -> list[Entity]:
        """Return entities in topological order (dependencies first)."""
        if not self.topo_order:
            return self.entities
        m = self.entity_map
        return [m[n] for n in self.topo_order if n in m]
