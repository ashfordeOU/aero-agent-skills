---
name: e2008-failed-blocking-diodes
description: "Use when blocking diode inspection findings have to become delivery status. Derive the designation ECSS-E-ST-20-08C clause 12.7.2 gives a planar blocking diode showing any mode the preceding failure criteria list: treat one standing mode as enough, hold the designation on the individual part rather than on its lot, keep a part whose inspection is unfinished undetermined instead of deliverable, refuse a retest clearance the policy does not admit or that names no authority, demand a segregation record, a non-conformance reference and withdrawal from any string it was allocated to before a failed part counts as handled, reconcile offered parts against records both ways, and derive the deliverable count. Trigger: ecss, e-st-20-08c-clause-12-7-2, failed-blocking-diode-designation, blocking-diode-failure-mode-disposition, blocking-diode-segregation-record, blocking-diode-string-allocation-withdrawal, blocking-diode-deliverable-exclusion, blocking-diode-undetermined-inspection-status."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-08c, e2008-failed-blocking-diodes, e-st-20-08c-clause-12-7-2, failed-blocking-diode-designation, blocking-diode-failure-mode-disposition, blocking-diode-segregation-record, blocking-diode-string-allocation-withdrawal, blocking-diode-deliverable-exclusion, blocking-diode-undetermined-inspection-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Planar Blocking Diodes -- Failed Components (space-systems/ecss/e2008-failed-blocking-diodes)

Use when the task is clause 12.7.2 of ECSS-E-ST-20-08C: the preceding criteria
say what a blocking diode failure mode is, and this clause says what a part
showing one becomes. It is a failed blocking diode, and a failed blocking
diode is not part of what is delivered. This leaf reads the inspection outcome
for each offered part and returns the designation, the evidence that
designation owes, and the deliverable count that survives.

## Domain quick reference

- One standing mode is enough. Modes do not vote and severity does not dilute,
  so a part carrying a single listed mode takes the same designation as a part
  carrying four. What differs is the cause list, not the word.
- The designation is per part. It attaches to the individual diode, not to the
  procurement lot it came from and not to the subgroup it was drawn into, so a
  lot that passed its sampling still contains failed components by name.
- Undetermined is a third word and it has to stay a third word. A part whose
  inspection is unfinished is not deliverable and not failed; collapsing it
  into either arm converts absent evidence into a decision nobody made.
- A designation without segregation is a word in a report. A failed component
  needs a segregation record and a non-conformance reference, or nothing on
  the bench keeps it out of the next delivery, which is exactly how a shorted
  diode walks back into a shipment and onto a string.
- A blocking diode that was already allocated to a string owes one more piece
  of paper. The allocation has to be withdrawn as well, because the build
  paperwork downstream reads the allocation rather than the inspection report,
  and a failed part left allocated is a part the integrator will go looking
  for.
- Retest does not quietly restore a part. A clearance stands only where the
  policy in force admits it and a clearing authority is named, and clearing a
  mode that was never observed is a data defect rather than good news.
- The deliverable count is derived, never declared. It is what is left once
  the failed parts are removed, so a count carried over from the offered
  quantity is wrong by exactly the number that matters.
- A record for a part the lot does not offer is not a typo to correct. It may
  describe another lot entirely, and rewriting the identifier destroys the
  only evidence that it did.

## Workflow

1. Validate the designation policy: whether a segregation record, a
   non-conformance reference and a string-allocation withdrawal are demanded,
   whether a retest clearance is admitted at all, whether an undetermined part
   may still be counted into the delivery, and the failed share the lot may
   carry.
2. Read each part record, refuse a mode outside the recognised set rather than
   dropping it, and collapse repeated modes to one.
3. Apply clearance only where the policy admits it and an authority is named,
   and reject a clearance naming a mode the inspection never raised.
4. Give the part its designation: failed when any mode still stands,
   undetermined when the inspection is unfinished, deliverable otherwise. A
   standing mode outranks an unfinished inspection.
5. For a failed part, name the missing evidence rather than assuming the
   paperwork exists, and hold its designation undocumented until it is there.
   A part with a live string allocation is not handled until that allocation
   is withdrawn.
6. Sweep the offered population: an offered part with no record at all is
   undetermined, and a record for a part the lot does not offer is reported
   rather than absorbed.
7. Group the parts by designation, take the failed parts out of the
   deliverable count, weigh the failed share against its allowance, and close
   on designation-assigned only when every offered part is settled, every
   failed part is documented and no foreign record is riding along.

## Pitfalls

- Weighing the modes. The clause reads a list membership, not a severity
  score, and a weighted verdict quietly delivers a cracked diode that scored
  low.
- Applying the designation to the lot. Parts are categorized one at a time,
  and a lot-level word hides which part has to leave the tray.
- Reporting undetermined as deliverable to keep the count round. It is the one
  error the delivery note cannot show, and it ships an uninspected part onto a
  string that depends on it.
- Recording the designation and skipping the segregation. The report is then
  correct and the shelf is not, which is the failure mode that actually
  reaches the customer.
- Leaving a failed part allocated to its string. The integrator reads the
  allocation, not the inspection report, and will go and fetch the part the
  paperwork still points at.
- Taking a retest as a clearance on its own. Without an admitting policy and a
  named authority it is a second opinion, not a disposition.
- Quoting the offered quantity as the deliverable count. The count is what is
  left after the failed parts are removed, and nothing else.

## Behavior contract (gate 3)

The designation policy validation, the standing-mode reduction with its
clearance rules, the per-part designation with undetermined kept separate, the
required failed-component evidence including the string-allocation withdrawal,
the foreign and unrecorded part arms, the designation grouping, the derived
deliverable count and the failed share against its allowance are exercised by
the gate 3 contract test:
scripts/test_e2008_failed_blocking_diodes.py against
scripts/e2008_failed_blocking_diodes_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e2008_failed_blocking_diodes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
