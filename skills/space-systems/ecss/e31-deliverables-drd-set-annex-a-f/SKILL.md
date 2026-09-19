---
name: e31-deliverables-drd-set-annex-a-f
description: "Produce and grade the thermal control deliverable set of ECSS-E-ST-31C clause 4.9 and its annexes A to F. Use when a programme has to show which thermal documents exist, what each one carries and when it issues: hold the model specification, model description, analysis report, interface control document, balance test specification and detailed design description as one register, name the content sections each owes, compute schedule slack in days against the review it is due at, and refuse a plan where a report issues before the model it reports on. Trigger: ecss, e-st-31-thermal-control, e31-deliverables-drd-set-annex-a-f, thermal-mathematical-model-specification, thermal-geometrical-model-description, thermal-balance-test-specification, thermal-interface-control-document, thermal-deliverable-schedule-slack."
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
  tags: [ecss, e-st-31-thermal-control, e31-deliverables-drd-set-annex-a-f, thermal-mathematical-model-specification, thermal-geometrical-model-description, thermal-balance-test-specification, thermal-interface-control-document, thermal-deliverable-schedule-slack]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Thermal Control — Deliverables and the Annex A-F DRD Set (space-systems/ecss/e31-deliverables-drd-set-annex-a-f)

Use when the task is the deliverables step of ECSS-E-ST-31C clause 4.9 and
its annexes A to F -- deciding which thermal documents a programme owes,
what each of them has to contain, which review each is due at, and whether
the plan on the table can actually be executed in that order.

## Domain quick reference

- The set is six documents, not a folder: a mathematical model
  specification, a thermal and geometrical model description, an analysis
  report, an interface control document, a balance test specification and a
  detailed design description. A plan missing one of the six is incomplete
  even when every document it does list is perfect.
- Each deliverable owes named content, and the content is the requirement.
  An analysis report without a model-uncertainty section is a set of
  temperatures with no statement of how much to believe them.
- Two of the six are due early. The model specification and the interface
  control document fix how the model is built and what the interfaces are,
  and both have to be settled before the detailed work that depends on
  them; the remaining four land at the critical design review.
- The set has a dependency order and it is not the alphabetical one. The
  model description implements the model specification; the analysis report
  reports on the model description; the balance test specification sizes
  its cases from the analysis report; the detailed design description
  depends on the interface control document.
- Lateness is a number of days, not a flag. A document three days past its
  review and one three months past it call for different actions, and only
  the day count distinguishes them.
- Planning a deliverable for a later review than it is owed at is a
  separate finding from issuing it late. The first is a plan that already
  concedes the requirement; the second is a plan that intends to meet it
  and does not.
- Completeness is counted against the whole annex set, not against the
  documents the plan happens to list. Two perfect documents out of six is
  one third complete, not complete.

## Workflow

1. Take the declared plan: for each deliverable, its key, the content
   sections it carries, the review it is planned for, and its planned issue
   date. Take the programme review dates separately.
2. Refuse a plan naming a deliverable outside the annex set, repeating a
   deliverable, or carrying a malformed date.
3. For each declared deliverable, list the content sections of its annex
   requirement that it does not carry.
4. Compare the review it is planned for with the review it is owed at, and
   raise a finding when the plan defers it.
5. Compute schedule slack as whole days between the planned issue date and
   the date of the review it serves; a negative slack is the day count it
   is late by.
6. Check the dependency order against the planned dates, and report a
   deliverable planned to issue before something it depends on, together
   with a dependency the plan does not carry at all.
7. Roll up: absent deliverables by name, completeness against the whole set
   of six, and the deliverable with the least slack.

## Pitfalls

- Grading the documents the plan lists and calling the set complete. The
  register is the six, and an absent document produces no findings of its
  own precisely because it is absent.
- Treating the content sections as a suggested outline. They are what the
  deliverable owes, and a missing section is a missing requirement.
- Ordering the set alphabetically or by annex letter. The executable order
  is the dependency order, and the annex letters only happen to agree with
  it in part.
- Reporting lateness as a boolean. The action for three days late and three
  months late is not the same action.
- Merging the deferred-review finding with the late-issue finding. A plan
  that moves a document to a later review has conceded the requirement
  before any date slips.
- Accepting an analysis report dated before the model description it
  reports on because both sit before the review. The review date is
  satisfied and the work cannot have happened.
- Measuring completeness against the plan rather than the annex set, which
  makes a two-document plan read as fully complete.

## Behavior contract (gate 3)

The six-deliverable register with its annex letters, due reviews and
dependency edges, the content-section gap list, the milestone-deferral
finding, the whole-day schedule slack including the zero-slack boundary,
the dependency-order and absent-dependency findings, and the roll-up with
completeness measured against the whole set are exercised by the gate 3
contract test: scripts/test_e31_deliverables_drd_set_annex_a_f.py against
scripts/e31_deliverables_drd_set_annex_a_f_logic.py (stdlib unittest,
offline). Schedule arithmetic is whole days from the stdlib date type, so
it carries no floating-point boundary at all.
Run: python3 scripts/test_e31_deliverables_drd_set_annex_a_f.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
