# Chapter 13 — Improving the Completeness of TMS (CLTMS): exercises

Worked solutions for the completeness chapter. Statements are **paraphrased in
our own words** (the originals are copyrighted); answers and code are original.
The runnable demonstrations are in [solutions.py](solutions.py).

Background: clausal **Boolean Constraint Propagation (BCP)** is sound but
*incomplete*. It can leave an entailed literal `unknown` (e.g. `{x∨¬y, x∨y}`
entails `x` yet no unit ever propagates) and can miss an outright contradiction
(the four-clause set over `{p,q}` is unsatisfiable but no unit ever fires). The
cure used by the CLTMS is to add the logically redundant but BCP-useful **prime
implicates** of the clause set. The package implements this via `consensus`
(resolution), `prime_implicates` (saturate under consensus, keep subsumption-
minimal), `complete` (install the missing prime implicates and re-settle), and
`try_indirect_proof` (assume the negation, look for a contradiction).

---

**1 (★) — A formula with far more prime implicates than CNF conjuncts.**
*(demonstrated in code)*
Paraphrase: exhibit a formula whose prime-implicate count greatly exceeds the
number of clauses in its conjunctive normal form.
Answer: a **transitive implication chain** `x0→x1→…→x_{n−1}` is stored as just
`n−1` binary clauses, but its prime implicates are *all* derived implications
`x_i→x_j` for `i<j`, i.e. `C(n,2)=n(n−1)/2` of them. So the count is quadratic
while the input is linear; `solutions.py` verifies 4→10 (n=5) and 7→28 (n=8). For
an *exponential* gap, see Ex 9 (kean): clauses force, by resolution, a clause for
every choice of one `s_j` per `a_i`, which is exponential in `k`.

**2 (★) — Show consensus is not associative.** *(demonstrated in code)*
Paraphrase: give three clauses for which `(c1∘c2)∘c3` differs from
`c1∘(c2∘c3)`, where `∘` is consensus (resolution).
Answer: take `c1={a}`, `c2={¬a,b}`, `c3={a,¬b,c}`.
- Left grouping: `c1∘c2={b}`, then `{b}∘c3={a,c}` — **defined**.
- Right grouping: `c2∘c3` shares *two* complementary pairs (`a/¬a` and `b/¬b`),
  so the resolvent would be a tautology and consensus returns **None**; hence
  `c1∘None` is undefined.
The two groupings disagree (one yields `{a,c}`, the other is undefined), so
consensus is not associative. This is exactly why the saturation algorithm must
take consensus over *all* pairs repeatedly rather than fold left-to-right.

**3 (★★) — Let the user justify / enable / retract whole formulas.**
Paraphrase: extend the LTMS interface so formulas (not just primitive nodes) can
be premises, enabled, and retracted as units.
Answer (design): a formula is installed as several CNF clauses, so to make a
formula a controllable unit you give it a single **reified node** `F` and add the
biconditional `F ↔ formula` (in CNF, the implications both ways). Then:
- *justify a formula*: add a clause whose conclusion is `F` (or just install the
  clauses with `F` as informant);
- *enable a formula*: `enable_assumption(F, Label.TRUE)` — its CNF body is forced;
- *retract a formula*: `retract_assumption(F)`, which withdraws the body via the
  `F→body` half of the biconditional (the clauses are tagged by `F` so the TMS
  knows their support).
The package already tags every installed clause with an informant
(`add_formula(m, formula, informant)`); grouping all clauses of one formula under
a reified controlling node is the missing piece, and is straightforward to add on
top of the existing `assume`/`enable_assumption`/`retract_assumption` API.
(Design/answer only.)

**4 (★) — Prime implicates of a TAXONOMY on n nodes.** *(demonstrated in code)*
Paraphrase: count the prime implicates of an "exactly one of n" (taxonomy)
constraint.
Answer: **`1 + C(n,2) = 1 + n(n−1)/2`**. The taxonomy expands to one "at least
one" clause `(x_1∨…∨x_n)` plus the `n(n−1)/2` pairwise "not both" clauses
`(¬x_i∨¬x_j)`. This CNF is *already* its own prime-implicate set: consensus
between two "not both" clauses needs a complementary pair, but they share only
negative literals (no resolution); consensus of the big clause with `(¬x_i∨¬x_j)`
yields a clause subsumed by an existing one. `solutions.py` confirms the formula
for n = 3, 5, 6 (4, 11, 16).

