---
name: q6012-mmic-design-review-process
description: "Evaluate an MMIC design-review programme before fabrication release. Use when the question is whether the microwave circuit design cleared every formal checkpoint ECSS-Q-ST-60-12C clause 7.3 expects, not merely whether reviews happened: normalise the declared checkpoints into canonical gate order, name the mandatory gates never held, detect a gate held out of sequence, measure the schedule slip against the planned day, accumulate the action-item closure ratio over the held gates, and check the fabrication release day clears the last gate plus its quiet period. Trigger: ecss, q-st-60-12c-clause-7-3, mmic-design-review-programme, mmic-pre-fabrication-release-gate, mmic-review-checkpoint-sequence, mmic-review-action-closure-ratio, mmic-review-schedule-slip."
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
  tags: [ecss, q-st-60-12-mmic-scope, q6012-mmic-design-review-process, mmic-design-review-programme, mmic-pre-fabrication-release-gate, mmic-review-checkpoint-sequence, mmic-review-action-closure-ratio, mmic-review-schedule-slip]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS MMIC — Design Review Process (space-systems/ecss/q6012-mmic-design-review-process)

Use when the task is the clause 7.3 programme question of ECSS-Q-ST-60-12C:
a microwave monolithic circuit is approaching fabrication release and the
question is whether the formal checkpoints that examine the design were
actually walked through, in order, with their actions closed — not whether
review meetings appear somewhere in the schedule.

## Domain quick reference

- Clause 7.3 is a gate sequence, not a single event. The design is examined
  at requirements, architecture, detailed design and layout checkpoints, and
  again at the pre-release gate that authorises the mask set. Each gate
  depends on the one before it, so the order is part of the requirement.
- A gate that was planned is not a gate that was held. A programme listing
  five checkpoints with four held days has one open gate, and the correct
  reading of the fifth is "never held", not "assumed closed by the schedule".
- Holding a gate out of order is a real defect, not a bookkeeping quirk. A
  layout review held before the detailed-design review it depends on examined
  a layout whose schematic baseline had not yet been agreed, so both gates
  have to be re-walked rather than reordered on paper.
- The output of a gate is its action list. The programme's readiness is
  therefore a closure ratio over the actions raised at the gates that were
  held; actions raised at a gate that never happened do not exist, and a
  record claiming them is an input error.
- Fabrication release is a separate day from the last review day. A quiet
  period between the two is what lets the final actions be dispositioned and
  the released data package be assembled, so a release landing inside that
  window is a finding even when every gate was held.
- Schedule slip is reported, not gated. A gate held late is information the
  programme owner needs; it does not by itself block release, and conflating
  the two hides the gates that genuinely do.

## Workflow

1. Normalise the declared programme: refuse an unknown checkpoint key, a
   duplicate entry, a non-integer or negative day, and a record closing more
   actions than it raised or raising actions at a gate never held.
2. Sort the records into canonical gate order so the sequence check reads
   dependency order rather than the order the entries were typed in.
3. Name every mandatory gate that is absent or planned-but-unheld. A gate
   explicitly marked non-mandatory and unheld is not a finding.
4. Walk the held gates in canonical order and flag any pair whose held days
   run backwards. Two gates held the same day are combined, not out of order.
5. Compute the action closure ratio over the held gates and the coverage
   fraction over the mandatory ones, plus the worst positive schedule slip.
6. Compare the closure ratio with the required value, absorbing floating-point
   representation error at the boundary with a named tolerance rather than by
   relaxing the required ratio.
7. Decide release: every mandatory gate held, no sequence violation, closure
   ratio met, and the release day at or after the last gate plus the quiet
   period. Report each failed condition as its own finding.

## Pitfalls

- Reading a planned checkpoint as a held one. The planned day says what the
  schedule intended; only a held day is evidence the design was examined, and
  a programme graded on planned days passes every gate it never ran.
- Reordering an out-of-sequence gate in the record instead of re-walking it. A
  gate held early examined a baseline that did not exist yet; moving its row
  in the table changes the report, not the evidence.
- Gating on schedule slip. Slip is reported so the programme owner can act on
  it; treating a late gate as a failed gate buries the checkpoints that were
  genuinely skipped under a list of dates.
- Counting actions raised at a gate that never happened. That inflates both
  numerator and denominator of the closure ratio and can make an incomplete
  programme look better closed than a complete one.
- Releasing on the last review day. The quiet period is where the residual
  actions are dispositioned and the data package frozen; a same-day release
  means the package that went to fabrication is not the one the gate saw.
- Widening the required closure ratio to make an exact-equality case pass. An
  equality at the limit is a representation question, handled by the tolerance
  inside the comparison; the required value stays as specified.

## Behavior contract (gate 3)

The checkpoint validation, canonical ordering, missing-gate detection,
sequence check, slip and closure-ratio computation and the release verdict are
exercised by the gate 3 contract test:
scripts/test_q6012_mmic_design_review_process.py against
scripts/q6012_mmic_design_review_process_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6012_mmic_design_review_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
