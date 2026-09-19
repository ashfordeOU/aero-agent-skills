# Test strength, not test count

`tools/mutation/mutation_score.py` replaces the claim "10 to 65 tests per leaf"
with a number that can be defended: a **sampled mutation score**.

A test count is an inventory of files. It tells a buyer nothing about whether a
suite would notice if the logic were wrong. The published HumanEval work made
that concrete: suites that looked adequate by count turned out to be weak
enough that adding far more tests moved measured pass rates by tens of points
and reordered the leaderboard. A count that can move like that is not a quality
claim.

A mutation score is a different kind of statement. Damage a logic module in a
small, well-defined way, then run that leaf's own suite against the damaged
copy. If the suite goes red, the mutant is **killed** and the suite was watching
that behaviour. If the suite still passes, the mutant **survived** and there is
a hole in the suite.

---

## The measured result

Corpus: 3,021 leaves, fingerprint
`sha256:f677dc813a989ecbf322a415389341b103c130888388d8e1d68c8a97f64351a4`.

| run | seed | leaves (n) | mutants | killed | survived | score | 95% CI (leaf bootstrap) |
|---|---|---|---|---|---|---|---|
| reference | 20260919 | 40 | 1,000 | 819 | 181 | **0.8190** | [0.7760, 0.8590] |
| **deep** | 20260919 | 500 | 19,911 | 16,006 | 3,905 | **0.8039** | [0.7934, 0.8139] |
| replication | 77 | 200 | 7,976 | 6,387 | 1,589 | **0.8008** | [0.7838, 0.8174] |

The headline number is **0.80 (95% CI 0.79 to 0.81, n = 500 leaves, 19,911
mutants, seed 20260919)**. One mutant in five slips past the suite that is
supposed to be guarding the behaviour it damaged.

The three runs draw disjoint-ish samples at two different seeds and land within
two points of each other, so the estimate is not an artefact of one draw. All
three ran against the same corpus fingerprint.

Spread across the 500 sampled leaves: median 0.825, first decile 0.675,
22 leaves below 0.60, 65 below 0.70, 125 at or above 0.90, 24 perfect.
No leaf had to be excluded; every sampled suite was green before mutation and
survived the source round-trip. 5 of the 19,911 mutants hit the time limit.

By domain, on the deep run (pooled over the leaves sampled from each):

| domain | mutants | score |
|---|---|---|
| flight-test-operations | 240 | 0.6917 |
| flight-mechanics | 280 | 0.7000 |
| vehicle-design | 560 | 0.7250 |
| propulsion | 280 | 0.7643 |
| gnc-autonomy | 520 | 0.7712 |
| manufacturing-quality | 440 | 0.7750 |
| aerodynamics | 400 | 0.8050 |
| space-systems | 16,000 | 0.8102 |
| structures | 520 | 0.8135 |
| avionics | 320 | 0.8344 |
| cross-cutting | 160 | 0.8438 |
| systems-engineering-safety | 191 | 0.9005 |

Space systems dominates the sample because it dominates the corpus; the small
domains carry few leaves each and their figures are correspondingly loose.

### Where the holes are

| mutation family | run | survived | score |
|---|---|---|---|
| early-return | 1,229 | 11 | 0.9910 |
| boolean-negation | 4,780 | 327 | 0.9316 |
| arithmetic-swap | 2,751 | 432 | 0.8430 |
| boundary-offset | 4,110 | 808 | 0.8034 |
| comparison-swap | 2,043 | 480 | 0.7651 |
| constant-perturbation | 4,998 | 1,847 | 0.6305 |

Broken down further, the weakest kinds are a float constant nudged by 1%
(0.476), a boolean literal flipped (0.641), an integer constant moved by one
(0.660) and a constant zeroed (0.661). The strongest are an inserted early
return (0.991), a dropped `not` (0.984) and a negated `if` test (0.983).

Read plainly: the suites are excellent at noticing that a function stopped
doing its job, and much weaker at noticing that it is doing its job with the
wrong number. For a corpus of engineering calculations that is the wrong way
round, and it is the concrete thing to fix.

### A suite that could never fail, found by the score

