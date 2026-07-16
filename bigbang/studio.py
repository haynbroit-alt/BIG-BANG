"""
BIG BANG Studio — natural language → genesis.yaml via Claude.

Public API
----------
generate(description, *, model, stream_to) -> str
    Generate a genesis.yaml from a plain-English description.
"""
import os
import re
from typing import IO, Optional

_SYSTEM_PROMPT = """\
You are BIG BANG Studio, an expert at writing genesis.yaml files for the BIG BANG "Universe as Code" compiler.

BIG BANG compiles a genesis.yaml into a complete production application (REST API, database migrations, auth, Docker setup, etc.).

## Full DSL reference

bigbang: "1.0"         # optional, defaults to 1.0

universe:
  name: MyApp           # PascalCase, no spaces (required)
  type: api             # "api" | "saas" | "mobile" (required)

  entities:             # data models → database tables + REST endpoints
    - name: Entity      # PascalCase
      fields:
        - name: field   # snake_case
          type: string  # string | integer | float | boolean | text | datetime | uuid | email | url | json
          required: true
          computed: false  # computed fields are read-only, derived server-side

  flows:                # automated business logic
    - name: flow_name   # snake_case
      trigger: "human-readable event description"
      steps:
        - action: "human-readable step description"

  roles:
    - name: admin
      permissions: ["read", "write", "delete"]

  auth:
    enabled: true
    provider: jwt        # jwt | oauth2 | api_key
    user_fields:
      - name: role
        type: string
        required: true

  security:
    ed25519: true        # Ed25519 cryptographic proofs on every write
    ledger: true         # immutable audit trail

  monetization:          # omit key or set to ~ (null) if no billing
    model: subscription  # subscription | per_seat | usage
    plans:
      - name: starter
        price: 29
        currency: USD

  plugins: []            # reserved for future extensions

## Rules
1. Output ONLY valid YAML — no markdown fences, no explanation, no preamble
2. Entity names → PascalCase (User, BlogPost, LineItem)
3. Field names → snake_case (first_name, created_at)
4. Foreign keys → {entity}_id with type: integer (e.g. user_id references User)
5. Always include at least one entity with meaningful production-ready fields
6. `monetization` must be a proper object or ~ (null) — never an empty mapping {}
7. Add auth when the app has user accounts
8. Add security when the app handles financial, medical, or compliance-sensitive data
9. Be thorough: add all the entities, flows, roles, and fields a real production app would need
10. Prefer type: saas for B2B SaaS products, type: api for pure REST backends, type: mobile for mobile backends
"""


def _require_anthropic():
    """Import and return the anthropic module, raising ImportError with a helpful message."""
    try:
        import anthropic
        return anthropic
    except ImportError as exc:
        raise ImportError(
            "The `anthropic` package is required for Studio. "
            "Install it with: pip install 'big-bang[studio]'"
        ) from exc


def _require_api_key() -> str:
    """Return the Anthropic API key from the environment, raising ValueError if absent."""
    key = os.environ.get("ANTHROPIC_API_KEY", "").strip()
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY environment variable is not set. "
            "Get your key at https://console.anthropic.com/."
        )
    return key


def generate(
    description: str,
    *,
    model: str = "claude-opus-4-8",
    stream_to: Optional[IO] = None,
) -> str:
    """Generate a genesis.yaml from a natural-language description.

    Args:
        description: Plain-English description of the application to build.
        model: Claude model to use (default: claude-opus-4-8).
        stream_to: Optional file-like object; raw YAML tokens are written as
                   they stream so callers can provide live feedback.

    Returns:
        A ready-to-use genesis.yaml string (newline-terminated).

    Raises:
        ImportError: anthropic package is not installed.
        ValueError: ANTHROPIC_API_KEY environment variable is not set.
        anthropic.APIError: API-level error from the Claude API.
    """
    _anthropic = _require_anthropic()
    api_key = _require_api_key()

    client = _anthropic.Anthropic(api_key=api_key)

    with client.messages.stream(
        model=model,
        max_tokens=8192,
        thinking={"type": "adaptive"},
        system=_SYSTEM_PROMPT,
        messages=[{"role": "user", "content": description}],
    ) as stream:
        chunks: list[str] = []
        for text in stream.text_stream:
            chunks.append(text)
            if stream_to is not None:
                stream_to.write(text)
                if hasattr(stream_to, "flush"):
                    stream_to.flush()

    return _clean_yaml("".join(chunks))


def _clean_yaml(text: str) -> str:
    """Strip markdown code fences if the model accidentally wraps the output."""
    text = text.strip()
    text = re.sub(r"^```(?:yaml)?\s*\n", "", text)
    text = re.sub(r"\n```\s*$", "", text)
    return text.strip() + "\n"
