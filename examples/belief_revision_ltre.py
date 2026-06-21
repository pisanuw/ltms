"""Belief revision driven entirely by a .kb data file.

The world model lives in ``kb/belief_revision.kb`` -- there is no theory mixed
into this Python, only the loader. Run:

    python examples/belief_revision_ltre.py
"""

from __future__ import annotations

from pathlib import Path

from ltms.dsl import KBResult, load_kb_file

KB = Path(__file__).resolve().parent / "kb" / "belief_revision.kb"


def main() -> KBResult:
    result = load_kb_file(KB)
    print(f"Loaded {KB.name}; checked beliefs:")
    for expr, status in result.queries:
        print(f"  {expr}: {status}")
    return result


if __name__ == "__main__":
    main()
