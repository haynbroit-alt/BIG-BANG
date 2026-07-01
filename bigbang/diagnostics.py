"""
BIG BANG Diagnostic Engine — structured error reporting for the compilation pipeline.

Diagnostics carry a code, a human-readable message, an optional source path
(e.g. "entities[Deal].fields[closed_at].type"), and an optional hint.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Level(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


_LABEL = {Level.INFO: "INFO", Level.WARNING: "WARN", Level.ERROR: "ERROR"}
_COLOUR = {Level.INFO: "\033[36m", Level.WARNING: "\033[33m", Level.ERROR: "\033[31m"}
_RESET = "\033[0m"


@dataclass(frozen=True)
class Diagnostic:
    level: Level
    code: str
    message: str
    path: Optional[str] = None
    hint: Optional[str] = None

    def __str__(self) -> str:
        label = _LABEL[self.level]
        loc = f"\n      at: {self.path}" if self.path else ""
        tip = f"\n    hint: {self.hint}" if self.hint else ""
        return f"  {label} [{self.code}] {self.message}{loc}{tip}"

    def coloured(self) -> str:
        c = _COLOUR[self.level]
        label = _LABEL[self.level]
        loc = f"\n      at: {self.path}" if self.path else ""
        tip = f"\n    hint: {self.hint}" if self.hint else ""
        return f"  {c}{label}{_RESET} [{self.code}] {self.message}{loc}{tip}"


class DiagnosticEngine:
    """Accumulates diagnostics across compilation phases."""

    def __init__(self) -> None:
        self._diags: list[Diagnostic] = []

    def info(self, code: str, message: str, path: str = None, hint: str = None) -> None:
        self._diags.append(Diagnostic(Level.INFO, code, message, path, hint))

    def warn(self, code: str, message: str, path: str = None, hint: str = None) -> None:
        self._diags.append(Diagnostic(Level.WARNING, code, message, path, hint))

    def error(self, code: str, message: str, path: str = None, hint: str = None) -> None:
        self._diags.append(Diagnostic(Level.ERROR, code, message, path, hint))

    @property
    def has_errors(self) -> bool:
        return any(d.level == Level.ERROR for d in self._diags)

    @property
    def errors(self) -> list[Diagnostic]:
        return [d for d in self._diags if d.level == Level.ERROR]

    @property
    def warnings(self) -> list[Diagnostic]:
        return [d for d in self._diags if d.level == Level.WARNING]

    @property
    def infos(self) -> list[Diagnostic]:
        return [d for d in self._diags if d.level == Level.INFO]

    @property
    def all(self) -> list[Diagnostic]:
        return list(self._diags)

    def raise_if_errors(self) -> None:
        if self.has_errors:
            lines = "\n".join(str(d) for d in self.errors)
            raise CompilationError(
                f"Compilation failed with {len(self.errors)} error(s):\n{lines}"
            )


class CompilationError(ValueError):
    """Raised when the pipeline cannot continue due to fatal diagnostics."""
