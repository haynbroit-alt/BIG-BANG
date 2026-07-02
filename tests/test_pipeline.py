"""End-to-end pipeline tests — every example compiles, output is deterministic,
user edits survive regeneration."""
import filecmp
from pathlib import Path

import pytest

from bigbang import pipeline

# .bigbang.lock embeds a generated_at timestamp — the one known (tracked)
# exception to byte-for-byte determinism. See docs/STRATEGY.md, phase 1.
NON_DETERMINISTIC_FILES = {".bigbang.lock"}

EXAMPLES = sorted((Path(__file__).parent.parent / "examples").glob("*.yaml"))


def _all_files(root: Path) -> list[Path]:
    return sorted(p.relative_to(root) for p in root.rglob("*") if p.is_file())


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_example_compiles_without_errors(example, tmp_path):
    result = pipeline.compile(str(example), str(tmp_path))
    assert not result.errors, [d.message for d in result.errors]
    assert result.written
    assert result.output_path.exists()


@pytest.mark.parametrize("example", EXAMPLES, ids=lambda p: p.stem)
def test_compilation_is_deterministic(example, tmp_path):
    """Same DSL → same output, byte for byte (VISION.md, principle 2)."""
    out_a, out_b = tmp_path / "a", tmp_path / "b"
    ra = pipeline.compile(str(example), str(out_a))
    rb = pipeline.compile(str(example), str(out_b))

    files_a = [f for f in _all_files(ra.output_path) if f.name not in NON_DETERMINISTIC_FILES]
    files_b = [f for f in _all_files(rb.output_path) if f.name not in NON_DETERMINISTIC_FILES]
    assert files_a == files_b

    for rel in files_a:
        assert filecmp.cmp(ra.output_path / rel, rb.output_path / rel, shallow=False), (
            f"{rel} differs between two compilations of the same genesis"
        )


def test_recompilation_preserves_user_code_outside_blocks(tmp_path):
    example = str(EXAMPLES[0])
    result = pipeline.compile(example, str(tmp_path))

    # Simulate a user edit outside managed blocks in a block-managed file
    target = next(
        (result.output_path / rel for rel in result.written
         if "@bigbang:start:" in (result.output_path / rel).read_text(encoding="utf-8")),
        None,
    )
    assert target is not None, "expected at least one block-managed file"
    marker = "# USER CUSTOM CODE — must survive recompilation\n"
    target.write_text(marker + target.read_text(encoding="utf-8"), encoding="utf-8")

    pipeline.compile(example, str(tmp_path))
    assert marker in target.read_text(encoding="utf-8")


def test_dry_run_writes_nothing(tmp_path):
    result = pipeline.compile(str(EXAMPLES[0]), str(tmp_path), dry_run=True)
    assert result.written  # files are listed…
    assert not result.output_path.exists()  # …but nothing touches the disk


def test_parse_error_yields_diagnostic_not_crash(tmp_path):
    bad = tmp_path / "genesis.yaml"
    bad.write_text("universe:\n  type: api\n", encoding="utf-8")  # missing name
    result = pipeline.compile(str(bad), str(tmp_path / "out"))
    assert result.errors
    assert result.errors[0].code == "E000"
