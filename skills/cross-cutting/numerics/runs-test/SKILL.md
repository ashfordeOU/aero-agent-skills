---
name: runs-test
description: "Use when you must run the Wald-Wolfowitz runs test: determining whether the ordering of a two-sign sequence (plus and minus signs, or 1/0 flags recoded as plus and minus) is random by counting the runs of identical signs, computing the expected number of runs and its variance under the randomness null from the two sign counts, forming the standard normal z statistic, and returning the randomness verdict against the two-sided 95 percent normal critical value. Produces the run count, expected runs, variance, standard deviation, z statistic, and the REJECT or FAIL_TO_REJECT randomness verdict. Trigger: runs-test, wald-wolfowitz runs, sequence randomness test, runs count statistic, run length pattern, nonparametric randomness, two sign sequence."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: naca-tr-824
    reference-only: true
gated: false
domain: cross-cutting
pack: numerics
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: cross-cutting
  subdomain: numerics
  tags: [runs-test, wald-wolfowitz-runs, sequence-randomness-test, runs-count-statistic, nonparametric-randomness, run-length-pattern]
  version: 0.1.0
  author: Aero Agent Skills
---

# Runs Test (cross-cutting/numerics/runs-test)

Use when the task is testing whether the ordering of a two-sign
sequence is random: a telemetered channel that flips between two
states, a test log of plus and minus deviations, or any binary record
whose sequential arrangement may carry trend or alternation structure.
This leaf implements the Wald-Wolfowitz runs test in pure Python,
stdlib only (scripts/runs_test_logic.py): it counts the maximal
consecutive same-sign blocks,
computes the expected number of runs and its variance under the null
hypothesis of randomness from the two sign counts, forms the standard
normal z statistic, and returns the randomness verdict against the
two-sided 95 percent normal critical value. It pairs with
cross-cutting/numerics/hypothesis-testing for parametric significance
tests on the same measured data and with rank-based-hypothesis-testing
for two-sample and paired rank comparisons; this leaf tests the
ordering of ONE sequence, it is not a parametric location procedure,
not a rank procedure, and not an information-content measure of a
symbol distribution.

## Domain quick reference

- Run definition: a run is a maximal consecutive block of one sign in
  the sequence; count_runs returns the number of such blocks. An
  alternating sequence maximizes the run count (runs equals length),
  a clumped sequence minimizes it (runs equals 2 for one block of each
  sign).
- Sign counts: n1 = count of plus signs, n2 = count of minus signs,
  n = n1 + n2. The caller recodes 1/0 flags to +1/-1 before calling.
- Expected runs under the null of randomness:
  E(R) = 1 + 2 n1 n2 / n.
- Variance of the run count under the null:
  Var(R) = 2 n1 n2 (2 n1 n2 - n) / (n^2 (n - 1)); the standard
  deviation is sqrt(Var(R)).
- Test statistic: z = (R - E(R)) / sqrt(Var(R)), standard normal
  under the null for moderate n.
- Verdict: REJECT randomness when |z| >= z_crit with the two-sided
  95 percent normal critical value z_crit = 1.96
  (Z_CRIT_95_TWOTAIL); otherwise FAIL_TO_REJECT. A REJECT means the
  ordering shows evidence of non-random structure (too few runs
  suggests trend or clumping, too many suggests alternation).
- Minimum data: at least 4 signs with both signs present; a
  single-sign sequence carries no ordering information.
- NACA TR-824 is named as the numerics-pack reference; the relations
  above are standard statistical methodology, summary-only.

## Workflow

1. Encode the record as a list of +1 and -1 ints; recode any 1/0
   flags to +1/-1 at the call site.
2. Count the sign totals and the run count with count_runs(signs);
   confirm both signs are present and the length is at least 4.
3. Compute the expected number of runs under the null with
   expected_runs(n1, n2) from the two sign counts.
4. Compute the variance of the run count with runs_variance(n1, n2)
   and take the square root for the standard deviation.
5. Form the z statistic as (runs - expected) / sd, or call
   runs_test(signs) directly for the full result dict {n1, n2, runs,
   expected, variance, sd, z, verdict}.
6. Read the verdict: REJECT (evidence of non-random ordering) when
   |z| >= z_crit, else FAIL_TO_REJECT; state it next to the run count
   and the z statistic, never the z alone.
