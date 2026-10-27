"""Static outlines of source files. Files are read, never imported or executed."""

import ast
import re
from dataclasses import dataclass, field

from ai_alchemist.repository.file_filters import FileRead

_GENERIC_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("function", re.compile(r"^\s*(?:export\s+)?(?:async\s+)?function\s+([A-Za-z_$][\w$]*)", re.M)),
    ("function", re.compile(r"^\s*(?:pub\s+)?(?:async\s+)?fn\s+([A-Za-z_][\w]*)", re.M)),
    ("function", re.compile(r"^\s*func\s+(?:\([^)]*\)\s*)?([A-Za-z_][\w]*)", re.M)),
    ("class", re.compile(r"^\s*(?:export\s+)?class\s+([A-Za-z_][\w]*)", re.M)),
    ("type", re.compile(r"^\s*(?:pub\s+)?struct\s+([A-Za-z_][\w]*)", re.M)),
)


@dataclass(frozen=True)
class Symbol:
    """A definition found by parsing or, failing that, by a pattern."""

    kind: str
    name: str
    line: int
    approximate: bool = False


@dataclass
class CodeOutline:
    """A static description. `executed` is always false."""

    relative_path: str
    language: str
    imports: list[tuple[str, int]] = field(default_factory=list)
    symbols: list[Symbol] = field(default_factory=list)
    parse_note: str = ""
    executed: bool = False

    def render(self) -> str:
        """Plain-text outline for the terminal and for the model prompt."""
        lines = [
            f"File: {self.relative_path}",
            f"Language guess: {self.language}",
            "Analysis: static read only. This file was not executed or tested.",
        ]
        if self.parse_note:
            lines.append(self.parse_note)
        if self.imports:
            lines.append("Imports:")
            for name, line in self.imports:
                lines.append(f"  - {name} (line {line})")
        else:
            lines.append("Imports: none recorded by the static reader.")
        if self.symbols:
            lines.append("Definitions:")
            for symbol in self.symbols:
                qualifier = " approximate" if symbol.approximate else ""
                lines.append(
                    f"  - {symbol.kind} {symbol.name} (line {symbol.line}){qualifier}"
                )
        else:
            lines.append("Definitions: none recorded by the static reader.")
        if any(symbol.approximate for symbol in self.symbols):
            lines.append(
                "Approximate definitions came from text patterns, not from a language parser. "
                "Treat them as uncertain."
            )
        return "\n".join(lines)


class _PythonVisitor(ast.NodeVisitor):
    def __init__(self) -> None:
        self.imports: list[tuple[str, int]] = []
        self.symbols: list[Symbol] = []
        self._class: str | None = None

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            self.imports.append((alias.name, node.lineno))

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = node.module or ""
        self.imports.append((module or "(relative)", node.lineno))

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        name = f"{self._class}.{node.name}" if self._class else node.name
        self.symbols.append(Symbol("function", name, node.lineno))

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.visit_FunctionDef(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        self.symbols.append(Symbol("class", node.name, node.lineno))
        previous = self._class
        self._class = node.name if previous is None else f"{previous}.{node.name}"
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                self.visit(child)
        self._class = previous


def _outline_python(source: FileRead) -> CodeOutline:
    outline = CodeOutline(relative_path=source.relative_path, language="python")
    try:
        tree = ast.parse(source.text)
    except SyntaxError as exc:
        outline.parse_note = (
            f"Python parser note: {exc.msg} at line {exc.lineno}. "
            "The outline is incomplete."
        )
        return outline
    visitor = _PythonVisitor()
    visitor.visit(tree)
    outline.imports = visitor.imports
    outline.symbols = visitor.symbols
    return outline


def _outline_generic(source: FileRead) -> CodeOutline:
    suffix = PathSuffix.language(source.relative_path)
    outline = CodeOutline(relative_path=source.relative_path, language=suffix)
    outline.parse_note = (
        "No dedicated parser ran for this file type. "
        "Any definitions below are pattern matches and may be wrong."
    )
    for kind, pattern in _GENERIC_PATTERNS:
        for match in pattern.finditer(source.text):
            line = source.text.count("\n", 0, match.start()) + 1
            outline.symbols.append(Symbol(kind, match.group(1), line, approximate=True))
    return outline


class PathSuffix:
    """Map a few extensions to a language label. Unknown stays 'text'."""

    _MAP = {
        ".py": "python",
        ".pyi": "python",
        ".js": "javascript",
        ".jsx": "javascript",
        ".ts": "typescript",
        ".tsx": "typescript",
        ".go": "go",
        ".rs": "rust",
        ".java": "java",
        ".rb": "ruby",
        ".php": "php",
        ".cs": "c#",
    }

    @classmethod
    def language(cls, relative: str) -> str:
        suffix = "." + relative.lower().rsplit(".", 1)[-1] if "." in relative else ""
        return cls._MAP.get(suffix, "text")


def outline_source(source: FileRead) -> CodeOutline:
    """Build an outline from source text. Does not import or run the file."""
    if source.relative_path.lower().endswith((".py", ".pyi")):
        return _outline_python(source)
    return _outline_generic(source)


def excerpt(text: str, *, max_lines: int = 40) -> str:
    """Return a short excerpt and say when lines were omitted."""
    lines = text.splitlines()
    if len(lines) <= max_lines:
        return text if text.endswith("\n") or text == "" else text + "\n"
    head = "\n".join(lines[:max_lines])
    omitted = len(lines) - max_lines
    return f"{head}\n… [{omitted} more lines not shown]\n"
