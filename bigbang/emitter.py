"""
BIG BANG Emitter — abstract base class for all output generators.

Emitters are the ONLY component that knows about output formats.
They read the final IR graph and produce (template, destination) pairs.
They have no knowledge of auth, billing, cryptography, or any other
domain concept — they only know what the graph tells them.

This separation guarantees:
  - Adding a NestJS backend requires only a new emitter, zero plugin changes.
  - Plugins remain format-agnostic; they can never break an emitter.
  - The IR graph is the stable contract between the two layers.
"""
from abc import ABC, abstractmethod
from pathlib import Path

from bigbang.ir import UniverseGraph


class BangEmitter(ABC):
    """
    Base class for all BIG BANG emitters.

    An emitter declares which (template_name, output_path) pairs it produces
    for a given graph. The pipeline handles rendering, block-merge, and
    file-lock strategies — the emitter only answers "what files and from where."
    """
    NAME: str = ""
    DESCRIPTION: str = ""

    @classmethod
    def should_emit(cls, graph: UniverseGraph) -> bool:
        """Return True if this emitter should run for the given graph."""
        return True

    @classmethod
    @abstractmethod
    def get_pairs(
        cls,
        graph: UniverseGraph,
        output: Path,
    ) -> list[tuple[str, Path]]:
        """
        Return (template_name, destination_path) pairs.

        template_name is relative to the templates directory.
        destination_path is an absolute path inside `output`.
        The pipeline renders each template with both `universe` and `graph`
        in context, applying block-merge or file-lock as appropriate.
        """

    @classmethod
    def pip_requirements(cls, graph: UniverseGraph) -> list[str]:
        """Python packages the emitted code requires at runtime."""
        return []

    @classmethod
    def post_emit(cls, graph: UniverseGraph, output: Path) -> None:
        """Called once after all pairs have been rendered. Optional hook."""
