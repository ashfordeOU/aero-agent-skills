---
name: cmh17-allowables
description: "Compute composite material design allowables per the CMH-17 method: determine A-basis and B-basis values from coupon test data using the one-sided normal tolerance k-factor approximation, pool coupon batches across environments to enlarge the effective data set, and apply knockdown factors for environmental conditioning, barely visible impact damage, and open hole features to derive laminate-level allowables from lamina allowables. Produce the lamina and laminate allowable table with basis designation and the confidence and content statement, and validate the counts against the minimums. Use when the task is composite allowables, basis values, coupon pooling, or laminate knockdown factors for polymer matrix composites. Trigger: composite allowables, cmh-17, a-basis, b-basis, tolerance k-factors, coupon pooling, laminate allowables, knockdown factors, environmental conditioning, open hole."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: mmpsd
    reference-only: true
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [cmh-17-allowables, composite-allowables, a-basis, b-basis, k-factor, tolerance-k-factors, pooling, laminate-allowables, knockdown-factors, environmental-conditioning, open-hole]
  version: 0.1.0
  author: Aero Agent Skills
---

# CMH-17 Composite Allowables (structures/composites/cmh17-allowables)

Use when the task is statistically based composite material design
allowables: A-basis and B-basis values from coupon test samples,
one-sided normal tolerance k-factors, coupon pooling across batches
and environments, and laminate-level allowables derived from lamina
allowables with knockdown factors. This leaf is the composite
counterpart of structures/materials/mmpsd-allowables (which treats
metals); it is also distinct from
structures/composites/laminate-stiffness, which computes the elastic
stiffness matrix rather than strength design values.

## Domain quick reference

- A-basis: 95% confidence that 99% of the population exceeds the
  value; B-basis: 95% confidence that 90% exceeds the value.
- One-sided normal tolerance k-factor (Owen/Odeh approximation):
  z_c = 1.6448536269514722 (0.95 confidence); z_p = 2.3263478740408408
  for A-basis content or 1.2815515655446004 for B-basis;
  a = 1 - z_c^2/(2(n-1)); b = z_p^2 - z_c^2/n;
  k = (z_p + sqrt(z_p^2 - a*b))/a.
- Allowable = sample mean - k * sample standard deviation.
- Common minimum samples: 10 for A-basis, 6 for B-basis; verify
  against the current CMH-17 edition.
- Pooling: combine coupon batches (batches, environments) into one
  effective sample; the pooled mean is the overall mean and the pooled
  standard deviation is the within-batch pooled value
  (sum((n_i - 1) s_i^2) / sum(n_i - 1))^0.5. The larger effective
  sample count lowers the k-factor.
- Knockdown factors: environmental conditioning (hot/wet), barely
  visible impact damage (BVID), and open hole features reduce the
  lamina allowable to the laminate allowable; the combined factor is
  the product of the individual factors, each in (0, 1].
- Where strength data are Weibull distributed, the content quantile
  eta * (-ln(p))^(1/beta) from a two-parameter Weibull MLE fit is used
  in place of the normal tolerance method.
- CMH-17 is the Composite Materials Handbook (proprietary, published
  by SAE); name and paraphrase only, per standards-map.yaml and
  research/briefs/06-legal-export-control.md. FAR-25 is the public
  airworthiness context for transport category strength substantiation.

## Workflow

1. Gather the coupon test sample per material, batch, environment,
   and property of interest; record the sample count.
2. Check the sample count against the basis minimum with
   check_sample_count.
3. For a single batch, compute the k-factor with
   k_factor_one_sided and the allowable with allowable_from_sample.
4. For pooled data, call pooled_allowable with the batch list to get
   the pooled mean, pooled standard deviation, effective n, k-factor,
   and pooled allowable.
5. For Weibull-distributed strength data, fit the two-parameter
   Weibull with weibull_mle and derive the content quantile or basis
   value with weibull_content_value / weibull_basis.
6. Apply the environmental, BVID, and open hole knockdown factors to
   each lamina allowable with knockdown to get the laminate
   allowable.
7. Assemble the lamina and laminate allowable table with
   build_allowable_table; each row carries the basis designation and
   the confidence/content statement from basis_statement.
8. Confirm the deterministic checks with the contract test
   scripts/test_cmh17_allowables.py.

## Basis value statistics

