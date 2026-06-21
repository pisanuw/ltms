"""CLTMS -- logical completeness via prime implicates (optional layer).

Plain clausal BCP is *sound but incomplete*: it can leave entailed literals
unknown (``{x v ~y, x v y}`` entails ``x``) and miss contradictions (the
four-clause set on two variables is unsatisfiable yet unit propagation never
fires). The cure is to add the logically-redundant-but-BCP-useful **prime
implicates** of the clause set; once they are present, every entailed unit and
every contradiction is reachable in one BCP step.

This module computes prime implicates by **consensus (resolution)** closed under
**subsumption** -- the brute-force saturation (Algorithm 13.1 in BPS). It is
correct but can be exponential; the book's incremental Tison method (IPIA) is
the efficiency optimization and is noted as future work. Call :func:`complete`
when you want completeness (the recommended "delay, then complete" usage), not
on every assertion.
"""

from __future__ import annotations

from .core import LTMS, Label, TmsNode

# A clause-as-set: frozenset of (node, sign) literals.
LitSet = "frozenset[tuple[TmsNode, Label]]"


def _opposite(sign: Label) -> Label:
    return Label.FALSE if sign is Label.TRUE else Label.TRUE


def consensus(
    c1: frozenset[tuple[TmsNode, Label]], c2: frozenset[tuple[TmsNode, Label]]
) -> frozenset[tuple[TmsNode, Label]] | None:
    """The consensus (resolvent) of two clauses, or None if they don't resolve.

    Two clauses resolve iff they share exactly one complementary literal pair;
    the resolvent is their union minus that pair. More than one complementary
    pair would yield a tautology, so None is returned.
    """
    complementary = {n for (n, s) in c1 if (n, _opposite(s)) in c2}
    if len(complementary) != 1:
        return None
    pivot = next(iter(complementary))
    merged = (set(c1) | set(c2)) - {(pivot, Label.TRUE), (pivot, Label.FALSE)}
    seen: dict[TmsNode, Label] = {}
    for n, s in merged:
        if n in seen and seen[n] is not s:
            return None  # tautology -- a second complementary pair survived
        seen[n] = s
    return frozenset(merged)


def subsumes(
    a: frozenset[tuple[TmsNode, Label]], b: frozenset[tuple[TmsNode, Label]]
) -> bool:
    """True iff clause ``a`` subsumes ``b`` (``a`` is a subset of ``b``)."""
    return a <= b


def prime_implicates(
    clauses: list[frozenset[tuple[TmsNode, Label]]],
) -> list[frozenset[tuple[TmsNode, Label]]]:
    """Saturate ``clauses`` under consensus, keeping a subsumption-minimal set."""
    result: list[frozenset[tuple[TmsNode, Label]]] = []
    queue = list(dict.fromkeys(clauses))  # dedup, preserve order
    while queue:
        c = queue.pop()
        if any(subsumes(p, c) for p in result):
            continue  # already covered by a more general clause
        result = [p for p in result if not subsumes(c, p)]  # drop ones c covers
        for p in result:
            r = consensus(c, p)
            if r is not None and not any(subsumes(q, r) for q in result):
                queue.append(r)
        result.append(c)
    return result


def complete(ltms: LTMS, informant: object = "prime-implicate") -> int:
    """Add the missing prime implicates of the LTMS's clauses, then settle.

    Returns the number of new clauses added. After this, BCP is logically
    complete for the current clause set: entailed units are forced and any
    unsatisfiability is detected (raising / dispatching a contradiction).
    """
    existing = [frozenset(cl.literals) for cl in ltms.clauses]
    have = set(existing)
    added = 0
    for pi in prime_implicates(existing):
        if pi in have:
            continue
        true_nodes = [n for (n, s) in pi if s is Label.TRUE]
        false_nodes = [n for (n, s) in pi if s is Label.FALSE]
        ltms.add_clause(true_nodes, false_nodes, informant)
        have.add(pi)
        added += 1
    return added
