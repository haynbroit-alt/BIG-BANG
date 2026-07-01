"""Shared fixtures for BIG BANG test suite."""
import textwrap
from pathlib import Path

import pytest

from bigbang.diagnostics import DiagnosticEngine
from bigbang.universe import (
    AuthConfig, Entity, Flow, FlowStep, Monetization,
    Plan, Relation, Role, Security, Universe, UniverseField,
)


# ── Universe builders ─────────────────────────────────────────────────────────

def make_field(name: str, type_: str = "string", required: bool = True, computed: bool = False):
    return UniverseField(name=name, type=type_, required=required, computed=computed)


def make_entity(name: str, fields: list | None = None, relations: list | None = None):
    return Entity(
        name=name,
        fields=fields or [],
        relations=relations or [],
    )


def minimal_universe() -> Universe:
    return Universe(
        name="TestApp",
        type="api",
        entities=[
            make_entity("Todo", fields=[make_field("title"), make_field("done", "boolean")]),
            make_entity("Tag",  fields=[make_field("name")]),
        ],
    )


def crm_universe() -> Universe:
    """Three-entity CRM with inferred relations (not yet resolved)."""
    contact = make_entity("Contact", fields=[
        make_field("first_name"),
        make_field("email"),
    ])
    deal = make_entity("Deal", fields=[
        make_field("title"),
        make_field("contact_id", "integer"),
    ])
    activity = make_entity("Activity", fields=[
        make_field("subject"),
        make_field("deal_id", "integer"),
        make_field("contact_id", "integer"),
    ])
    return Universe(
        name="SwiftCRM",
        type="saas",
        entities=[contact, deal, activity],
        flows=[
            Flow(name="qualify_lead", trigger="on_create",
                 steps=[FlowStep(action="notify_team")]),
        ],
        roles=[
            Role(name="admin", permissions=["read", "write", "delete"]),
            Role(name="viewer", permissions=["read"]),
        ],
        auth=AuthConfig(enabled=True, provider="jwt",
                        user_fields=[make_field("email"), make_field("role")]),
        security=Security(ed25519=True, ledger=True),
        monetization=Monetization(model="subscription", plans=[
            Plan(name="starter", price=29, currency="USD"),
            Plan(name="pro",     price=99, currency="USD"),
        ]),
    )


# ── Pytest fixtures ───────────────────────────────────────────────────────────

@pytest.fixture
def diags():
    return DiagnosticEngine()


@pytest.fixture
def todo_universe():
    return minimal_universe()


@pytest.fixture
def crm():
    return crm_universe()


@pytest.fixture
def examples_dir():
    return Path(__file__).parent.parent / "examples"


@pytest.fixture
def tmp_output(tmp_path):
    """A fresh temp directory for pipeline output."""
    return tmp_path / "output"
