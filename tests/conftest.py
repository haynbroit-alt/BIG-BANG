"""Shared fixtures for the BIG BANG test suite."""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).parent.parent


@pytest.fixture
def examples_dir() -> Path:
    return REPO_ROOT / "examples"


def write_genesis(tmp_path: Path, content: str) -> str:
    """Write a genesis.yaml into tmp_path and return its path as str."""
    path = tmp_path / "genesis.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)
