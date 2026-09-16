---
name: q6013-class-3-selection-overview
description: "Use when a parts selection list is reviewed at the lowest class. Assess whether the general selection duties behind a commercial component are discharged at the lowest assurance class of ECSS-Q-ST-60-13C clause 6.2.1: credit a duty only where an evidence reference is cited, leave an asserted duty open, drop a duty from the denominator only where it is discretionary at this class and the not-applicable claim carries a recorded justification, refuse that claim on a duty the class keeps mandatory, weight the credited duties into a coverage fraction against the declared floor, and return the outstanding duties, the governing component and one verdict. Trigger: ecss, q-st-60-13c-clause-6-2-1, class-three-selection-duty-register, selection-duty-evidence-credit, selection-duty-applicability-claim, selection-coverage-floor, class-three-selection-verdict."
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
  tags: [ecss, q-st-60-13-commercial-eee-component-scope, q-st-60-13c, q6013-class-3-selection-overview, class-three-selection-duty-register, selection-duty-evidence-credit, selection-duty-applicability-claim, selection-coverage-floor, class-three-selection-verdict]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Commercial EEE — Class 3 Selection Overview (space-systems/ecss/q6013-class-3-selection-overview)

Use when the task is clause 6.2.1 of ECSS-Q-ST-60-13C at the lowest assurance
class: the general duties a project owes when it picks a commercial component
for a design, and how far those duties have actually been discharged. This
leaf grades a candidate list duty by duty and returns what is still owed.

## Domain quick reference

- The lowest class is where the selection duties earn their keep, because it
  is the class with the least downstream testing to catch a bad choice. The
  duty set is short precisely so that none of it can be skipped.
- Four duties stay mandatory whatever the class: the part has to suit the
  application, its ratings have to cover the environment it will see, the real
  manufacturer has to be known rather than the distributor who shipped it, and
  the excluded technologies have to be absent. No coverage fraction buys any
  of them.
- The remaining duties are discretionary here, and discretionary means
  justified, not skipped. A duty dropped with a written reason leaves the
  denominator; a duty dropped silently stays in it and stays owed.
- An evidence reference is the whole difference. A duty someone says was done
  and a duty with a document number behind it read the same in a meeting and
  differently in an audit, and only one of them survives a change of staff.
- Coverage is taken over what still applies, not over the full register.
  Grading against a denominator that includes duties the project legitimately
  dropped punishes exactly the projects that wrote their reasoning down.
- The governing component is the weakest one. A list mean above the floor
  built from one thoroughly documented part and one undocumented part is the
  arithmetic hiding the only line that matters.

## Workflow

1. Validate the duty register: weights sum to unity, mandatory flags are real
   booleans, and at least one duty stays mandatory.
2. Disposition every duty in the register for each component, treating an
   absent declaration as open rather than as satisfied.
3. Refuse an evidenced claim that cites no reference, and record an asserted
   duty as open with its reason.
4. Refuse a not-applicable claim on a mandatory duty, and refuse one on a
   discretionary duty that carries no written justification; both stay owed.
5. Drop a justified discretionary duty from the applicable set so the
   denominator reflects what the project actually owes.
6. Weight the credited duties over the applicable duties to form the component
   coverage, and compare it with the declared floor through a named tolerance
   rather than by moving the floor.
7. Categorize each component as blocked when a mandatory duty is outstanding,
   otherwise open or closed on the coverage.
8. Return the list coverage, the union of outstanding duties, the governing
   component, ranked findings and one verdict.

## Pitfalls

- Reading a short duty set as a light one. The set is short because the class
  has the least downstream verification behind it, so each remaining duty is
  carrying more weight, not less.
- Claiming a mandatory duty is not applicable. A simple part still has to suit
  its application and still has to have a known manufacturer; the claim is
  refused and the duty stays outstanding.
- Dropping a discretionary duty without writing down why. The unwritten
  justification is the one nobody can reconstruct at the review, and it is
  indistinguishable from an oversight.
- Grading coverage over the full register. Including legitimately dropped
  duties in the denominator makes an honest project look worse than a silent
  one, which teaches exactly the wrong habit.
- Accepting an asserted duty. Without a reference there is nothing for a later
  reader to open, and the selection argument dies with the engineer who made
  it.
- Averaging coverage across the list. The weakest component governs; a list
  mean is how a thoroughly documented part carries an undocumented one.

## Behavior contract (gate 3)

The register validation, duty disposition, evidence and justification rules,
mandatory-duty refusal, applicable-set reduction, coverage weighting, floor
comparison, category assignment, governing-component selection and list
verdict are exercised by the gate 3 contract test:
scripts/test_q6013_class_3_selection_overview.py against
scripts/q6013_class_3_selection_overview_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q6013_class_3_selection_overview.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
