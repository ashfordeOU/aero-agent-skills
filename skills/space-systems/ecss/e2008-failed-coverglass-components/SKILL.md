---
name: e2008-failed-coverglass-components
description: "Use when inspection findings have to become delivery status. Determine the status ECSS-E-ST-20-08C clause 8.8.2 gives a coverglass showing any mode the preceding failure criteria list: treat one standing mode as enough, hold the status on the individual piece rather than on its batch or its sample group, keep a piece whose inspection is unfinished undetermined instead of deliverable, refuse a retest clearance the policy does not admit or that names no authority, demand a segregation record and a non-conformance reference before a failed piece counts as handled, and take the failed pieces out of the deliverable count. Trigger: ecss, coverglass-failed-component-status, coverglass-failure-mode-disposition, coverglass-segregation-record, coverglass-nonconformance-reference, coverglass-deliverable-population-exclusion, coverglass-undetermined-inspection-status."
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
  tags: [ecss, e-st-20-08-coverglass-scope, e2008-failed-coverglass-components, e-st-20-08c-clause-8-8-2, coverglass-failed-component-status, coverglass-failure-mode-disposition, coverglass-segregation-record, coverglass-nonconformance-reference, coverglass-deliverable-population-exclusion, coverglass-undetermined-inspection-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic -- Failed Coverglass Components (space-systems/ecss/e2008-failed-coverglass-components)

Use when the task is clause 8.8.2 of ECSS-E-ST-20-08C: the preceding criteria
say what a failure mode is, and this clause says what a piece showing one
becomes. It is a failed component, and a failed component is not part of what
is delivered. This leaf reads the inspection outcome for each offered piece
and returns the status, the evidence that status owes, and the deliverable
count that survives.

## Domain quick reference

- One standing mode is enough. Modes do not vote and severity does not
  dilute, so a piece carrying a single listed mode takes the same status as a
  piece carrying four. What differs is the cause list, not the word.
- The status is per piece. It attaches to the individual coverglass, not to
  the batch it came from and not to the sample group it was drawn into, so a
  batch that passed its sampling still contains failed components by name.
- Undetermined is a third word and it has to stay a third word. A piece whose
  inspection is unfinished is not deliverable and not failed; collapsing it
  into either arm converts absent evidence into a decision nobody made.
- Status without segregation is a word in a report. A failed component needs
  a segregation record and a non-conformance reference or nothing on the
  bench keeps it out of the next delivery, which is exactly how a failed
  piece walks back into a shipment.
- Retest does not quietly restore a piece. A clearance stands only where the
  policy in force admits it and a clearing authority is named, and clearing a
  mode that was never observed is a data defect rather than good news.
- The deliverable count is derived, never declared. It is what is left once
  the failed pieces are removed, so a count carried over from the offered
  quantity is wrong by exactly the number that matters.
- A status record for a piece the batch does not offer is not a typo to
  correct. It may describe another batch entirely, and rewriting the
  identifier destroys the only evidence that it did.

## Workflow

1. Validate the status policy: whether a segregation record and a
   non-conformance reference are demanded, whether a retest clearance is
   admitted at all, and whether an undetermined piece may still be counted
   into the delivery.
2. Read each piece record, refuse a mode outside the recognised set rather
   than dropping it, and collapse repeated modes to one.
3. Apply clearance only where the policy admits it and an authority is named,
   and reject a clearance naming a mode the inspection never raised.
4. Give the piece its status: failed when any mode still stands, undetermined
   when the inspection is unfinished, deliverable otherwise. A standing mode
   outranks an unfinished inspection.
5. For a failed piece, name the missing evidence rather than assuming the
   paperwork exists, and mark its status incomplete until it is there.
6. Sweep the offered population: an offered piece with no record at all is
   undetermined, and a record for a piece the batch does not offer is
   reported rather than absorbed.
7. Group the pieces by status, take the failed pieces out of the deliverable
   count, report the failed share, and close on status-assigned only when
   every offered piece is settled and every failed piece is documented.

## Pitfalls

- Weighing the modes. The clause reads a list membership, not a severity
  score, and a weighted verdict quietly delivers a cracked piece that scored
  low.
- Applying the status to the batch. Pieces are categorized one at a time, and
  a batch-level word hides which piece has to leave the tray.
- Reporting undetermined as deliverable to keep the count round. It is the
  one error the delivery note cannot show, and it ships an uninspected piece.
- Recording the status and skipping the segregation. The report is then
  correct and the shelf is not, which is the failure mode that actually
  reaches the customer.
- Taking a retest as a clearance on its own. Without an admitting policy and
  a named authority it is a second opinion, not a disposition.
- Quoting the offered quantity as the deliverable count. The count is what is
  left after the failed pieces are removed, and nothing else.

## Behavior contract (gate 3)

The status policy validation, the standing-mode reduction with its clearance
rules, the per-piece status with undetermined kept separate, the required
failed-component evidence, the foreign and unrecorded piece arms, the status
grouping, the derived deliverable count and the failed share against a
declared allowance are exercised by the gate 3 contract test:
scripts/test_e2008_failed_coverglass_components.py against
scripts/e2008_failed_coverglass_components_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_failed_coverglass_components.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