**5 (★★) — A `subsumed?` that also checks node ids; does it help performance?**
Paraphrase: implement subsumption that, beyond the subset test, also distinguishes
clauses by identity, and measure whether it speeds anything up.
Answer: the package's `subsumes(a,b)` is the pure subset test `a ⊆ b` over
`frozenset`s of `(node, sign)` literals; clause identity is already captured
because literals reference the *same* `TmsNode` objects (identity, not value).
Adding an explicit id check on top of the subset test does **not** change which
clauses are removed (a clause subsumes itself trivially under `⊆`), so semantics
are unchanged. Performance: an id-based fast path can short-circuit the obvious
"is this the identical clause" case before doing the (potentially larger) subset
scan, but with `frozenset` subset already O(min(|a|,|b|)) the win is marginal; the
real cost in `prime_implicates` is the *number* of consensus operations and the
all-pairs subsumption sweeps, not the per-pair test. So: an id-checking
`subsumed?` is correct but makes essentially no difference here. (Answer only;
the existing `ltms.cltms.subsumes` is the reference implementation.)

**6 (★★) — Convert qualitative equations to formulas, then to prime implicates.**
Paraphrase: take qualitative ("sign") equations and turn them into propositional
formulas whose prime implicates can be computed.
Answer (method): a qualitative variable `q` has sign in `{−,0,+}`, modeled as a
3-way taxonomy `taxonomy(q⁻, q⁰, q⁺)`. A qualitative sum `[x] + [y] = [z]`
becomes the (finite) sign-addition table: enumerate the legal `(sx, sy, sz)`
triples and assert the disjunction over them, equivalently exclude the illegal
triples as clauses `¬(x_sx ∧ y_sy ∧ z_sz)`. Once every equation is a set of
clauses over these sign literals, run `prime_implicates` on the whole set to get
the minimal entailed sign constraints (e.g. `x⁺ ∧ y⁺ → z⁺`). Reuse `normalize`
for the taxonomy/`not`/`and` expansion and `prime_implicates` for the reduction.
(Method/answer; the building blocks — `taxonomy` normalization and
`prime_implicates` — are demonstrated for taxonomies in Ex 4.)

**7 (★★) — An ATMS that is plug-compatible with the earlier one but built on the
CLTMS.**
Paraphrase: reimplement the ATMS interface on top of the completeness machinery.
Answer (design): the ATMS labels are the prime implicates restricted to
assumption literals. Build it as: install all justifications as CLTMS clauses
tagged by assumption nodes; run `complete` (consensus saturation) to get prime
implicates; for each datum, its **label** is the set of minimal assumption sets
that entail it, read off as the prime implicates that resolve down to that node's
literal (negate the assumption literals to get the supporting environment). The
nogoods are exactly the prime implicates containing only (negated) assumption
literals (the empty-conclusion ones). This gives the four ATMS label properties
(sound, complete, consistent, minimal) for free, because prime implicates are by
construction subsumption-minimal and consensus-complete. (Design only; the
underlying `prime_implicates`/`complete` are demonstrated in code.)

**8 (★★) — A trie-based nogood store for a more efficient ATMS.**
Paraphrase: replace the ATMS nogood table with a trie so nogood subsumption
queries are faster.
Answer (design): store each nogood (a sorted tuple of assumption ids) as a path
in a trie keyed by assumption id. Subsumption test "is some stored nogood a
subset of environment E?" becomes a depth-first walk that, at each node, may skip
absent ids; the first complete path found is a subsuming nogood. Insertion prunes
any stored superset along the way. This turns the linear scan of the flat nogood
table into a search bounded by the trie's branching, matching the CLTMS clause set
which is already a compact subsumption-minimal structure. (Design only; the CLTMS
side — subsumption-minimal clause sets — is what `prime_implicates` maintains.)

