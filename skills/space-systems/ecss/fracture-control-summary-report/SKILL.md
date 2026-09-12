---
name: fracture-control-summary-report
description: "Use when produce a fracture control summary report for all flight items
  in a spacecraft programme under ECSS-E-ST-32C clause 6.4.4: determine the fracture-critical
  designation and its documented basis for each item, verify that crack growth analysis
  is complete and the life ratio meets the programme requirement, confirm that safety
  factors are satisfied, check that the inspection category (inspectable or safe-life)
  is recorded with the correct interval or life margin, record test verification outcomes,
  and aggregate per-item compliance findings into a programme-level status table.
  Flag any item lacking a documented designation basis, incomplete analysis, a life
  ratio below threshold, a missing inspection record, or unverified test status.
  Trigger: ecss, e-st-32-structures-scope, fracture-control-summary-report, fracture-critical,
  crack-growth, inspection, flight-item, safe-life, compliance."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control-summary-report, fracture-critical, crack-growth, inspection, flight-item, safe-life, compliance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Summary Report (space-systems/ecss/fracture-control-summary-report)

Use when the task is to produce the fracture control summary report per
ECSS-E-ST-32C clause 6.4.4 -- collating the fracture-critical designation,
crack growth analysis status, safety factor compliance, inspection category
and interval, and test verification outcome for every flight item, and
consolidating the results into a programme-level compliance table.

## Domain quick reference

- Clause 6.4.4 requires one row in the summary for every flight item in the
  programme. Each row captures: item identification, fracture-critical
  designation with its documented basis, crack growth analysis status, life
  ratio (computed life divided by required life with scatter factor applied),
  safety factor compliance, inspection category, inspection interval or
  safe-life margin, test verification status, and overall item compliance.
- Every item must carry an explicit designation: either fracture-critical or
  non-fracture-critical. A non-fracture-critical designation must be supported
  by a documented basis (e.g. low-stress category, containment, or proved
  redundancy) recorded in the fracture control plan. An item with no documented
  basis is incomplete regardless of its designation.
- For fracture-critical items two inspection categories are recognised:
  inspectable (the item can be examined by an approved NDE method within the
  required interval) and safe-life (the item cannot be reliably inspected in
  service and must demonstrate a life margin of at least four times the
  required programme life without crack growth to failure). The minimum safe-life
  ratio of 4.0 reflects the scatter and inspection uncertainty allowance in
  ECSS-E-ST-32C.
- The life ratio check uses the value produced by the fracture mechanics crack
  growth analysis: for inspectable items the ratio must be ≥ 1.0 (the analysis
  life meets or exceeds one inspection interval with all required safety factors
  already applied); for safe-life items the same ratio must be ≥ 4.0.
- Safety factor compliance is a separate check: the applied stress intensity
  must remain below the fracture toughness divided by the required safety factor
  at the worst-case flaw size. This is assessed independently of the life ratio.
- Test verification records whether a qualifying fracture test, coupon test, or
  similarity argument has been completed and accepted for the item.

## Workflow

1. Retrieve the master flight item list from the fracture control plan. Reject
   any item record missing an item identifier or name before continuing.
2. For each item, read the fracture-critical designation and confirm a documented
   basis exists. Record a finding for any item where the basis field is blank or
   absent.
3. For each fracture-critical item, check that the crack growth analysis is
   marked complete. Record a finding for any item where the analysis is
   incomplete; do not attempt life ratio or safety factor checks on an incomplete
   analysis.
4. For each fracture-critical item with a complete analysis, read the life ratio.
   Determine the required threshold from the inspection category: ≥ 1.0 for
   inspectable items, ≥ 4.0 for safe-life items. Record a finding if the ratio
   falls below the threshold.
5. Check safety factor compliance for each fracture-critical item. Record a
   finding if the safety factor requirement is not met.
6. For inspectable items, confirm that the inspection method is on record and the
   inspection interval is met. Record a finding if either is absent or the
   interval requirement is not satisfied.
7. For safe-life items, the life ratio check at step 4 covers the safe-life
   margin requirement; no separate inspection interval check applies.
8. Check test verification status for each fracture-critical item. Record a
   finding if verification is not complete.
9. Determine per-item compliance: an item is compliant when its findings list is
   empty. Non-fracture-critical items are compliant when the basis is documented.
10. Compile the programme summary: count total items, fracture-critical items,
    non-fracture-critical items, compliant items, and non-compliant items.
    The programme is overall compliant only when every item is individually
    compliant.

## Pitfalls

- Reporting a non-fracture-critical item as compliant without verifying that a
  documented basis exists -- the designation alone is not sufficient; the
  supporting rationale must be on record.
- Skipping life ratio and safety factor checks when the analysis is listed as
  complete but the numerical results have not been reviewed -- completeness of
  the analysis record is a prerequisite, not a substitute for the numerical
  checks.
- Applying the inspectable threshold (≥ 1.0) to a safe-life item -- a safe-life
  item that just meets ≥ 1.0 is not compliant; the ≥ 4.0 margin is required
  because no in-service inspection provides a detect-and-repair opportunity.
- Treating test verification as optional when it is listed as planned -- only
  completed and accepted test evidence closes the verification finding; planned
  or in-progress does not count.
- Reporting programme-level compliance as pass when any single item has open
  findings -- the summary is only compliant when every row is closed.

## Behavior contract (gate 3)

The designation-basis, life-ratio, safety-factor, inspection-category,
safe-life-margin, and test-verification logic is exercised by the gate 3
contract test: scripts/test_fracture_control_summary_report.py against
scripts/fracture_control_summary_report_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_control_summary_report.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
