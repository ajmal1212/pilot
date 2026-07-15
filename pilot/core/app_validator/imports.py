from __future__ import annotations

import ast
import sys
import typing
from collections.abc import Iterable, Iterator
from pathlib import Path

from pilot.core.app_validator.base import python_files
from pilot.core.app_validator.module_resolver import ModuleResolver
from pilot.core.app_validator.tmp_env import TmpEnv

if typing.TYPE_CHECKING:
    from pilot.core.app import App


class ImportCheck:
    """Installs the app into a throwaway venv and verifies every import it
    makes actually resolves, without executing any module-level code."""

    def __init__(self) -> None:
        self.tmp_env = TmpEnv()

    def run(self, app: "App") -> None:
        try:
            self.tmp_env.create(app.bench.apps_path / "frappe")
            self.tmp_env.install_app(app)
            self._check_imports(app)
        finally:
            self.tmp_env.delete()

    def _check_imports(self, app: "App") -> None:
        # Stat-based resolution first (fast, no code runs); anything it can't
        # find goes through find_spec in the tmp env for an authoritative error.
        resolver = ModuleResolver(self.tmp_env.path)
        unresolved = resolver.unresolved(self._imported_modules(app))
        if unresolved:
            self.tmp_env.resolve_modules(unresolved)

    def _imported_modules(self, app: "App") -> list[str]:
        modules: set[str] = set()
        for path in python_files(app):
            if not self._is_test_file(path):
                modules.update(self._file_imported_modules(app, path))
        return sorted(m for m in modules if m.split(".")[0] not in sys.stdlib_module_names)

    @staticmethod
    def _is_test_file(path: Path) -> bool:
        # Test-only imports (responses, time_machine, ...) come from dev extras
        # a plain pip install never provides, so they'd always fail to resolve.
        return path.name.startswith("test_") or path.name == "conftest.py"

    def _file_imported_modules(self, app: "App", path: Path) -> set[str]:
        try:
            tree = ast.parse(path.read_text(), filename=str(path))
        except OSError:
            # We ideally should never hit SyntaxError here because we already validated syntax.
            return set()

        modules = set()
        for node in self._runtime_imports(tree.body):
            if isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
            else:
                modules.add(self._resolve_module(app, path, node.level, node.module))
        return modules

    def _runtime_imports(
        self, nodes: Iterable[ast.AST]
    ) -> Iterator[ast.Import | ast.ImportFrom]:
        """Imports that must resolve at runtime — skips imports guarded by
        try/except ImportError and `if TYPE_CHECKING:` blocks, which apps use
        for genuinely optional dependencies."""
        for node in nodes:
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                yield node
            elif isinstance(node, ast.Try) and self._handles_import_error(node):
                continue
            elif isinstance(node, ast.If) and self._is_type_checking(node.test):
                yield from self._runtime_imports(node.orelse)
            else:
                yield from self._runtime_imports(ast.iter_child_nodes(node))

    @staticmethod
    def _handles_import_error(node: ast.Try) -> bool:
        catchers = {"ImportError", "ModuleNotFoundError", "Exception", "BaseException"}
        for handler in node.handlers:
            if handler.type is None:
                return True
            names = {n.id for n in ast.walk(handler.type) if isinstance(n, ast.Name)}
            names |= {n.attr for n in ast.walk(handler.type) if isinstance(n, ast.Attribute)}
            if names & catchers:
                return True
        return False

    @staticmethod
    def _is_type_checking(test: ast.expr) -> bool:
        return (isinstance(test, ast.Name) and test.id == "TYPE_CHECKING") or (
            isinstance(test, ast.Attribute) and test.attr == "TYPE_CHECKING"
        )

    @staticmethod
    def _resolve_module(app: "App", path: Path, level: int, module: str | None) -> str:
        if level == 0:
            return module or ""
        parts = path.relative_to(app.path).with_suffix("").parts[:-1]
        if level > 1:
            parts = parts[: -(level - 1)] if level - 1 <= len(parts) else ()
        base = ".".join(parts)
        return f"{base}.{module}" if module else base
