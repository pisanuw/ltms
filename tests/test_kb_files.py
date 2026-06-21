"""Run every .kb file under examples/kb; `expect` lines make them self-checking."""

from __future__ import annotations

from pathlib import Path

import pytest

from ltms.dsl import load_kb_file

_KB_DIR = Path(__file__).resolve().parent.parent / "examples" / "kb"
_KB_FILES = sorted(_KB_DIR.glob("*.kb")) if _KB_DIR.exists() else []


@pytest.mark.parametrize("kb_path", _KB_FILES, ids=lambda p: p.name)
def test_kb_file_runs_clean(kb_path):
    result = load_kb_file(kb_path)  # raises AssertionError on any failed expect
    assert result.engine is not None


def test_at_least_one_kb_file_present():
    assert _KB_FILES, "expected example .kb files under examples/kb"
