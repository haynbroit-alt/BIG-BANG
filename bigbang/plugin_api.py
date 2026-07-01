"""
BangPlugin — formal base class for all BIG BANG plugins.

A plugin is the unit of capability in the compiler pipeline. It knows:
  - when it is relevant (is_active)
  - what files it produces (get_files)
  - what pip packages the generated code depends on (pip_requirements)

The engine has no knowledge of Stripe, Ed25519, Auth, etc.
It only runs plugins.

Plugins are pure IR transformations — they add nodes and edges to the
UniverseGraph during the Transform phase. They have no knowledge of
output formats (FastAPI, React, Docker). Emitters own that layer.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import TYPE_CHECKING

from bigbang.universe import Universe

if TYPE_CHECKING:
    from bigbang.ir import UniverseGraph


class BangPlugin(ABC):
    NAME: str = ""
    DESCRIPTION: str = ""
    REQUIRES: list[str] = []  # names of other plugins that must run before this one

    @classmethod
    def is_active(cls, universe: Universe) -> bool:
        """Return True if this plugin should run for the given universe."""
        return True

    @classmethod
    @abstractmethod
    def get_files(cls, universe: Universe, output: Path) -> list[tuple[str, Path]]:
        """
        Return a list of (template_name, destination_path) pairs.
        The generator will render each template and write it to destination.
        """

    @classmethod
    def pip_requirements(cls, universe: Universe) -> list[str]:
        """
        Python packages that the generated code requires.
        These are injected into the generated requirements.txt.
        """
        return []

    @classmethod
    def transform(cls, graph: "UniverseGraph") -> None:
        """
        Enrich the IR graph — the primary method of every plugin.

        Add nodes and edges that represent what this plugin contributes
        to the universe. The graph is mutated in place.

        Rules:
          - Only add nodes/edges, never remove or modify existing ones.
          - Never reference output files, templates, or backend frameworks.
          - This method is the only code that runs during the Transform phase.
        """

    @classmethod
    def post_generate(cls, universe: Universe, output: Path) -> None:
        """Called after all files are written. For post-processing hooks."""
