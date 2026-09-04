---
name: acceptance-sampling
description: "Use when you must design an attribute acceptance sampling plan: choose the sample size code letter from the lot size and the inspection level, look up the single-sampling plan (sample size n, accept number Ac, reject number Re) for the required AQL from a small embedded reference table, decide accept or reject from the number of nonconforming units found in the sample, and compute the operating-characteristic probability of acceptance across incoming fraction nonconforming with the binomial model. Produces the code letter, the sample size, the accept and reject numbers, the lot verdict, and the OC curve points that quantify the plan discrimination. Trigger: acceptance sampling, attribute sampling plan, aql, lot size code letter, sample size, accept number, reject number, operating characteristic curve, probability of acceptance, lot acceptance."
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
  tags: [acceptance-sampling, attribute-sampling-plan, aql-acceptance-quality-limit, lot-size-code-letter, operating-characteristic-curve, accept-reject-numbers]
  version: 0.1.0
  author: AeroSkills
---

# Attribute Acceptance Sampling (manufacturing-quality/as9100/acceptance-sampling)

Use when a lot of incoming or final product must be accepted or rejected on
the evidence of a sampled attribute inspection: the lot size fixes the
sample size code letter, the required AQL fixes the accept and reject
numbers, and the number of nonconforming units found in the sample decides
the verdict. This leaf implements an attribute acceptance-sampling plan
design and evaluation model in pure Python, stdlib only: a documented
reduced reference table in the style of ANSI/ASQ Z1.4 attribute sampling
(single sampling, normal inspection) resolves the code letter and the plan,
and the binomial model resolves the operating-characteristic (OC) curve.
It pairs with statistical-process-control in this pack, which monitors an
ongoing production process with process-behavior charts over time, and with
nonconformance-control, which handles the lots that sampling rejects.

## Domain quick reference

- Scope: attribute acceptance sampling decides each individual lot from
  counts of nonconforming units in a sample; it is not a chart-based
  monitoring scheme for a process over time.
- Lot size bands (units per lot), documented for this reduced table: small
  51-90, medium 281-500, large 1201-3200, very-large 10001-35000. A lot
  size outside these bands has no code letter in the table.
- Code letter lookup: code_letter(lot_size, inspection_level) returns the
  sample size code letter. Level II mapping: small -> F, medium -> J,
  large -> J, very-large -> L; level I medium -> F; level III medium -> K.
  Inspection levels are the general levels I, II and III.
- Single-sampling plan lookup: sampling_plan(code_letter, aql) returns
  (n, Ac, Re) with Re = Ac + 1. Anchor plan rows at AQL 1.0: code J ->
  (80, 2, 3), code H -> (50, 1, 2), code L -> (200, 5, 6). n is the sample
  size, Ac the accept number, Re the reject number.
- Decision rule: a lot is accepted when the nonconforming units found in
  the sample are at most Ac, rejected when they reach Ac + 1 = Re:
  lot_decision(nonconforming_found, plan).
- Operating characteristic: with incoming fraction nonconforming p, the
  probability of acceptance under the binomial model is
  Pa(p) = sum over d = 0..Ac of C(n, d) * p^d * (1-p)^(n-d), computed by
  oc_acceptance_probability(n, ac, p) with math.comb. oc_curve(n, ac,
  p_values) returns the (p, Pa) point list.
- OC anchors for the anchor plan (n 80, Ac 2): Pa(0.01) = 0.9534 and
  Pa(0.04) = 0.3748 (independently verified).
- Reference: ANSI/ASQ Z1.4 style attribute sampling plan selection, named
  and paraphrased only, never reproduced verbatim; AS9100 clause 8.6
  frames the product acceptance context.
- Assumption: the CODE_LETTER_TABLE ("II", "medium") cell maps to code
  letter J so that the anchor plan (lot size 500, level II, AQL 1.0)
  resolves to the worked-example plan (80, 2, 3) with its verified OC
  anchors; all other cells are as published in the engineering spec. The
  tables are reduced summary data, not the full standard tables.

## Workflow

1. Fix the lot size (units per lot) and the inspection level (I, II or
   III) and resolve the sample size code letter with code_letter.
2. Fix the AQL for the attribute being checked and look up the
   single-sampling plan with sampling_plan(code_letter, aql); the result
   is (n, Ac, Re) with Re = Ac + 1.
3. Inspect a random sample of n units and count the nonconforming units.
4. Decide the lot verdict with lot_decision(nonconforming_found, plan):
   at or below Ac the lot is accepted, at Ac + 1 it is rejected.
5. Quantify the plan discrimination with oc_curve(n, ac, p_values) across
   incoming fraction nonconforming p, and read Pa at the AQL-adjacent
   points; the curve falls from 1.0 at p = 0 toward 0 as p grows.
6. Report the code letter, the plan (n, Ac, Re), the verdict and the OC
   points, then confirm the deterministic checks with the contract test
   scripts/test_acceptance_sampling.py.

## Worked example

