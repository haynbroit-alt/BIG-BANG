"""
Universe IR — typed intermediate representation of a parsed genesis.yaml.

This is the AST that flows through the compiler pipeline:
    genesis.yaml → Parser → Universe → Plugin Pipeline → Generator → Output
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
class Entity:
    name: str
    fields: list[UniverseField] = field(default_factory=list)

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

    @property
    def name_slug(self) -> str:
        return self.name.lower().replace(" ", "_").replace("-", "_")
