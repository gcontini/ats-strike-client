"""The rules that keep the client a client.

These are not style checks: the frozen client must not drag in the server's
dependencies, and it talks to the server over HTTP only, through the
contracts package. The server and its pipeline live in another repository;
these tests make sure nothing here starts to lean on them.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Set

CLIENT = Path(__file__).resolve().parents[1] / "src" / "cv_client"


def imports_of(package: Path) -> Set[str]:
    """Every top-level module imported anywhere in a package."""
    found: Set[str] = set()
    for path in package.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                found.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
                found.add(node.module.split(".")[0])
    return found


def test_the_client_never_imports_the_server_or_the_pipeline():
    used = imports_of(CLIENT)
    assert "cv_contracts" in used, "the check must see the imports it is checking"
    assert not used & {"cv_server", "pipeline_v1"}


def test_the_client_carries_no_server_side_dependency():
    """No LaTeX, no model SDK, no templating in the shipped executable."""
    forbidden = {
        "openai",
        "jinja2",
        "pypdf",
        "fastapi",
        "uvicorn",
        "subprocess",
        "langchain_core",
        "langchain_openai",
        "langchain_deepseek",
        "langgraph",
    }
    assert not (imports_of(CLIENT) & forbidden - {"subprocess"})
    # subprocess is allowed in exactly one place: probing the clipboard helper.
    users = [p.name for p in CLIENT.rglob("*.py") if "import subprocess" in p.read_text(encoding="utf-8")]
    assert users == ["clipboard.py"]


def client_modules_used_by(subpackage: Path) -> Set[str]:
    """Every ``cv_client.<module>`` a client subpackage imports, however spelled."""
    found: Set[str] = set()
    for path in subpackage.rglob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name.split(".") for alias in node.names]
                found.update(parts[1] for parts in names if parts[0] == "cv_client" and len(parts) > 1)
            elif isinstance(node, ast.ImportFrom):
                parts = (node.module or "").split(".")
                if node.level == 0 and parts[0] == "cv_client" and len(parts) > 1:
                    found.add(parts[1])
                elif node.level == 2 and node.module:  # from ..module import x
                    found.add(parts[0])
                elif node.level == 2:  # from .. import module
                    found.update(alias.name for alias in node.names)
    return found


def test_the_stages_never_reach_back_into_the_modes_or_the_sources():
    """``stages/`` is the one pipeline every mode builds on. It uses the shared
    modules (the API, the workspace, the spreadsheet) but never a mode, and
    never where a posting comes from: a new source is a new ``JDSource``,
    handed in by its mode, and no change here."""
    used = client_modules_used_by(CLIENT / "stages")
    assert "workspace" in used, "the check must see the imports it is checking"
    assert not used & {"modes", "sources"}