One leaf in the deep sample, `skills/space-systems/ecss/e1002-method-analysis`,
scored **0.000** — 40 mutants applied, none killed, including a mutant that
replaced the whole body of `validate_analysis_technique` with `return None`.
No real suite lets that through, so the suite was not the explanation.

Its entry point is `unittest.main(exit=False)`. The suite runs its 31 tests,
prints `FAILED`, and exits **0**. Gate 3 decides pass/fail on the exit code
(`if ! python3 "$t"`), so that leaf's contract test can report any number of
failures and the gate will still be green. Neutering one function in a scratch
copy reproduces it exactly: `FAILED (failures=3)` on stderr, exit code 0.

Two leaves in the corpus use `exit=False`:
`space-systems/ecss/e1002-method-analysis` and
`space-systems/ecss/e1004-ref-geomag`. Neither the leaves nor the gate are this
tool's to change, but the score is what surfaced them, and the same one-line
pattern would hide any future regression in those two leaves. A mutation score
of exactly zero is worth treating as an alarm about the harness, not a verdict
on the tests.

### A worked example

`skills/aerodynamics/drag-polars/drag-polar` scores 0.95 — 38 of 40 killed.
Both survivors sit on the same line: the guard `if ar <= 0:` with its `0`
perturbed to `1`. The suite checks that an aspect ratio of `0.0` and `-4.0`
raise, and both still raise with the bound at 1, so nothing notices. Nothing in
the suite exercises `0 < ar <= 1`. That is a real, specific, one-line gap that
no test count could have pointed at.

---

## What the number is not

**It is a lower bound.** Some mutants are semantically equivalent to the
original — a tolerance constant nudged by 1% very often is — and an equivalent
mutant can never be killed by any suite, so it lands in the survivor column and
pushes the score down. Equivalence is undecidable in general and this tool makes
no attempt to detect it. Quote the score as "at least this strong", never as
"exactly this strong". The `constant-perturbation/one-percent` line is the
largest suspected source of that inflation.

**It is a sample, twice over.** 500 of 3,021 leaves, and a cap of 40 mutants
against a median catalogue of 201 sites per leaf. Both samples are seeded and
recorded. The confidence interval covers the leaf sample; it does not cover the
within-leaf mutant sample, which the cap makes small but not zero.

**The sampling unit is the leaf, not the mutant.** Mutants inside one leaf are
correlated, so a binomial interval over pooled mutants is too narrow. The report
carries three intervals and labels which to quote:

- `ci95_pooled_cluster_bootstrap_leaf_level` — resamples **leaves** with
  replacement. **This is the one to quote.**
- `ci95_pooled_wilson_mutant_level` — Wilson on the pooled mutant proportion,
  ignoring clustering. Printed only so the difference is visible.
- `ci95_mean_per_leaf_cluster_bootstrap` — the same bootstrap applied to the
  unweighted mean of per-leaf scores, which weights a small leaf and a large one
  equally.

A score with no `n` and no interval is not a measurement. The tool refuses to
print one without both.

---

## Method

1. **Enumerate the population.** A leaf is a directory holding `SKILL.md` and a
   `scripts/` directory with at least one logic module and at least one suite.
   Modules are separated by content — does the file define a `TestCase` or call
   `unittest.main` — and not by filename, because a few leaves ship a logic
   module whose name begins with `test_`.
2. **Draw a seeded sample of leaves.** The seed is a required argument; there is
   no unseeded random source anywhere in the tool. The selection, the seed, the
   population size and a fingerprint of the population all go into the report,
   and `--list-only` prints the selection without running anything.
3. **Copy the leaf out of the tree.** Every run happens in a scratch copy under
   the system temporary directory; the scorer asserts at construction that the
   scratch directory is not inside the repository. The working tree is never
   written to, and a self-test hashes the tree before and after a sweep to prove
   it.
4. **Run two controls.** The untouched copy must pass, and a copy whose logic
   module has been round-tripped through the AST unparser with no change applied
   must also pass. A leaf that fails either is excluded, with the reason
   recorded — a red suite, or one that reads its own source text, cannot give an
   honest score.
5. **Generate the catalogue, sample it, apply one mutant at a time.** Each
   mutant is exactly one change, written into a fresh copy of the logic module.
   A mutant whose unparsed text is identical to the control is discarded as a
   provable no-op rather than counted either way.