The A- and B-basis design values follow the standard one-sided normal
tolerance approach: the allowable sits k sample standard deviations
below the sample mean. Because the k-factor grows as the sample
shrinks, small coupon samples produce conservative (low) allowables;
meeting the minimum sample count is the first validation step.

Pooling is the composite-specific refinement: coupon batches from
different panels, batches, or environments are combined into one
effective sample. The pooled standard deviation weights each batch by
its degrees of freedom, so batch-to-batch scatter is retained without
inflating the estimate by between-batch spread, and the larger
effective n reduces the k-factor and raises the allowable relative to
any single batch alone.

For strength distributions that are not normal, the two-parameter
Weibull fit provides the content quantile: with shape beta and scale
eta from the MLE, the value exceeded by fraction p of the population
is eta * (-ln(p))^(1/beta). The sample-size shrink (1 - 1/n) applied
in weibull_basis is a conservative engineering adjustment; the
authoritative confidence factors are the published CMH-17 values
(referenced, not reproduced).

## Knockdown model

Laminate allowables are derived from lamina allowables by multiplying
the lamina value by each applicable knockdown factor, in (0, 1]:

- environmental conditioning factor: hot/wet conditioned strength
  reduction (for example 0.9 for a wet elevated temperature case);
- barely visible impact damage (BVID) factor: compression and shear
  strength reduction after impact (for example 0.85 for a
  compression-dominated case);
- open hole factor: strength reduction at fastener holes (for example
  0.95 for an open hole tension case).

Combined knockdown = env * bvid * hole; laminate allowable = lamina
allowable * combined. Each factor must be strictly between 0 and 1;
unit factors leave the allowable unchanged.

## Worked example

A tension lamina coupon sample of 7 values is
[100, 102, 104, 106, 108, 110, 112] MPa. For B-basis:

- n = 7, mean = 106.0, sample standard deviation about 4.32.
- k_factor_one_sided(7, "B") is between 2.0 and 2.8; the allowable is
  mean - k * sd, positive and below the sample mean.
- With the environmental factor 0.9, BVID factor 0.85, and open hole
  factor 0.95, the combined knockdown is 0.9 * 0.85 * 0.95 = 0.72675
  and the laminate allowable is about 27% below the lamina allowable.
- The table row carries the statement "B-basis: 95% confidence, 90%
  content".

If the 7-value sample is split into batches of 4 and 3 across two
environments, pooling combines them into one effective sample of 7:
the pooled standard deviation stays within the batch spreads, the
k-factor is driven by the total n, and the pooled allowable is
computed from the overall mean.


## Pitfalls

- Using the allowable below the minimum sample count: A-basis needs
  about 10 coupons and B-basis about 6 (verify against the current
  CMH-17 edition); smaller samples grow the k-factor and the value
  loses its statistical meaning.
- Pooling when batches disagree: the pooled standard deviation is the
  within-batch value sum((n_i - 1) s_i^2) / sum(n_i - 1), so it
  retains batch scatter only if the batches are genuinely combinable;
  pooling between-batch spread inflates the estimate.
- Applying the normal tolerance method to Weibull strength data: for
  Weibull-distributed properties use the two-parameter MLE content
  quantile eta * (-ln(p))^(1/beta), not the normal k-factor.
- Multiplying knockdown factors outside (0, 1]: each factor must be
  strictly between 0 and 1; a factor at or above 1 (or at or below 0)
  breaks the combined knockdown 0.9 * 0.85 * 0.95 = 0.72675 chain.
- Confusing the basis statements: A-basis is 95% confidence / 99%
  content and B-basis is 95% confidence / 90% content; the table row
  statement must match the requested basis.
- Forgetting this is lamina-to-laminate: the knockdown path derives
  laminate allowables from lamina allowables; the elastic stiffness
  side (not strength design values) belongs to laminate-stiffness,
  and the metal counterpart is materials/mmpsd-allowables.
## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_cmh17_allowables.py

The test covers the k-factor bands and monotonicity, minimum sample
counts, allowables below the sample mean, pooling behavior (k shrinks
with effective n, pooled sd within batch spreads), Weibull content
values and basis values, knockdown reduction, the allowable table
builder, and invalid-input edge cases.

## Compliance

- Standards referenced, not reproduced: CMH-17 (proprietary, SAE
  publication) name + paraphrase only; mmpsd and far-25 resolve in
  standards-map.yaml, both reference-only.
- compliance: STANDARDS-REF, gated: false.
