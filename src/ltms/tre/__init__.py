"""TRE -- tiny pattern-directed inference engine (no truth maintenance)."""

from __future__ import annotations

from .engine import Dbclass, Rule, RuleBody, Tre

__all__ = ["Dbclass", "Rule", "RuleBody", "Tre"]
