---
name: variables-acceptance-sampling
description: "Use when you must design a variables acceptance sampling plan: map the lot size and inspection level to the sample size code letter, look up the sample size and acceptability constant k, with the maximum allowable percent nonconforming M, for the required AQL from a reduced MIL-STD-414 k-method table, form the Q statistic from the specification limit, the sample mean and the sample standard deviation, and decide accept or reject by comparing Q with k, with the estimated percent nonconforming p_hat as the M-method check. Produces the code letter, sample size, acceptability constant, Q statistic, p_hat and the accept verdict for lot disposition by measurement. Trigger: variables acceptance sampling, k-method, acceptability constant, mil-std-414."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: as9100
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: as9100
  tags: [variables-acceptance-sampling, k-method, acceptability-constant, form-q-statistic, estimated-percent-nonconforming, code-letter-lot-size, aql-variables-plan]
  version: 0.1.0
  author: AeroSkills
---

# Variables Acceptance Sampling (manufacturing-quality/as9100/variables-acceptance-sampling)

Use when a lot of measured product must be accepted or rejected on the
evidence of a sampled variable inspection: the lot size fixes the sample
size code letter, the required AQL fixes the sample size n, the
acceptability constant k and the maximum allowable percent nonconforming M,
and the Q statistic formed from the specification limit, the sample mean
and the sample standard deviation decides the verdict against k. This leaf
implements a variables acceptance sampling plan model in pure Python,
stdlib only: a documented reduced reference table in the style of the
public ANSI Z1.9 and MIL-STD-414 k-method resolves the code letter, n, k
and M, and an in-leaf normal survival function resolves the estimated
percent nonconforming p_hat for the M-method check. It pairs with
acceptance-sampling in this pack, which decides lots from counts of
nonconforming units instead of measurements, and with
statistical-process-control, which watches the ongoing process with charts
over time rather than gating individual lots.

## Domain quick reference

- Scope: variables acceptance sampling decides each individual lot from the
  measured values of a single quality characteristic (normal distribution
  assumed, sigma unknown and estimated by the sample standard deviation s);
  it is not a chart-based monitoring scheme and not a count-based plan on
  nonconforming units.
- Code letter lookup: code_letter(lot_size, level) returns the sample size
  code letter from the general level II rows of the reduced table: 91-150
  E, 151-280 F, 281-500 G, 501-1200 H, 1201-3200 J, 3201-10000 K. Lot
  sizes below 91 or above 10000 have no code letter in the table.
- Plan lookup: plan_lookup(code, aql) returns {n, k, M}. Sample sizes: E
  15, F 20, G 25, H 30, J 35, K 40. k by AQL: 0.65 -> 1.75, 1.0 -> 1.62,
  1.5 -> 1.47, 2.5 -> 1.28, 4.0 -> 1.09. M pairs with the same AQL order
  per code: E 4.17/3.61/2.98/2.28/1.66, F 4.05/3.50/2.89/2.21/1.61, G
  3.97/3.43/2.83/2.16/1.58, H 3.90/3.37/2.78/2.13/1.55, J
  3.85/3.33/2.75/2.10/1.53, K 3.80/3.29/2.72/2.08/1.52. The anchor plan
  row is code H at AQL 1.0: n = 30, k = 1.62, M = 3.37.
- Q statistics: upper limit Q_u = (USL - xbar) / s and lower limit Q_l =
  (xbar - LSL) / s, computed by form_q_upper and form_q_lower.
- k-method decision: accept when Q >= k and reject when Q < k, via
  accept_verdict.
- M-method check: p_hat is the estimated percent nonconforming, 100 *
  normal_survival(Q) for an upper limit and 100 * normal_cdf(-Q) for a
  lower limit (equal values through normal symmetry); the M-method accepts
  when p_hat <= M.
- Reference: the ANSI Z1.9 / MIL-STD-414 style k-method plan structure is
  named and paraphrased only, never reproduced verbatim; AS9100 clause 8.6
  frames the product acceptance context per standards-map.yaml.
- Assumption: the reduced table embeds only the general level II code
  letter rows and the five AQL rows listed above, so levels I and III, lot
  sizes outside 91-10000, other code letters and other AQLs raise
  ValueError by design, the same convention as the attribute
  acceptance-sampling sibling.

## Workflow

1. Fix the lot size (units per lot) and the inspection level, then resolve
   the sample size code letter with code_letter(lot_size, level).
2. Fix the AQL for the measured characteristic and look up the plan with
   plan_lookup(code, aql): the sample size n, the acceptability constant k
   and the maximum allowable percent nonconforming M.
3. Measure a random sample of n units and compute the sample mean xbar and
   the sample standard deviation s.
4. Form the Q statistic for the applicable single limit with
   form_q_upper(usl, xbar, s) or form_q_lower(lsl, xbar, s).
5. Decide the k-method verdict with accept_verdict(Q, k): accept when Q >=
   k.
6. Run the M-method companion: estimated_pct_nonconforming(Q, tail)
   returns p_hat in percent, and the plan accepts by M when p_hat <= M.
7. Run the whole single-sided flow with
   variables_sampling_decision(lot_size, aql, usl_or_lsl, xbar, s), which
   returns {code, n, k, M, Q, p_hat, accept}; report those fields and
   confirm the deterministic checks with the contract test
   scripts/test_variables_acceptance_sampling.py.

## Worked example

Lot of 800 units at level II, AQL 1.0, measured characteristic with sample
mean xbar = 49.97 and sample standard deviation s = 0.12.