6. **Run the suite under a wall-clock limit**, capturing **both** stdout and
   stderr. The stdlib runner prints its `OK` line on stderr, so a stdout-only
   capture reads a pass as a failure. The child runs in its own process group
   and the whole group is killed on timeout, so an endless-loop mutant cannot
   hang the sweep.

Exit code zero means the mutant survived. Anything else means it was killed.
A timeout is counted as killed and also counted separately, because an endless
loop is a detected change but not an assertion. The deep run had 5 timeouts out
of 19,911.

### Mutation catalogue

| family | what it does |
|---|---|
| `comparison-swap` | `<`↔`<=`, `>`↔`>=`, `==`↔`!=`, `is`↔`is not`, `in`↔`not in` |
| `boundary-offset` | a compared bound `n` becomes `n+1` or `n-1` |
| `arithmetic-swap` | `+`↔`-`, `*`↔`/`, `//`→`*`, `%`→`*`, `**`→`*` |
| `boolean-negation` | `and`↔`or`, a `not` dropped, an `if`/`while` test negated, `True`↔`False` |
| `constant-perturbation` | a numeric literal `v` becomes `v+1`, becomes `0` (or `1` if already `0`), and for floats `v*1.01` |
| `early-return` | `return None` inserted at the top of a function body |

### Reproducibility

Mutants are addressed by index into the breadth-first AST walk, so a
specification re-applies exactly to a freshly parsed copy of the same source.
Leaf selection is seeded from the run seed alone; each leaf's mutant selection
is seeded from the run seed **and the leaf path**, so raising `--sample` does not
reshuffle the mutants an already-sampled leaf receives. Child processes run with
`PYTHONHASHSEED=0`. The report records the corpus fingerprint: if the corpus
changes, the fingerprint changes and a rerun is a new measurement, not a repeat
of the old one.

---

## Running it

```sh
# the reference sweep (about 15 s)
python3 tools/mutation/mutation_score.py --seed 20260919 --sample 40 --mutants-per-leaf 25

# the deep sweep whose number we publish (about 8 min on 10 cores)
python3 tools/mutation/mutation_score.py --seed 20260919 --sample 500 --mutants-per-leaf 40 --jobs 10

# just show which leaves a seed picks, run nothing
python3 tools/mutation/mutation_score.py --seed 20260919 --sample 500 --list-only

# re-run exactly the leaves a previous report named
python3 tools/mutation/mutation_score.py --leaves-file tools/mutation/results/run-seed20260919-n500.json

# the scorer's own suite
python3 tools/mutation/test_mutation_score.py
```

Everything is stdlib and offline. Reports land in `tools/mutation/results/` and
carry repo-relative paths only; any absolute path that appears in captured
output is scrubbed before it is written, because a report is committed and a
machine-local path is not.

### Report contents

`aggregate` carries the score, `n` at both levels, the kill/survive/timeout
counts and the three intervals. `by_operator` and `by_operator_kind` say which
kind of damage goes unnoticed. `selection` is the exact leaf list. `leaves[]`
gives the per-leaf score and, for each survivor, the family, the line and the
change — that list is the work queue for strengthening a suite.

---

## Using it to improve the corpus

A survivor is a specific, actionable defect: at this line, this change was made
and nothing complained. The highest-value work the deep run points at:

1. **Numeric constants.** Roughly a third of constant perturbations survive.
   Suites assert shape and error-raising well and exact values poorly. Pinning
   analytic anchor values (as the drag-polar leaf already does) kills these.
2. **Comparison boundaries.** 480 survivors. A suite that exercises a threshold
   only from one side cannot tell `<` from `<=`; the fix is a case on each side
   of every boundary.
3. **The weakest leaves first.** The per-leaf list is sorted; the 22 leaves under
   0.60 are where a fixed amount of test-writing buys the most strength.

Re-run at the same seed after the work and the delta is a real measurement of
improvement rather than a larger inventory of files.

## Scope

This tool reads the corpus and writes only to its own `results/` directory and
to scratch space outside the repository. It does not modify any leaf, and it is
not part of `make validate` — the deep sweep is far too slow for a per-commit
gate. It is a periodic measurement, not a gate.
