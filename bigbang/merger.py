"""
Block-level merger — the key to smart regeneration.

Generated files contain fenced regions:
    # @bigbang:start:block_name
    ... generated content ...
    # @bigbang:end:block_name

On regeneration:
  - Content inside markers  → replaced with the new generated version
  - Content outside markers → preserved exactly (user's custom code)
  - New blocks (new entity added to genesis.yaml) → appended at end
  - Removed blocks (entity deleted from genesis.yaml) → kept as-is with a warning comment

Files without any @bigbang markers fall back to file-level lock strategy.
"""
import re

_BLOCK_RE = re.compile(
    r"# @bigbang:start:(\w+)\n(.*?)# @bigbang:end:\1",
    re.DOTALL,
)

MARKER_START = "# @bigbang:start:{name}"
MARKER_END   = "# @bigbang:end:{name}"


def has_blocks(content: str) -> bool:
    return bool(_BLOCK_RE.search(content))


def extract_blocks(content: str) -> dict[str, str]:
    """Return {block_name: full_block_text_including_markers}."""
    return {m.group(1): m.group(0) for m in _BLOCK_RE.finditer(content)}


def merge(existing: str, generated: str) -> tuple[str, list[str], list[str]]:
    """
    Merge freshly-generated content into an existing file.

    Returns
    -------
    merged   : str         Final file content
    updated  : list[str]  Block names that were refreshed
    appended : list[str]  Block names that were new and appended at the end
    """
    if not existing.strip():
        return generated, [], []

    gen_blocks = extract_blocks(generated)
    updated: list[str] = []

    def _replace(m: re.Match) -> str:
        name = m.group(1)
        if name in gen_blocks:
            updated.append(name)
            return gen_blocks[name]
        # Block no longer in genesis — keep old content but annotate it
        return (
            f"# @bigbang:start:{name} [removed from genesis — kept for reference]\n"
            + m.group(2)
            + f"# @bigbang:end:{name}"
        )

    merged = _BLOCK_RE.sub(_replace, existing)

    # Blocks in generated that didn't exist in existing → append
    appended = [n for n in gen_blocks if n not in updated]
    if appended:
        merged = merged.rstrip("\n") + "\n\n"
        for name in appended:
            merged += gen_blocks[name] + "\n\n"
        merged = merged.rstrip("\n") + "\n"

    return merged, updated, appended
