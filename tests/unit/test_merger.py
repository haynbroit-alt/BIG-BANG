"""Unit tests for bigbang.merger — block-level merge logic."""
import pytest

from bigbang.merger import extract_blocks, has_blocks, merge, MARKER_START, MARKER_END


# ── has_blocks ────────────────────────────────────────────────────────────────

class TestHasBlocks:
    def test_true_with_block(self):
        content = "# @bigbang:start:todo\nsome code\n# @bigbang:end:todo\n"
        assert has_blocks(content)

    def test_false_without_block(self):
        assert not has_blocks("just some python code\n")

    def test_false_on_empty_string(self):
        assert not has_blocks("")

    def test_false_with_only_start_marker(self):
        assert not has_blocks("# @bigbang:start:todo\nno end marker\n")


# ── extract_blocks ────────────────────────────────────────────────────────────

class TestExtractBlocks:
    def test_single_block(self):
        content = "# @bigbang:start:todo\nclass Todo:\n    pass\n# @bigbang:end:todo\n"
        blocks = extract_blocks(content)
        assert "todo" in blocks
        assert "class Todo:" in blocks["todo"]

    def test_multiple_blocks(self):
        content = (
            "# @bigbang:start:todo\ntodo code\n# @bigbang:end:todo\n"
            "middle code\n"
            "# @bigbang:start:tag\ntag code\n# @bigbang:end:tag\n"
        )
        blocks = extract_blocks(content)
        assert set(blocks.keys()) == {"todo", "tag"}

    def test_block_includes_markers(self):
        content = "# @bigbang:start:foo\nbody\n# @bigbang:end:foo\n"
        blocks = extract_blocks(content)
        assert "# @bigbang:start:foo" in blocks["foo"]
        assert "# @bigbang:end:foo" in blocks["foo"]

    def test_empty_content(self):
        assert extract_blocks("") == {}


# ── merge ─────────────────────────────────────────────────────────────────────

def _block(name: str, body: str) -> str:
    return f"# @bigbang:start:{name}\n{body}\n# @bigbang:end:{name}\n"


class TestMerge:
    def test_empty_existing_returns_generated(self):
        generated = _block("todo", "new code")
        merged, updated, appended = merge("", generated)
        assert merged == generated
        assert updated == []
        assert appended == []

    def test_whitespace_only_existing_returns_generated(self):
        generated = _block("todo", "new code")
        merged, _, _ = merge("   \n  ", generated)
        assert merged == generated

    def test_block_updated_in_place(self):
        existing = "header\n" + _block("todo", "old code") + "footer\n"
        generated = _block("todo", "new code")
        merged, updated, appended = merge(existing, generated)
        assert "new code" in merged
        assert "old code" not in merged
        assert "header" in merged
        assert "footer" in merged
        assert "todo" in updated

    def test_user_code_outside_block_preserved(self):
        existing = (
            "# user import\nimport custom\n\n"
            + _block("models", "class Todo: pass\n")
            + "\n# user custom code\ndef my_func(): pass\n"
        )
        generated = _block("models", "class Todo:\n    title: str\n")
        merged, _, _ = merge(existing, generated)
        assert "import custom" in merged
        assert "my_func" in merged
        assert "title: str" in merged

    def test_new_block_appended(self):
        existing = _block("todo", "todo code")
        generated = _block("todo", "todo code") + _block("tag", "tag code")
        merged, updated, appended = merge(existing, generated)
        assert "tag code" in merged
        assert "tag" in appended
        assert "todo" in updated

    def test_removed_block_kept_with_annotation(self):
        existing = _block("todo", "todo code") + _block("old_model", "legacy")
        generated = _block("todo", "updated todo")
        merged, updated, appended = merge(existing, generated)
        assert "removed from genesis" in merged
        assert "legacy" in merged
        assert "old_model" not in updated
        assert "old_model" not in appended

    def test_multiple_blocks_all_updated(self):
        existing = _block("contact", "old contact") + _block("deal", "old deal")
        generated = _block("contact", "new contact") + _block("deal", "new deal")
        merged, updated, appended = merge(existing, generated)
        assert "new contact" in merged
        assert "new deal" in merged
        assert set(updated) == {"contact", "deal"}
        assert appended == []

    def test_returns_three_tuple(self):
        result = merge("", _block("x", "body"))
        assert len(result) == 3
