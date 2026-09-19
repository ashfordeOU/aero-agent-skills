---
name: q7001-cleanliness-audits
description: "Audit the contamination-control practices of a cleanroom facility or a supplier against ECSS-Q-ST-70-01C. Use when a facility has to be surveyed before flight hardware is allowed into it, when a supplier's cleanliness performance is being checked on site, or when the next re-audit has to be dated: score every practice area against its weight, categorize each finding as major, minor or observation, compute the weighted conformity index, decide whether the facility is approved, approved with conditions or suspended, and derive the re-audit interval from that index and the contamination criticality of the hardware. Trigger: ecss, q-st-70-01c-cleanliness-scope, contamination-control-facility-audit, supplier-cleanliness-survey, cleanroom-practice-conformity-index, contamination-audit-finding-severity, cleanliness-re-audit-interval, contamination-control-approval-status."
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
  tags: [ecss, q-st-70-01c-cleanliness-scope, q7001-cleanliness-audits, contamination-control-facility-audit, supplier-cleanliness-survey, cleanroom-practice-conformity-index, contamination-audit-finding-severity, cleanliness-re-audit-interval, contamination-control-approval-status]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Cleanliness — Facility and Supplier Audits (space-systems/ecss/q7001-cleanliness-audits)

Use when the task is the audit duty of ECSS-Q-ST-70-01C — going into a
cleanroom or a supplier's premises and deciding, on what is actually
practised there, whether flight hardware may enter and when the place
has to be looked at again.

## Domain quick reference

- An audit scores practice, not paperwork. A facility with an
  immaculate procedure set and operators who gown in the wrong order
  is a contaminating facility, so each area is scored on what was
  observed being done.
- Practice areas are weighted because they are not equally load
  bearing. Cleaning and verification method and air-quality monitoring
  govern whether the cleanliness level is real at all; consumable
  control and documentation matter but cannot by themselves put a
  deposit on a surface.
- A single collapsed area vetoes the whole audit. An index averages,
  and an average lets seven strong areas carry one area scoring zero,
  which is exactly the area that will contaminate the hardware.
- Findings and scores answer different questions. The score says how
  well the area is run; the finding says what specifically has to
  change and how urgently. An audit reporting only one of the two
  leaves the supplier with nothing to act on.
- The re-audit interval is a result, not a calendar habit. A facility
  that scored well on hardware of low contamination criticality can
  wait; the same score on optical or cryogenic hardware cannot, and a
  weak index shortens the interval regardless.
- Approval with conditions is a real state. It says hardware may enter
  while named findings close, and it is only honest when those
  findings carry owners and dates.
- Suspension is about entry, not about blame. It stops new hardware
  going in while the facility fixes what the audit found; hardware
  already inside becomes a separate contamination assessment.

## Workflow

1. Take the facility identifier, the audit date, the contamination
   criticality of the hardware and the per-area scores, and reject a
   case that leaves an area unscored rather than assuming it passed.
2. Validate each score against the declared scale, and refuse an area
   the checklist does not contain.
3. Compute the weighted conformity index as the weighted score over
   the weighted maximum, so the index stays on a zero-to-one scale
   whichever subset of areas was in scope.
4. Categorize the findings by severity and count them, keeping the
   identifiers so the report names what has to close.
5. Apply the vetoes before the index: any area at zero, and any major
   finding count past the declared tolerance, block approval whatever
   the index says.
6. Decide the approval status: approved, approved with conditions, or
   suspended, and state the reason in the same terms the supplier will
   have to act on.
7. Derive the re-audit interval from the index and the criticality,
   floor it so no interval runs away, and give the due date.

## Pitfalls

- Auditing the procedure set instead of the floor. Procedures are the
  claim; the audit exists to test the claim against practice.
- Letting the index carry a collapsed area. The average is a summary,
  not a gate, and the gate has to look at the worst area on its own.
- Scoring areas that were not in scope as zero. An area nobody looked
  at is unknown, not failed, and scoring it as failed both punishes
  the supplier and hides the fact that it was never examined.
- Fixing the re-audit interval by calendar convention. The interval is
  the audit's own output, and a twelve-month habit applied to a
  facility that scored poorly leaves a year of unexamined practice on
  contamination-critical hardware.
- Reporting a finding with no severity. Severity is what tells the
  supplier which findings close before hardware enters and which close
  afterwards.
- Comparing an index against an approval threshold by bare arithmetic.
  A weighted ratio landing exactly on the threshold can miss it by a
  few units in the last place, so the comparison absorbs that
  representation error rather than suspending a compliant facility.

## Behavior contract (gate 3)

Score validation, area weighting, the conformity index, finding
categorization, the collapsed-area veto, the approval status and the
re-audit interval are exercised by the gate 3 contract test:
scripts/test_q7001_cleanliness_audits.py against
scripts/q7001_cleanliness_audits_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7001_cleanliness_audits.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
