---
name: e3102-acceptance-principles-allowed-modifications
description: "Evaluate a two-phase heat transport flight article against the acceptance principles of ECSS-E-ST-31-02 clause 4.5 and its permitted-change table: grade every proposed difference from the qualified design as accepted as is, permitted against a delta acceptance test, or outside acceptance altogether, take the most onerous grade as the one that governs, build the acceptance test set the permitted changes oblige, and confirm the acceptance levels sit inside the qualified envelope. Use when a heat pipe or loop heat pipe flight unit differs from the qualified article and the delivery route has to be settled. Trigger: ecss, e-st-31-02-two-phase, two-phase-acceptance-principles, allowed-design-modification-table, delta-acceptance-test-set, qualified-span-containment, two-phase-requalification-trigger, acceptance-level-envelope-check."
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
  tags: [ecss, e-st-31-02-two-phase, e3102-acceptance-principles-allowed-modifications, two-phase-acceptance-principles, allowed-design-modification-table, delta-acceptance-test-set, qualified-span-containment, two-phase-requalification-trigger, acceptance-level-envelope-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Two-Phase — Acceptance Principles and Allowed Modifications (space-systems/ecss/e3102-acceptance-principles-allowed-modifications)

Use when the task is the acceptance step of ECSS-E-ST-31-02 clause 4.5
-- deciding whether a two-phase flight article that differs from the
qualified design can still be delivered on acceptance, what that costs in
extra testing, and which differences send it back to qualification.

## Domain quick reference

- Acceptance hardware is built to an already-qualified design. Its tests
  run at levels inside the qualified envelope, and it is allowed to
  differ from the qualified article only in the ways the permitted
  change table names.
- Every proposed difference grades to one of three dispositions, ordered
  by cost: accepted as is, permitted against a delta acceptance test, or
  outside acceptance and back to qualification.
- Two kinds of change are graded differently. A dimensional change is
  graded against the qualified span -- inside it the change is
  permitted, outside it the qualified basis no longer covers the
  article. A change of kind is graded by what it is: a wick, a working
  fluid or an envelope material change breaks the qualified basis
  whatever the numbers look like.
- The article takes the most onerous disposition in the set. One change
  back to qualification governs the delivery even when everything else
  on the list is trivial.
- A permitted change brings its own acceptance test. An evaporator
  length or charge change owes a transport capability demonstration; a
  wall thickness change owes a proof pressure test; a mounting interface
  change owes an interface conductance test. A change back to
  qualification adds no acceptance test, because the article is not on
  the acceptance route any more.
- Acceptance levels themselves are part of the principle. A cold limit
  below the qualified cold end, a hot limit above the qualified hot end
  or a spectral density above the qualified one is an acceptance test
  the qualification never covered.

## Workflow

1. Name the article and list every difference from the qualified design
   as a typed change. Refuse a change type that is not in the permitted
   change table rather than grading it by analogy -- an ungraded change
   is a qualification question, not an acceptance one.
2. Grade each dimensional change by containment in its qualified span,
   absorbing representation error at the bounds so a value set exactly
   on a limit is inside it.
3. Grade each change of kind from the table directly.
4. Reduce the grades to the most onerous one and record each change that
   put the article back to qualification as its own finding.
5. Build the acceptance test set: the baseline plus whatever the
   permitted changes add, de-duplicated, so a proof pressure test
   already in the baseline is not run twice.
6. Compare the acceptance levels against the qualified envelope at both
   temperature ends and on the vibration density, and close with a
   deliverability verdict that is false while any finding stands.

## Pitfalls

- Grading a wick or fluid change on how small it looks. Those changes
  move the capillary limit and the fluid-material compatibility basis
  directly, and the qualified evidence was taken on the old ones; the
  table puts them outside acceptance for that reason.
- Letting one trivial change set the disposition for the article. The
  governing grade is the most onerous one in the set, and averaging
  across a change list is how an article back to qualification ships as
  acceptance hardware.
- Comparing a dimension with a qualified bound by bare arithmetic. A
  value set exactly on a limit can land a few units in the last place
  outside it once it has been through a unit conversion, and that
  phantom step outside the span costs a requalification that was never
  needed.
- Treating a delta acceptance as paperwork. It names an extra test, and
  a delta agreed without that test in the acceptance programme leaves
  the change unverified on the flight article.
- Running acceptance at a level the qualification never reached. It
  looks conservative and is the opposite: the article is being asked to
  survive an environment no qualified unit ever saw.

## Behavior contract (gate 3)

Change validation, qualified-span containment, disposition grading,
most-onerous reduction, acceptance test set assembly, acceptance level
audit and the deliverability verdict are exercised by the gate 3
contract test:
scripts/test_e3102_acceptance_principles_allowed_modifications.py
against
scripts/e3102_acceptance_principles_allowed_modifications_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3102_acceptance_principles_allowed_modifications.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