7. Confirm the deterministic checks with the contract test
   scripts/test_runs_test.py.

## Worked example

Reference sequence +++++-----+++++----- (five plus, five minus, five
plus, five minus), 20 signs with n1 = n2 = 10.

- Runs: count_runs returns 4 (two plus blocks, two minus blocks,
  R = 4 against the spec anchor).
- Expected runs: E(R) = 1 + 2 * 100 / 20 = 11.000.
- Variance: Var(R) = 2 * 100 * (200 - 20) / (400 * 19) =
  36000 / 7600 = 4.7368; sd = 2.1764.
- z statistic: z = (4 - 11) / 2.1764 = -3.216 (module value
  -3.2163), |z| = 3.216 >= 1.96.
- Verdict: REJECT randomness. Four runs where 11 are expected is far
  too few: the sequence is clumped into long same-sign blocks, clear
  evidence of non-random ordering.

## Verification

- Confirm count_runs(ANCHOR) returns 4 and that the alternating
  sequence of length 10 with 5/5 signs returns 10 (the maximum
  possible run count).
- Confirm expected_runs(10, 10) returns 11.000 within 1e-9.
- Confirm runs_variance(10, 10) returns 4.7368 within 1e-4 and its
  square root 2.1764 within 1e-4.
- Confirm runs_test(ANCHOR)["z"] is -3.216 within 1e-3 with verdict
  REJECT.
- Confirm the random-looking fixture ++--++--++-- (n1 = n2 = 6, six
  runs, z = -0.606) gives FAIL_TO_REJECT.
- Confirm ValueError on fewer than 4 signs, any sign other than +1 or
  -1, a single-sign sequence, non-positive sign counts, and a total
  count below 4 in the variance function.
- Run the contract test offline: python3
  scripts/test_runs_test.py (32 tests, deterministic).

## Related leaves

- cross-cutting/numerics/hypothesis-testing: the parametric
  significance-test layer for measured-data group comparisons, used
  when the question is about location rather than ordering.
- cross-cutting/numerics/rank-based-hypothesis-testing: two-sample
  and paired comparisons built on ranks, the neighboring nonparametric
  procedures for separate samples.
- cross-cutting/numerics/descriptive-statistics: summary measures and
  scatter characterization of the same measured sequences before the
  ordering question is posed.

## Pitfalls

- Reading the verdict from the z sign alone: both tails matter. Too
  few runs (negative z, clumping or trend) AND too many runs (positive
  z, alternation) are evidence of non-random ordering, so the verdict
  always compares |z| with the critical value.
- Counting sign changes instead of runs: a sequence with R runs has
  exactly R - 1 transitions; quoting the transition count shifts the
  statistic by one and breaks the expectation comparison.
- Feeding 1/0 flags straight in: every element must be +1 or -1, so a
  0 raises ValueError; recode flags at the call site before running
  the test.
- Expecting a proportion test: the null here is randomness of the
  ordering GIVEN the two sign counts, not equality of the sign
  proportions; count imbalance is held fixed by conditioning on n1 and
  n2.
- Using a one-sided critical value: the two-sided 95 percent normal
  critical value is 1.96; a one-sided 1.645 threshold rejects far more
  easily and is not what this leaf's verdict implements.
- Ignoring the normal approximation's data floor: the procedure needs
  both signs and a total of at least 4 signs; smaller or single-sign
  records are rejected with ValueError instead of returning a
  meaningless statistic.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_runs_test.py

The test covers the worked-example anchors (R = 4, E = 11.000 within
1e-9, Var = 4.7368 and sd = 2.1764 within 1e-4, z = -3.216 within
1e-3, verdict REJECT), the alternating-sequence maximum run count, the
expected-runs and variance closed forms on small balanced inputs, the
fail-to-reject random-looking fixture (++--++--++--), the verdict
boundary semantics at the critical value (|z| >= z_crit rejects),
strict and relaxed critical-value overrides, the exact result dict
key set, determinism across calls, and ValueError rejection of every
non-physical input (short, single-sign, or invalid-sign sequences;
non-positive sign counts; total below 4).

## Compliance

- Standards referenced, not reproduced: NACA TR-824 is named as the
  numerics-pack reference; the Wald-Wolfowitz relations above are
  standard statistical methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
