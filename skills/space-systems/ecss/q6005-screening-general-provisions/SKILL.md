---
name: q6005-screening-general-provisions
description: "Evaluate the baseline provisions that govern how a hybrid microcircuit screening sequence is planned, applied and recorded, under ECSS-Q-ST-60-05 clause 10.3.1. Use when a screening programme needs grading above the level of its individual steps: test that the sequence reached every delivered unit, that it was written and approved beforehand, that each reject criterion was fixed before the data arrived and that results were kept per unit, weigh the batch against its screening reject allowance and re-screen limit, and return the provision index with one verdict. Trigger: ecss, q-st-60-05, hybrid-screening-provisions, hundred-percent-screening-application, hybrid-screening-reject-allowance, hybrid-rescreen-cycle-limit, per-unit-screening-records, hybrid-screening-provision-verdict."
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
  tags: [ecss, q-st-60-hybrid-scope, q-st-60-05, q6005-screening-general-provisions, hybrid-screening-provisions, hundred-percent-screening-application, hybrid-screening-reject-allowance, hybrid-rescreen-cycle-limit, per-unit-screening-records, hybrid-screening-provision-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Screening General Provisions (space-systems/ecss/q6005-screening-general-provisions)

Use when the task is clause 10.3.1 of ECSS-Q-ST-60-05: the rules that sit
above the individual screening steps and decide whether a screening
programme is one at all. The order the steps run in is graded separately
under the screening sequence, and each step has a leaf of its own.

## Domain quick reference

- Screening reaches every unit offered for delivery. A sequence run on a
  sample is a lot test wearing the wrong name, and the units it never touched
  carry none of its evidence, however good the sample looked.
- The sequence is written and approved before it runs. A sequence agreed on
  the shop floor cannot be audited afterwards, because there is nothing to
  audit it against.
- Each step carries its reject criterion in advance. A criterion settled once
  the data is in is a decision about this batch, not a screen.
- The result is kept per unit, not per batch. A batch-level pass hides which
  unit drifted, and the drift is the reason the step was run.
- Units screening removes are counted against an allowance. A batch that
  loses more than the allowance is not a good batch with some bad units in
  it: the population is suspect and the survivors inherit the doubt.
- A batch that lands exactly on the allowance is inside it. The comparison
  carries a tolerance rather than a bare inequality, because the rate is a
  ratio and the bound is a decision.
- Re-screening is bounded. Each pass consumes life the unit will not have in
  flight, so a batch re-screened past the limit is disqualified by the
  screening rather than rescued by it.
- The provision index ranks what is outstanding. A missing mandatory
  provision, a reject rate over the allowance, a re-screen past the limit or
  a batch with no survivor decides the outcome on its own, at any index.

## Workflow

1. Take the batch identifier and size, the units screening removed, and the
   re-screen passes the batch has already had.
2. Grade each governing provision from satisfied and evidenced down to not
   satisfied, and read a provision nobody mentioned as not satisfied rather
   than as assumed.
3. Mark the four provisions without which there is no programme — full
   application, an approved written sequence, criteria fixed beforehand, and
   per-unit records — and note any that fall short.
4. Compute the reject fraction over the batch and compare it with the
   allowance, tolerance included, so an exact landing counts as inside.
5. Compare the re-screen passes with the permitted limit.
6. Count the survivors and treat a batch with none as a yield rejection
   rather than an empty success.
7. Take the weighted credit over total weight as the provision index.
8. Name the verdict: rejected on yield when the allowance, the re-screen
   limit or the survivors decide it, not satisfied on a missing mandatory
   provision or a low index, satisfied with open actions when findings
   remain, satisfied only when none do.

## Pitfalls

- Reading a high sample yield as a screened batch. The screen covers the
  units it touched, and the delivery covers all of them.
- Approving the procedure after the run, from the run. The record then
  describes what happened rather than what was required.
- Moving a reject limit once the data is in. Every batch passes a criterion
  written to fit it.
- Keeping only the batch summary. The per-unit numbers are what a later
  failure investigation needs, and they cannot be reconstructed.
- Re-screening a marginal batch until it passes. The passes are stress the
  flight units have already spent, and the limit exists for that reason.
- Treating a batch exactly on the allowance as over it. The bound is a
  decision and the rate is a ratio; a bare inequality turns rounding into a
  rejection.
- Letting a strong provision set carry a batch that lost a third of itself.
  The index grades the programme; the allowance grades the population.

## Behavior contract (gate 3)

The provision catalogue and weights, mandatory-provision rule, provision
grading, provision index, reject-fraction computation, allowance comparison
with its tolerance, re-screen limit, survivor count and programme verdict are
exercised by the gate 3 contract test:
scripts/test_q6005_screening_general_provisions.py against
scripts/q6005_screening_general_provisions_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_q6005_screening_general_provisions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