Lot of 500 units (medium band) inspected at level II, AQL 1.0.

- Code letter: code_letter(500, "II") = "J".
- Plan: sampling_plan("J", 1.0) = (80, 2, 3): sample n = 80, accept number
  Ac = 2, reject number Re = 3 (Re = Ac + 1).
- Sample result: 1 nonconforming unit found. lot_decision(1, (80, 2, 3))
  = "accept"; the lot is accepted.
- Sample result: 3 nonconforming units found. lot_decision(3, (80, 2, 3))
  = "reject"; the lot is rejected.
- OC anchors: oc_acceptance_probability(80, 2, 0.01) = 0.9534 (module
  output 0.953447), and oc_acceptance_probability(80, 2, 0.04) = 0.3748
  (module output 0.374788).
- OC curve points from oc_curve(80, 2, p_values): at p = 0.005, Pa =
  0.9923; at 0.01, 0.9534; at 0.02, 0.7844; at 0.04, 0.3748; at 0.08,
  0.0404; at 0.15, 0.0003. The plan passes nearly all lots near p = 0.005
  and nearly none near p = 0.08, which is the discrimination the producer
  and consumer risks trade.

## Verification

- Confirm code_letter(500, "II") returns "J" and code_letter(60, "II")
  returns "F" (small band) while code_letter(20000, "II") returns "L"
  (very-large band).
- Confirm sampling_plan("J", 1.0) returns (80, 2, 3) with Re = Ac + 1 for
  every plan row.
- Confirm lot_decision accepts at exactly Ac and rejects at Ac + 1, the
  decision identity of single sampling.
- Confirm oc_acceptance_probability(80, 2, 0.01) sits within 1e-3 of
  0.9534 and oc_acceptance_probability(80, 2, 0.04) within 1e-3 of 0.3748.
- Confirm the identities oc(p = 0) = 1.0 and oc(p = 1) = 0 for Ac < n.
- Confirm oc_curve is deterministic and preserves the input p order.
- Confirm ValueError rejection of non-physical inputs: lot_size <= 0,
  unknown inspection level, a lot size outside the documented bands, an
  unknown (code letter, AQL) pair, p outside [0, 1], a negative
  nonconforming count, and non-integer counts.
- Run the contract test offline: python3
  scripts/test_acceptance_sampling.py (35 tests, deterministic).

## Related leaves

- manufacturing-quality/as9100/statistical-process-control: chart-based
  monitoring of an ongoing process over time; this leaf gates each
  individual lot instead of watching the process run.
- manufacturing-quality/as9100/nonconformance-control: the follow-on
  handling of lots that a sampling plan rejects.
- manufacturing-quality/as9100/quality: the QMS overview that frames
  acceptance activity under AS9100 product acceptance.
- manufacturing-quality/as9100/attribute-control-charts: p-chart style
  attribute monitoring of a process, distinct from lot sampling verdicts.

## Pitfalls

- Reading the code letter from a fuller standard table: this leaf embeds a
  documented reduced reference table covering only the lot-size bands
  small 51-90, medium 281-500, large 1201-3200 and very-large 10001-35000;
  a lot size outside those bands raises ValueError instead of guessing.
- Confusing the accept number with the reject number: the verdict flips at
  Ac + 1, so with plan (80, 2, 3) a sample with 2 nonconforming units is
  still accepted and 3 rejects the lot.
- Treating the plan as a process monitor: acceptance sampling decides each
  lot from its own sample; it gives no signal about whether the process
  drifted between lots, which is the role of statistical-process-control.
- Computing the OC with the Poisson approximation by default: the model
  here is the binomial sum over d = 0..Ac with math.comb, exact for a
  random sample from a large lot at fraction nonconforming p.
- Passing the AQL as an unnormalized number: sampling_plan keys the table
  by the AQL string form, so "1.0" and 1.0 resolve to the same plan row
  while an AQL with no row, such as "4.0", raises ValueError.
- Expecting the full ANSI/ASQ Z1.4 table set: only the anchor rows listed
  above are embedded; other code letter or AQL combinations raise
  ValueError by design (the standard itself is reference-only).

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_acceptance_sampling.py

The test covers the spec validation list: the code letter truth table
across the lot size bands and inspection levels, the single-sampling plan
lookup with Re = Ac + 1, the decision truth table (Ac accepts, Ac + 1
rejects), the OC anchors 0.9534 and 0.3748 within 1e-3, the identities
oc(p = 0) = 1.0 and oc(p = 1) = 0 when Ac < n, curve ordering and
determinism, the end-to-end worked example flow, and ValueError rejection
of non-physical inputs (lot_size <= 0, unknown inspection level, lot size
outside the documented bands, unknown (code, AQL) pair, p outside [0, 1],
negative or non-integer counts).

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.6 (product
  acceptance) and the ANSI/ASQ Z1.4 style attribute sampling approach are
  named and paraphrased only, summary data per standards-map.yaml; no
  verbatim standard tables or text.
- compliance: STANDARDS-REF, gated: false.
