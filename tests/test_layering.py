"""Enforces the hexagonal layering: services/ and domain/ stay off the edges.

Run: python3 -m pytest tests/test_layering.py -v
"""

import ast
from pathlib import Path

SRC_ROOT = Path(__file__).parent.parent / "src" / "rentczecher"

FORBIDDEN_MODULES = ("sqlite3", "httpx", "smtplib")


def _owning_package(path: Path) -> tuple[str, ...]:
    """Dotted-path parts of the package a module file belongs to, for
    resolving its relative imports."""
    return path.relative_to(SRC_ROOT.parent).with_suffix("").parts[:-1]


def _resolve_relative(level: int, module: str | None, package: tuple[str, ...]) -> str:
    base = package[: len(package) - (level - 1)] if level > 1 else package
    return ".".join((*base, module) if module else base)


def _imported_names(tree: ast.Module, path: Path) -> list[str]:
    """Every module dotted-path this file imports, from both `import x.y`
    and `from x.y import z` forms, absolute or relative."""
    package = _owning_package(path)
    names = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            module = (
                _resolve_relative(node.level, node.module, package)
                if node.level > 0
                else node.module
            )
            if module is not None:
                names.append(module)
                names.extend(f"{module}.{alias.name}" for alias in node.names)
    return names


def _is_forbidden(imported: str, forbidden_prefixes: tuple[str, ...]) -> bool:
    return any(imported == prefix or imported.startswith(f"{prefix}.") for prefix in forbidden_prefixes)


def _violations(package_dir: Path, forbidden_prefixes: tuple[str, ...]) -> list[tuple[Path, str]]:
    found = []
    for path in sorted(package_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for imported in _imported_names(tree, path):
            if _is_forbidden(imported, forbidden_prefixes):
                found.append((path, imported))
    return found


def test_services_never_import_adapters_or_their_libraries():
    violations = _violations(
        SRC_ROOT / "services", FORBIDDEN_MODULES + ("rentczecher.adapters",)
    )
    assert violations == [], "\n".join(
        f"{path.relative_to(SRC_ROOT.parent.parent)} imports forbidden module {imported!r}"
        for path, imported in violations
    )


def test_domain_never_imports_adapters_or_services():
    violations = _violations(
        SRC_ROOT / "domain", ("rentczecher.adapters", "rentczecher.services")
    )
    assert violations == [], "\n".join(
        f"{path.relative_to(SRC_ROOT.parent.parent)} imports forbidden module {imported!r}"
        for path, imported in violations
    )


def test_relative_imports_resolve_to_their_absolute_dotted_path():
    """A forbidden import reached via `from ..x import y` or `from .. import x`
    is caught exactly like its absolute-import equivalent."""
    path = SRC_ROOT / "services" / "dedup.py"
    dotted_form = ast.parse("from ..adapters.geocoding.gazetteer import Gazetteer\n")
    bare_form = ast.parse("from .. import adapters\n")
    assert "rentczecher.adapters.geocoding.gazetteer" in _imported_names(dotted_form, path)
    assert "rentczecher.adapters" in _imported_names(bare_form, path)
