"""A small text format for describing a world model separately from Python.

A ``.kb`` file is a sequence of statements, one per line (``#`` starts a
comment). Propositions are written as space-separated words; multi-word
propositions are compounds, ``?x`` is a variable, numbers are numbers::

    rain                      # the proposition (rain)
    wet ground                # the compound (wet ground)
    sprinkler on -> wet ground   # an implication

Connectives (low to high precedence): ``<->`` ``->`` ``|`` ``&`` ``~``.
Parentheses group. ``->`` is right-associative.

Statements (the leading keyword is the directive; a bare line is an assertion)::

    rain -> wet ground            # assert a formula (permanent)
    assume rain                   # retractable assumption
    retract rain                  # withdraw it
    contradiction a, b            # a and b cannot both hold
    rule (human ?x) => (mortal ?x)            # universal forward rule
    rule (parent ?x ?y) & (parent ?y ?z) => (grandparent ?x ?z)
    taxonomy red, green, blue     # exactly one of them holds
    complete                      # add prime implicates (make BCP complete)
    query wet ground              # record its belief (true/false/unknown)
    expect wet ground true        # like query, but fails if it is not 'true'

``load_kb`` runs the statements against an :class:`~ltms.ltre.LTRE` and returns
a :class:`KBResult` (the recorded queries); ``expect`` lines make a ``.kb`` file
self-checking.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path

from .ltre import LTRE, RuleBody, Trigger
from .terms import Term, Var
from .unify import substitute

_MULTI_OPS = ("<->", "->", "=>")
_SINGLE_OPS = set("&|~(),")
_OP_START = set("<-=&|~(),")


def tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
            continue
        matched = False
        for op in _MULTI_OPS:
            if text.startswith(op, i):
                tokens.append(op)
                i += len(op)
                matched = True
                break
        if matched:
            continue
        if c in _SINGLE_OPS:
            tokens.append(c)
            i += 1
            continue
        j = i
        while j < n and not text[j].isspace() and text[j] not in _OP_START:
            j += 1
        if j == i:
            # A char in _OP_START that began no complete multi/single op
            # (a stray '<', '-', or '='): the word loop cannot advance, so
            # raise rather than spin forever on malformed input.
            raise ValueError(f"unexpected character {c!r} at position {i} in: {text!r}")
        tokens.append(text[i:j])
        i = j
    return tokens


def _atom(word: str) -> Term:
    if word.startswith("?"):
        return Var(word[1:])
    try:
        return int(word)
    except ValueError:
        pass
    try:
        value = float(word)
    except ValueError:
        return word
    # float() also parses "nan"/"inf"/"infinity"; those are almost certainly
    # proposition names, not numbers, and float('nan') would break node
    # identity (nan != nan). Keep only finite numeric literals as numbers.
    return value if math.isfinite(value) else word


class _Parser:
    def __init__(self, tokens: list[str]) -> None:
        self.toks = tokens
        self.pos = 0

    def peek(self) -> str | None:
        return self.toks[self.pos] if self.pos < len(self.toks) else None

    def next(self) -> str:
        tok = self.toks[self.pos]
        self.pos += 1
        return tok

    def expr(self) -> Term:
        return self._iff()

    def _iff(self) -> Term:
        left = self._implies()
        while self.peek() == "<->":
            self.next()
            left = ("iff", left, self._implies())
        return left

    def _implies(self) -> Term:
        left = self._or()
        if self.peek() == "->":
            self.next()
            return ("implies", left, self._implies())  # right-assoc
        return left

    def _or(self) -> Term:
        left = self._and()
        while self.peek() == "|":
            self.next()
            left = ("or", left, self._and())
        return left

    def _and(self) -> Term:
        left = self._not()
        while self.peek() == "&":
            self.next()
            left = ("and", left, self._not())
        return left

    def _not(self) -> Term:
        if self.peek() == "~":
            self.next()
            return ("not", self._not())
        return self._primary()

    def _primary(self) -> Term:
        tok = self.peek()
        if tok == "(":
            self.next()
            inner = self._iff()
            if self.peek() != ")":
                raise ValueError("missing ')'")
            self.next()
            return inner
        return self._proposition()

    def _proposition(self) -> Term:
        words: list[Term] = []
        while True:
            tok = self.peek()
            if tok is None or tok in _SINGLE_OPS or tok in _MULTI_OPS:
                break
            words.append(_atom(self.next()))
        if not words:
            raise ValueError(f"expected a proposition near {self.peek()!r}")
        return tuple(words)


def parse_expr(text: str) -> Term:
    """Parse one formula from text into a term."""
    parser = _Parser(tokenize(text))
    term = parser.expr()
    if parser.peek() is not None:
        raise ValueError(f"trailing tokens: {parser.toks[parser.pos:]}")
    return term


def _flatten_and(expr: Term) -> list[Term]:
    if isinstance(expr, tuple) and len(expr) == 3 and expr[0] == "and":
        return _flatten_and(expr[1]) + _flatten_and(expr[2])
    return [expr]


@dataclass
class KBResult:
    queries: list[tuple[str, str]] = field(default_factory=list)
    engine: LTRE | None = None
    clauses_added: int = 0  # prime implicates added by `complete` directives


def _status(engine: LTRE, expr: Term) -> str:
    if engine.is_true(expr):
        return "true"
    if engine.is_false(expr):
        return "false"
    return "unknown"


def _install_rule(engine: LTRE, antecedents: list[Term], consequent: Term) -> None:
    def step(i: int) -> RuleBody:
        def body(bindings: dict[Var, Term], e: LTRE) -> None:
            if i + 1 == len(antecedents):
                e.assert_(substitute(consequent, bindings))
            else:
                e.add_rule(
                    antecedents[i + 1], step(i + 1),
                    condition=Trigger.TRUE, environment=bindings,
                )

        return body

    engine.add_rule(antecedents[0], step(0), condition=Trigger.TRUE)


def load_kb(text: str, engine: LTRE | None = None) -> KBResult:
    """Run the statements in ``text`` against ``engine`` (created if None)."""
    engine = engine or LTRE()
    result = KBResult(engine=engine)
    for raw in text.splitlines():
        line = raw.split("#", 1)[0].strip()
        if not line:
            continue
        head, _, rest = line.partition(" ")
        rest = rest.strip()
        if head == "assume":
            expr = parse_expr(rest)
            engine.assume(expr, _informant(expr))
            engine.run_rules()
        elif head == "retract":
            expr = parse_expr(rest)
            engine.retract(expr, _informant(expr))
            engine.run_rules()
        elif head == "contradiction":
            facts = [parse_expr(part) for part in _split_top(rest)]
            engine.contradiction(facts)
            engine.run_rules()
        elif head == "rule":
            lhs, sep, rhs = rest.partition("=>")
            if not sep:
                raise ValueError(f"rule needs '=>': {line!r}")
            antecedents = _flatten_and(parse_expr(lhs))
            _install_rule(engine, antecedents, parse_expr(rhs))
            engine.run_rules()
        elif head == "taxonomy":
            options = [parse_expr(part) for part in _split_top(rest)]
            engine.assert_(("taxonomy", *options))  # exactly one of them holds
            engine.run_rules()
        elif head == "complete":
            from .cltms import complete

            result.clauses_added += complete(engine.ltms)
            engine.run_rules()
        elif head == "query":
            expr = parse_expr(rest)
            result.queries.append((rest, _status(engine, expr)))  # rest already stripped
        elif head == "expect":
            *expr_words, expected = rest.split()
            expr_text = " ".join(expr_words)
            expr = parse_expr(expr_text)
            actual = _status(engine, expr)
            if actual != expected:
                raise AssertionError(
                    f"expect failed: {expr_text} is {actual}, wanted {expected}"
                )
            result.queries.append((expr_text, actual))
        else:  # bare line: an assertion
            engine.assert_(parse_expr(line))
            engine.run_rules()
    return result


def load_kb_file(path: str | Path, engine: LTRE | None = None) -> KBResult:
    return load_kb(Path(path).read_text(), engine)


def _informant(expr: Term) -> str:
    from .terms import term_to_str

    return f"kb:{term_to_str(expr)}"


def _split_top(text: str) -> list[str]:
    """Split on top-level commas (no nesting needed for current uses)."""
    return [part.strip() for part in text.split(",") if part.strip()]
