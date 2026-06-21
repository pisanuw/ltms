"""Run every .kb world-model file; `expect` lines make them self-checking.

Covers both the runnable examples (examples/kb) and the declarative book
exercises expressed as data files (exercises/chNN/kb).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from ltms.dsl import load_kb_file

_ROOT = Path(__file__).resolve().parent.parent
_KB_FILES = sorted((_ROOT / "examples").glob("kb/*.kb")) + sorted(
    (_ROOT / "exercises").glob("ch*/kb/*.kb")
)


@pytest.mark.parametrize("kb_path", _KB_FILES, ids=lambda p: f"{p.parent.parent.name}/{p.name}")
def test_kb_file_runs_clean(kb_path):
    result = load_kb_file(kb_path)  # raises AssertionError on any failed expect
    assert result.engine is not None


def test_at_least_several_kb_files_present():
    assert len(_KB_FILES) >= 10, f"expected many .kb files, found {len(_KB_FILES)}"
