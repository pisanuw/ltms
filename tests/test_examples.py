"""Smoke tests: every example script's main() runs and returns sane results."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _load(name: str) -> Any:
    path = _EXAMPLES / name
    spec = importlib.util.spec_from_file_location(name[:-3], path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_family_tre_example():
    result = _load("family_tre.py").main()
    assert ("ancestor", "ann", "dee") in result  # transitive closure reached


def test_belief_revision_example():
    result = _load("belief_revision_ltre.py").main()  # loads kb/belief_revision.kb
    assert result.engine is not None
    assert result.engine.is_unknown(("wet", "ground"))  # both supports retracted


def test_coloring_dds_example():
    result = _load("coloring_dds.py").main()
    assert result  # the map is colorable
    for solution in result:
        assigned = dict(solution)
        assert len(assigned) == 4  # all four regions colored