- Code letter: code_letter(800, "II") = "H" (band 501-1200).
- Plan: plan_lookup("H", 1.0) = {n: 30, k: 1.62, M: 3.37}.
- Upper limit USL 50.2: Q_u = (50.2 - 49.97) / 0.12 = 1.9167 (module
  output 1.916667). accept_verdict(1.9167, 1.62) = True, the lot is
  accepted.
- M-method: p_hat = 100 * normal_survival(1.9167) = 2.764 percent (module
  output 2.764015), within 0.05 percent of the 2.76 percent anchor and
  below M = 3.37, so the M-method check also accepts.
- Lower limit LSL 49.4: Q_l = (49.97 - 49.4) / 0.12 = 4.75 (module output
  4.750000), accept True; p_hat sits below 0.001 percent.
- Reject case: sample mean 50.1 against USL 50.2 gives Q = 0.8333, below k
  = 1.62, accept False.
- AQL margin identity: the same stats with a sample mean at Q = 1.50 accept
  at AQL 1.5 (k 1.47) and reject at the tighter AQL 1.0 (k 1.62) and AQL
  0.65 (k 1.75).

## Verification

- Confirm code_letter returns H at lot 800, G at 281, H at 501, J at 1201
  and K at 10000, and raises ValueError below 91, above 10000, for
  non-positive lot sizes and for levels I and III with no reduced row.
- Confirm plan_lookup("H", 1.0) returns {n: 30, k: 1.62, M: 3.37} and that
  the embedded n, k and M rows match the spec table exactly.
- Confirm form_q_upper(50.2, 49.97, 0.12) returns 1.9167 and
  form_q_lower(49.4, 49.97, 0.12) returns 4.75.
- Confirm accept_verdict accepts at Q >= k including the boundary and
  rejects below it.
- Confirm estimated_pct_nonconforming(1.9167, "upper") returns 2.76 percent
  within 0.05 percent and that the upper and lower tail forms agree for any
  Q.
- Confirm variables_sampling_decision(800, 1.0, 50.2, 49.97, 0.12) returns
  the anchor dict {code H, n 30, k 1.62, M 3.37, Q 1.9167, p_hat 2.764,
  accept True} and rejects the xbar 50.1 case.
- Confirm ValueError rejection of non-physical inputs: s <= 0, lot_size <=
  0, out-of-band lot sizes, unknown code letters, AQLs outside the table,
  unknown levels and invalid tails.
- Run the contract test offline: python3
  scripts/test_variables_acceptance_sampling.py (33 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/acceptance-sampling: attribute lot plans
  decided by counts of nonconforming units in the sample; this leaf is the
  measurement-based counterpart for the same acceptance activity.
- manufacturing-quality/as9100/statistical-process-control: chart-based
  monitoring of an ongoing process over time; this leaf gates each
  individual lot from its own sample measurements instead.
- manufacturing-quality/as9100/measurement-systems-analysis: the
  repeatability and reproducibility context that the Q statistics here
  treat as negligible measurement error.

## Pitfalls

- Treating the bands as the full standard table: the leaf embeds a
  documented reduced table with only the general level II rows (91-150 E
  through 3201-10000 K) and five AQL rows, so any other code letter, AQL,
  level or out-of-band lot size raises ValueError instead of guessing.
- Reading the limit direction from the name: variables_sampling_decision
  treats the passed limit as an upper specification limit when the limit
  value exceeds the sample mean and as a lower specification limit
  otherwise; run a two-sided check or a mean that crossed its limit by
  forming Q with form_q_upper or form_q_lower and calling accept_verdict
  directly.
- Assuming the M-method always agrees with the k-method: on this reduced
  training table the M values are fixed paired constants, so the two checks
  can disagree at moderate Q; the disposition verdict is Q versus k (spec
  convention) and p_hat versus M is the secondary estimate check. In the
  worked anchor they agree, 2.764 <= 3.37.
- Substituting a known sigma or a range-based spread: the model estimates
  sigma by the sample standard deviation s and assumes a normal
  characteristic; other spread inputs change Q and can flip the verdict.
- Feeding s = 0, the all-identical sample: the Q statistic is undefined and
  the module raises ValueError; a zero-spread sample carries no sampling
  information about the lot position.
- Reading p_hat as a count: p_hat is the estimated percent of the normal
  population beyond the limit given the sample mean and spread, not the
  count of nonconforming units found in the sample, which is the attribute
  sibling's quantity.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_variables_acceptance_sampling.py

The test covers the spec validation list: the code letter boundary truth
table (spec boundaries 281 -> G, 501 -> H, 1201 -> J plus every band edge),
the plan lookup values for every embedded code and AQL (sample sizes 15-40,
k set 1.75/1.62/1.47/1.28/1.09, M rows E, H and K), the Q forms and accept
verdict at the worked example (Q 1.9167 accept, Q 4.75 lower-limit
accept), the reject case (xbar 50.1 against USL 50.2, Q 0.833 reject), p_hat
= 2.76 percent within 0.05 percent at Q 1.9167, the AQL margin identity
(accept at a looser AQL, reject at a tighter AQL for the same stats), the
normal survival and CDF complement identities, upper and lower tail
symmetry, the M-method agreement anchor, exact dict keys, determinism, and
ValueError rejection of non-physical inputs (s <= 0, lot_size <= 0,
out-of-band lots, unknown code letter, unknown AQL, unknown level, invalid
tail).

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.6 (product
  acceptance) frames the context, and the ANSI Z1.9 / MIL-STD-414 style
  k-method plan structure is named and paraphrased as a small reduced
  training table, summary data per standards-map.yaml; no verbatim standard
  tables or text.
- compliance: STANDARDS-REF, gated: false.
