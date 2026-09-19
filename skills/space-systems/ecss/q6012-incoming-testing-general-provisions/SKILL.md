---
name: q6012-incoming-testing-general-provisions
description: "Size the receipt testing arrangement for an arriving die lot and dispose of the lot on what the sample shows, per ECSS-Q-ST-60-12C clause 10.3.1: band the lot size to a code letter, draw the sample for the inspection level, derive the acceptance number by whole-number arithmetic, adjust it for tightened or reduced severity, accept or reject against the observed defectives, and apply the switching rules that set the severity for the next lot. Refuses a defective count larger than its own sample. Use when arriving material needs a sampling and disposition basis. Trigger: ecss, q-st-60-12c-clause-10-3-1, die-lot-receipt-sampling-plan, incoming-lot-acceptance-number, tightened-reduced-inspection-switching, die-lot-accept-reject-disposition, hundred-percent-receipt-inspection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, q-st-60-12-incoming-testing-general-provisions, q6012-incoming-testing-general-provisions, die-lot-receipt-sampling-plan, incoming-lot-acceptance-number, tightened-reduced-inspection-switching, die-lot-accept-reject-disposition, hundred-percent-receipt-inspection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Incoming Testing General Provisions (space-systems/ecss/q6012-incoming-testing-general-provisions)

Use when arriving die material has to be receipt tested and the baseline
arrangement has to be set before anyone picks up a probe: how much of the lot
is drawn, on what acceptance basis, what happens to the lot on the result,
and how the arrangement moves as the supplier's record builds.

## Domain quick reference

- The sample size comes from a size band, not from the lot size itself. A lot
  of three hundred and a lot of twelve hundred are drawn identically, and a
  lot of thirteen hundred is not; scaling the draw smoothly with lot size
  looks more principled and gives a different plan from the tabled one.
- The acceptance number is derived from whole permitted defectives per
  thousand and integer division. That is deliberate: the lot that lands
  exactly on the boundary is the one that matters, and a floating-point
  acceptance number is how the same lot gets two answers on two machines.
- A sample that reaches the lot size is not a sample. Small lots collapse to
  one hundred percent inspection, and reporting that as a sampling plan hides
  that there is no statistical inference left in the result at all.
- Accepting a lot is not the same as the lot being defect free. A plan with a
  non-zero acceptance number accepts lots with known defectives in the
  sample, and the material still goes on to screening; a zero acceptance
  number is called out precisely because it removes that latitude.
- Severity is the memory of the arrangement. Two rejections inside the recent
  window tighten the next lot, a long clean run reduces it, and a single
  rejection ends reduced inspection immediately. Without switching, a
  supplier's record has no effect on how their next delivery is treated.

## Workflow

1. Band the lot size and take its code letter, refusing a lot size that is
   not a whole positive count.
2. Draw the tabled sample size for that code letter at the chosen inspection
   level.
3. Derive the acceptance number from the sample size and the acceptance
   quality in defectives per thousand, by integer division.
4. Apply severity: tightened lowers the acceptance number without floor
   below zero, reduced halves the draw with a floor under it, normal leaves
   both as tabled.
5. Cap the sample at the lot size, recompute the acceptance number when it
   caps, and mark the plan as one hundred percent inspection.
6. Dispose of the lot against the observed defectives, refusing a count
   larger than the sample it came from, then apply the switching rules to say
   what severity the next lot is inspected under.

## Pitfalls

- Sampling a fixed percentage of the lot. It over-tests small lots into
  uselessness and under-tests large ones, and it is not the plan the size
  bands describe.
- Computing the acceptance number in floating point. The lot that sits on the
  boundary is the whole point of the number, and it is the one a float
  computation decides differently on different platforms.
- Reporting a capped sample as a sampling plan. Once the sample is the lot,
  the acceptance number is a count of defects in the delivery, not an
  inference about it, and the report should say so.
- Treating acceptance as a clean bill. A plan that permits two defectives
  accepts lots that contain them; downstream screening is not optional
  because receipt testing passed.
- Ignoring the supplier's record. Without switching, a supplier who has had
  two lots rejected is inspected exactly as lightly as one who has never had
  a finding.

## Behavior contract (gate 3)

The size banding, tabled sample draw, integer acceptance number, severity
adjustment, the hundred-percent cap with its recomputed acceptance number,
the accept-or-reject disposition with its defective-count refusal, and the
tightened and reduced switching rules are exercised by the gate 3 contract
test: scripts/test_q6012_incoming_testing_general_provisions.py against
scripts/q6012_incoming_testing_general_provisions_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q6012_incoming_testing_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
