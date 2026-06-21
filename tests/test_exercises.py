"""Run every exercises/chNN/solutions.py solve() to keep them honest."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

_EX_DIR = Path(__file__).resolve().parent.parent / "exercises"
_SOLUTIONS = sorted(_EX_DIR.glob("ch*/solutions.py")) if _EX_DIR.exists() else []


def _load(path: Path) -> Any:
    spec = importlib.util.spec_from_file_location(f"sol_{path.parent.name}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("path", _SOLUTIONS, ids=lambda p: p.parent.name)
def test_solutions_run(path: Path) -> None:
    module = _load(path)
    assert hasattr(module, "solve"), f"{path} must define solve()"
    result = module.solve()
    assert isinstance(result, dict) and result, f"{path} solve() returned nothing useful"
