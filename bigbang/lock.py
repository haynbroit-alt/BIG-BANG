"""
Lock file (.bigbang.lock) — tracks hashes of generated files so that
regeneration can skip files the user has modified since last generation.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

LOCK_FILENAME = ".bigbang.lock"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load(output: Path) -> dict:
    lock_path = output / LOCK_FILENAME
    if not lock_path.exists():
        return {}
    try:
        return json.loads(lock_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def save(output: Path, universe_name: str, file_paths: list[Path]) -> None:
    lock_path = output / LOCK_FILENAME
    data = {
        "universe": universe_name,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "files": {
            str(p.relative_to(output)): _sha256(p)
            for p in file_paths
            if p.exists()
        },
    }
    lock_path.write_text(json.dumps(data, indent=2), encoding="utf-8")


def is_user_modified(output: Path, rel_path: str, lock_data: dict) -> bool:
    """Return True if the file exists and its hash differs from the lock record."""
    files = lock_data.get("files", {})
    if rel_path not in files:
        return False  # not tracked → safe to write
    current_path = output / rel_path
    if not current_path.exists():
        return False
    return _sha256(current_path) != files[rel_path]