**9 (★★) — Prime-implicate count for the `kean` problem.**
*(demonstrated in code)*
Paraphrase: for the given Lisp routine that builds clauses `(a_i ∨ ¬s_j)` for all
`i≤k, j≤m` plus the single clause `(¬a_1 ∨ … ∨ ¬a_k)`, count the prime implicates
of `kean(3,6)` and `kean(5,10)` and find the general formula.
Answer (with an honesty caveat): under a **faithful reading of the printed (and
clearly OCR-garbled) listing** — note the `(1+ 0)` typo and the broken parens —
each `s_j` implies *every* `a_i`, which together with "not all `a_i`" makes each
`¬s_j` an entailed **unit** prime implicate; with the original big clause that is
`m + 1` prime implicates. `solutions.py` computes `kean(3,6)=7` and
`kean(5,10)=11`, matching `m+1`.
The book's stated answer, **`kean(5,10) = 60,466,236`**, does *not* come from this
reading (and `60,466,236 = 2²·3·5,038,853`, with that last factor prime, is not a
clean combinatorial expression). It must come from a different, un-garbled version
of the code in which the `s_j` clauses do **not** force `¬s_j` units — for
instance if the second clause is `(a_i ∨ s_j)` (so each `¬a_i` in the big clause
can be resolved away by *any* of the `m` choices independently), the prime
implicates become every clause formed by replacing each `¬a_i` by one of `m`
literals, giving a count that is **exponential in `k`** (on the order of `(m+1)^k`
before subsumption). I could not reconstruct the exact listing that yields
60,466,236 from the OCR; I am reporting what the printed code actually computes and
the structural reason the true answer is combinatorial rather than linear.

**10 (★★★★) — A notion of "BCP-prime implicates".**
Paraphrase: since full prime implicates are overkill for BCP completeness (the
current method blocks consensus once BCP already satisfies a clause), ask whether
one can define directly-computable *BCP-prime implicates* that guarantee BCP
completeness relative to the original clause set.
Answer (discussion): yes in principle, and this is essentially what the package
already approximates with "delay, then `complete`". The goal is the **smallest
set of added clauses such that unit propagation is refutation-complete** for the
clause set — every entailed unit is forced and every contradiction detected in one
BCP step. A BCP-prime implicate would be a clause that (a) is entailed, (b) is not
already made redundant by BCP given the current set, and (c) is minimal with that
property. Unlike ordinary prime implicates, the criterion is *operational*
(relative to what BCP can already derive), so many ordinary prime implicates are
not BCP-prime (they are entailed but never needed because BCP gets the same effect
from shorter clauses). Computing them directly means generating only those
resolvents that *unblock* future unit propagation — a focused, BCP-guided
consensus rather than full saturation. This is exactly the optimization the module
notes as future work (the incremental Tison/IPIA method); our `complete` does the
post-hoc full saturation instead. (Discussion only.)

**11 (★★★) — Prime implicants as negated prime implicates.**
Paraphrase: an implicant of a formula set is a complementary-pair-free
conjunction of literals that entails the set; a *prime* implicant has no
implicant proper subconjunction. Show the prime implicants of Σ are the negations
of the prime implicates of ¬Σ (treating Σ as a conjunction), and give a procedure
returning prime implicants using the CLTMS.
Answer (proof + procedure):
- *Proof.* `T = ℓ_1 ∧ … ∧ ℓ_r` is an implicant of Σ iff `T ⊨ Σ` iff `¬Σ ⊨ ¬T`
  iff `¬T = ¬ℓ_1 ∨ … ∨ ¬ℓ_r` is an implicate (entailed clause) of `¬Σ`. The
  subset/subsumption order is reversed exactly by negation: `T' ⊂ T` (a proper
  subconjunction) corresponds to `¬T' ⊂ ¬T` (a proper subclause). Hence `T` is a
  *prime* implicant of Σ (no implicant subconjunction) iff `¬T` is a *prime*
  implicate of `¬Σ` (no implicate subclause). So the prime implicants of Σ are
  exactly the negations of the prime implicates of ¬Σ.  ∎
- *Procedure (sketch using this package).* Form `¬Σ` (negate the conjunction:
  `normalize(("not", ("and", *formulas)))`), feed those clauses to
  `prime_implicates`, then negate each resulting clause literal-by-literal to get
  the prime implicants of Σ. The CLTMS supplies both halves: `normalize` for the
  CNF of `¬Σ` and `prime_implicates` for the consensus saturation. (Proof above;
  procedure is the dual of the demonstrated `prime_implicates` pipeline.)

---

## What is demonstrated in code

| Exercise | In `solutions.py` |
|---|---|
| 1 (blowup: chain → C(n,2) PIs) | yes |
| 2 (consensus not associative) | yes |
| 4 (taxonomy PI count = 1+C(n,2)) | yes |
| 9 (kean PI counts, our reading) | yes |
| completeness theme (BCP gap cured by `complete` and `try_indirect_proof`, 4-clause unsat) | yes |
| 3, 5, 6, 7, 8, 10, 11 | written answer / design only |

Run the demonstrations:

```bash
. .venv/bin/activate && python exercises/ch13/solutions.py
```
