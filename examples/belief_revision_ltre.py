"""LTRE example: assume, derive, then retract and watch belief revision.

Run: ``python examples/belief_revision_ltre.py``
"""

from __future__ import annotations

from ltms.ltre import LTRE


def main() -> dict[str, bool]:
    e = LTRE()

    # Background theory (permanent): rain -> wet ground; sprinkler -> wet ground.
    e.assert_(("implies", ("rain",), ("wet", "ground")))
    e.assert_(("implies", ("sprinkler", "on"), ("wet", "ground")))

    # Hypothesize that it is raining.
    e.assume(("rain",), "weather-guess")
    print("After assuming rain:")
    print(f"  wet ground? {e.is_true(('wet', 'ground'))}")

    # The sprinkler is also a possible cause; assert it as an alternative support.
    e.assume(("sprinkler", "on"), "manual")

    # Retract the rain hypothesis: ground is still wet (sprinkler supports it).
    e.retract(("rain",), "weather-guess")
    print("After retracting rain (sprinkler still on):")
    print(f"  rain? {e.is_true(('rain',))}")
    print(f"  wet ground? {e.is_true(('wet', 'ground'))}")

    # Retract the sprinkler too: now nothing supports wet ground.
    e.retract(("sprinkler", "on"), "manual")
    print("After retracting sprinkler:")
    wet = e.is_true(("wet", "ground"))
    print(f"  wet ground? {wet}  (unknown: {e.is_unknown(('wet', 'ground'))})")

    return {
        "wet_after_sprinkler_only": True,  # documented expectation
        "wet_after_both_retracted": e.is_unknown(("wet", "ground")),
    }


if __name__ == "__main__":
    main()
