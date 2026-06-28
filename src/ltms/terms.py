"""Term representation for the reasoning engine.

A *term* is an s-expression built from:

* **atoms** -- ``str`` (symbols), ``int``/``float`` (numbers),
* **variables** -- :class:`Var` instances (we do *not* use the Lisp ``?name``
  symbol convention internally; a ``Var`` is its own type), and
* **compound terms** -- ``tuple`` of terms.

Tuples are immutable and hashable, which makes structural equality and
dict-keying free -- handy for the fact databases built on top of this.

A small s-expression :func:`read` is provided for convenience so tests and
examples can write ``read("(implies (human ?x) (mortal ?x))")`` instead of
nested tuples; ``?``-prefixed tokens become :class:`Var`.
"""

from __future__ import annotations

from typing import TypeGuard, Union

Atom = str | int | float
# Recursive, forward-referencing alias: Var is defined below and Term refers to
# itself, so this must stay a string-based Union (cannot use bare `X | Y` here).
Term = Union[Atom, "Var", "tuple[Term, ...]"]  # noqa: UP007


class Var:
    """A logic variable, identified by name.

    Two variables are equal iff they have the same name, so a single name
    denotes a single logic variable across a unification (BPS does **not**
    standardize variables apart; rules carry a seed environment instead).
    """

    __slots__ = ("name",)

    def __init__(self, name: str) -> None:
        self.name = name

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Var) and other.name == self.name

    def __hash__(self) -> int:
        return hash(("Var", self.name))

    def __repr__(self) -> str:
        return f"?{self.name}"


def var(name: str) -> Var:
    """Construct a :class:`Var`, accepting an optional leading ``?``."""
    return Var(name[1:] if name.startswith("?") else name)


def is_variable(x: object) -> TypeGuard[Var]:
    """True iff ``x`` is a logic variable."""
    return isinstance(x, Var)


def is_compound(x: object) -> TypeGuard[tuple[Term, ...]]:
    """True iff ``x`` is a compound term (a tuple)."""
    return isinstance(x, tuple)


def is_atom(x: object) -> bool:
    """True iff ``x`` is an atom (neither a variable nor a compound term)."""
    return not isinstance(x, (Var, tuple))


def index_symbol(term: Term, env: dict[Var, Term] | None = None) -> str:
    """The leftmost ground symbol used to index ``term`` in a fact/rule database.

    Descends into a compound term's head and chases bound variables through
    ``env`` until it reaches a symbol. Raises :class:`ValueError` on the empty
    term, an unbound variable in head position, or a non-symbol key. Shared by
    the TRE / JTRE / LTRE ``get_dbclass`` methods so their indexing stays
    identical.
    """
    while True:
        if is_compound(term):
            if not term:
                raise ValueError("cannot index the empty term ()")
            term = term[0]
        elif is_variable(term):
            if env is not None and term in env:
                term = env[term]
            else:
                raise ValueError(f"dbclass: unbound variable {term!r} in head position")
        elif isinstance(term, str):
            return term
        else:
            raise ValueError(f"dbclass key must be a symbol, got {term!r}")


def term_to_str(term: Term) -> str:
    """Render a term back into s-expression notation."""
    if isinstance(term, Var):
        return f"?{term.name}"
    if isinstance(term, tuple):
        return "(" + " ".join(term_to_str(e) for e in term) + ")"
    return str(term)


# --------------------------------------------------------------------------- #
# s-expression reader (convenience for tests / examples)
# --------------------------------------------------------------------------- #


def _tokenize(text: str) -> list[str]:
    tokens: list[str] = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if c.isspace():
            i += 1
        elif c in "()":
            tokens.append(c)
            i += 1
        else:
            j = i
            while j < n and not text[j].isspace() and text[j] not in "()":
                j += 1
            tokens.append(text[i:j])
            i = j
    return tokens


def _atom(token: str) -> Term:
    if token.startswith("?"):
        return Var(token[1:])
    try:
        return int(token)
    except ValueError:
        pass
    try:
        return float(token)
    except ValueError:
        pass
    return token


def _parse(tokens: list[str], pos: int) -> tuple[Term, int]:
    if pos >= len(tokens):
        raise ValueError("unexpected end of input")
    token = tokens[pos]
    if token == "(":
        items: list[Term] = []
        pos += 1
        while pos < len(tokens) and tokens[pos] != ")":
            item, pos = _parse(tokens, pos)
            items.append(item)
        if pos >= len(tokens):
            raise ValueError("missing closing ')'")
        return tuple(items), pos + 1
    if token == ")":
        raise ValueError("unexpected ')'")
    return _atom(token), pos + 1


def read(text: str) -> Term:
    """Read exactly one term from an s-expression string."""
    tokens = _tokenize(text)
    term, pos = _parse(tokens, 0)
    if pos != len(tokens):
        raise ValueError("trailing tokens after first term")
    return term


def read_all(text: str) -> list[Term]:
    """Read all top-level terms from an s-expression string."""
    tokens = _tokenize(text)
    out: list[Term] = []
    pos = 0
    while pos < len(tokens):
        term, pos = _parse(tokens, pos)
        out.append(term)
    return out
