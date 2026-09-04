# Wave-36 leaf spec: runs-test (cross-cutting, numerics pack)

- Path: skills/cross-cutting/numerics/runs-test/
- Pack: numerics. Closest siblings: hypothesis-testing (parametric
  t/Welch/ANOVA/chi-square), rank-based-hypothesis-testing (Wilcoxon/
  Mann-Whitney/signed-rank/sign), descriptive-statistics, information-
  entropy. Whole-tree grep: "runs test|Wald-Wolfowitz|randomness test"
  = 0 hits across all skills. ZERO owners. NOTE (wave-35/36 honesty):
  this is a standard nonparametric randomness test in the SAME family as
  the two hypothesis-testing siblings; it is NOT generic-math padding
  (it has a distinct claim: testing sequence randomness by runs), and
  the numerics pack already hosts two hypothesis-test siblings.
- Standards id: naca-tr-824 (pack convention for numerics leaves; the
  normal-approximation convention follows the pack's statistical
  convention). Ledger Standard: naca-tr-824.
- Family: cross-cutting

## Claim

Run the Wald-Wolfowitz runs test on a binary sequence at the conceptual
level: count the number of runs of identical signs, compute the expected
number of runs and its variance under the null hypothesis of randomness
from the two sign counts, form the standard normal z statistic with the
continuity-corrected or uncorrected form, and return the verdict against
the two-sided 95 percent normal critical value. Produces the run count,
the expected runs, the variance and standard deviation, the z statistic
and a randomness verdict (REJECT randomness when |z| exceeds the
critical value).

Does NOT do: parametric location tests (hypothesis-testing); Wilcoxon/
Mann-Whitney/signed-rank tests (rank-based-hypothesis-testing); outlier
detection (descriptive-statistics); entropy measures
(information-entropy).

## Model (implement exactly)

Module constants:
- Z_CRIT_95_TWOTAIL = 1.96.

Conventions: input sequence is a list of +1 / -1 ints (or 1/0 encoded
as +1/-1 by the caller); a run is a maximal consecutive block of one
sign. n1 = count of +1, n2 = count of -1, n = n1 + n2. Under the null:
E(R) = 1 + 2 n1 n2 / n; Var(R) = 2 n1 n2 (2 n1 n2 - n) / (n^2 (n-1)).
z = (R - E(R)) / sqrt(Var(R)). Verdict: REJECT (evidence of non-random
ordering) when |z| >= 1.96, else FAIL_TO_REJECT.

Functions (pure stdlib):
- count_runs(signs) -> int. ValueErrors: length < 4; any sign not in
  (+1, -1); all same sign (single sign) -> ValueError.
- expected_runs(n1, n2) -> float = 1 + 2 n1 n2/(n1+n2). ValueErrors:
  n1 <= 0 or n2 <= 0.
- runs_variance(n1, n2) -> float = 2 n1 n2 (2 n1 n2 - n)/(n^2 (n-1)).
  ValueErrors: n1 <= 0 or n2 <= 0; n < 4.
- runs_test(signs, z_crit = Z_CRIT_95_TWOTAIL) -> dict {n1, n2, runs,
  expected, variance, sd, z, verdict} with verdict REJECT when
  abs(z) >= z_crit else FAIL_TO_REJECT. ValueErrors as above.

Identity to test: expected runs for n1 == n2 == 10 is 11; the anchor
fixture's z is -3.216; alternating sequence of length 10 (5/5) has
runs == 10 (max possible).

## Worked example

Reference sequence: +++++-----+++++----- (five plus, five minus,
five plus, five minus).

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- n1 = 10, n2 = 10, runs R = 4.
- E(R) = 1 + 2*100/20 = 11.000.
- Var(R) = 2*100*(200-20)/(400*19) = 36000/7600 = 4.7368; sd = 2.1764.
- z = (4 - 11)/2.1764 = -3.216; |z| = 3.216 >= 1.96 -> REJECT
  randomness.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs.

## Validation list (contract test must include)

- ValueError: length < 4; non +/- sign; single-sign sequence.
- Runs count: anchor R == 4; alternating 10 signs -> 10.
- Expected: n1=n2=10 -> 11.000 within 1e-9.
- Variance: 4.7368 within 1e-4; sd 2.1764 within 1e-4.
- z: -3.216 within 1e-3; verdict REJECT.
- A random-looking fixture (e.g. ++--++--++--) with |z| < 1.96 ->
  FAIL_TO_REJECT.
- Determinism; dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave36-runs-test.yaml)

Query 1 (copy verbatim):
  "apply the runs test to a plus minus sequence to test whether the ordering is random"
  intent: "cross-cutting; Wald-Wolfowitz runs test for sequence randomness"
  expected_skill: "cross-cutting/numerics/runs-test"
Query 2 (copy verbatim):
  "compute the expected number of runs and the z statistic for a two sign sequence under the randomness null"
  intent: "cross-cutting; runs expectation variance and z statistic"
  expected_skill: "cross-cutting/numerics/runs-test"
Task ids: w36-runs-test-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must run the Wald-Wolfowitz runs
test:" and include the outputs in the Claim. First tag: runs-test.
Additional tags ONLY: wald-wolfowitz-runs, sequence-randomness-test,
runs-count-statistic, nonparametric-randomness, run-length-pattern.
NEVER single generic words (runs, test, sequence, randomness, sign,
pattern, statistic, hypothesis). 50-150 words, <=1000 chars, no em
dash, no "classified", action verb present.

FORBIDDEN TOKENS (belong to siblings): t test, welch, anova, chi
square (hypothesis-testing); wilcoxon, mann whitney, signed rank
(rank-based-hypothesis-testing); shannon, entropy (information-
entropy); outlier (descriptive-statistics).
