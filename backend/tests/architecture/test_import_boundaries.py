import ast
from pathlib import Path

BACKEND_SRC = Path(__file__).resolve().parents[2] / "src" / "study_podcast"


def module_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.add(node.module.split(".")[0])
    return imports


def python_files(folder: str) -> list[Path]:
    return list((BACKEND_SRC / folder).rglob("*.py"))


def test_domain_does_not_import_framework_database_filesystem_or_tts_libraries() -> None:
    forbidden = {"fastapi", "sqlite3", "pathlib", "wave", "chatterbox"}

    offenders = {
        str(path.relative_to(BACKEND_SRC)): sorted(module_imports(path) & forbidden)
        for path in python_files("domain")
        if module_imports(path) & forbidden
    }

    assert offenders == {}


def test_application_does_not_import_fastapi_or_concrete_adapters() -> None:
    forbidden = {"fastapi", "sqlite3", "wave", "chatterbox"}

    offenders = {
        str(path.relative_to(BACKEND_SRC)): sorted(module_imports(path) & forbidden)
        for path in python_files("application")
        if module_imports(path) & forbidden
    }

    assert offenders == {}


def test_inbound_routes_use_route_facing_container_interfaces() -> None:
    forbidden_snippets = {
        ".projects",
        ".scripts",
        ".snapshots",
        ".voices",
        ".jobs",
        ".queue",
        ".storage",
        ".runner",
        ".worker_pool",
        ".settings_repo",
        ".env_writer",
    }

    offenders = {}
    for path in python_files("adapters/inbound/api"):
        text = path.read_text(encoding="utf-8")
        found = sorted(snippet for snippet in forbidden_snippets if f"container{snippet}" in text)
        if found:
            offenders[str(path.relative_to(BACKEND_SRC))] = found

    assert offenders == {}
