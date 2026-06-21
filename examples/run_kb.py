"""Load a .kb world-model file and print its query results.

Run: ``python examples/run_kb.py examples/kb/belief_revision.kb``
"""

from __future__ import annotations

import sys

from ltms.dsl import KBResult, load_kb_file


def main(path: str = "examples/kb/belief_revision.kb") -> KBResult:
    result = load_kb_file(path)
    print(f"Loaded {path}")
    for expr, status in result.queries:
        print(f"  {expr}: {status}")
    return result


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "examples/kb/belief_revision.kb")
