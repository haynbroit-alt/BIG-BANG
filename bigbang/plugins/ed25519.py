from pathlib import Path

from bigbang.plugin_api import BangPlugin
from bigbang.universe import Universe

NAME = "ed25519"
DESCRIPTION = "Cryptographic proof ledger: Ed25519 signatures, action timestamping, verification API"


class Ed25519Plugin(BangPlugin):
    NAME = NAME
    DESCRIPTION = DESCRIPTION

    @classmethod
    def is_active(cls, universe: Universe) -> bool:
        return universe.security.ed25519

    @classmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        b = output / "backend"
        return [
            ("backend/ledger.py.j2",        b / "ledger.py"),
            ("backend/ledger_routes.py.j2", b / "ledger_routes.py"),
        ]

    @classmethod
    def pip_requirements(cls, universe: Universe) -> list[str]:
        return ["cryptography>=42.0.0"]


is_active = Ed25519Plugin.is_active
get_files = Ed25519Plugin.get_files
pip_requirements = Ed25519Plugin.pip_requirements
