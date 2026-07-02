"""Block-level merger tests — smart regeneration guarantees."""
from bigbang import merger


def _block(name: str, body: str) -> str:
    return f"# @bigbang:start:{name}\n{body}\n# @bigbang:end:{name}"


def test_has_blocks():
    assert merger.has_blocks(_block("model_site", "class Site: ..."))
    assert not merger.has_blocks("plain content, no markers")


def test_extract_blocks():
    content = _block("a", "one") + "\n\n" + _block("b", "two")
    blocks = merger.extract_blocks(content)
    assert set(blocks) == {"a", "b"}
    assert "one" in blocks["a"]


def test_merge_replaces_block_content():
    existing = _block("model", "old code")
    generated = _block("model", "new code")
    merged, updated, appended = merger.merge(existing, generated)
    assert "new code" in merged
    assert "old code" not in merged
    assert updated == ["model"]
    assert appended == []


def test_merge_preserves_user_code_outside_blocks():
    existing = "# my custom import\n" + _block("model", "old") + "\n\ndef my_helper(): ...\n"
    generated = _block("model", "new")
    merged, _, _ = merger.merge(existing, generated)
    assert "# my custom import" in merged
    assert "def my_helper(): ..." in merged
    assert "new" in merged


def test_merge_appends_new_blocks():
    existing = _block("site", "site code")
    generated = _block("site", "site code") + "\n\n" + _block("report", "report code")
    merged, updated, appended = merger.merge(existing, generated)
    assert appended == ["report"]
    assert "report code" in merged


def test_merge_annotates_removed_blocks():
    existing = _block("site", "site code") + "\n\n" + _block("legacy", "legacy code")
    generated = _block("site", "site code")
    merged, updated, appended = merger.merge(existing, generated)
    assert "legacy code" in merged
    assert "removed from genesis" in merged
    assert "legacy" not in updated


def test_merge_into_empty_file_returns_generated():
    generated = _block("model", "code")
    merged, updated, appended = merger.merge("", generated)
    assert merged == generated
    assert updated == [] and appended == []
