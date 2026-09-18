---
name: q7002-acceptance-criteria
description: "Evaluate outgassing screening results against the mass-loss and condensable limits their application carries under ECSS-Q-ST-70-02C. Use when a materials list has total mass loss and CVCM figures and each item has to be graded for the place it will serve, from a warm sealed box to the proximity of a cold optic. Picks the grading basis, crediting regained water back only where the application allows it, treats a sub-floor condensable reading as a bound, not a value, and carries a failing material on an approved deviation only when both a deviation and a contamination assessment stand behind it. Trigger: ecss, q-st-70-02, tml-cvcm-screening-limits, outgassing-application-class, recovered-mass-loss-basis, water-vapour-credit, outgassing-deviation-package, sub-floor-cvcm-bound."
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
  tags: [ecss, q-st-70-materials-outgassing-scope, q7002-acceptance-criteria, tml-cvcm-screening-limits, outgassing-application-class, recovered-mass-loss-basis, water-vapour-credit, outgassing-deviation-package]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Outgassing Screening — Acceptance Criteria (space-systems/ecss/q7002-acceptance-criteria)

Use when the task is the acceptance step of the ECSS-Q-ST-70-02C
thermal-vacuum outgassing screening test — deciding whether a material's
measured mass loss and condensable figure clear the limits that the
application it is destined for imposes.

## Domain quick reference

- A screening result is a pair, and both halves carry a limit. The total
  mass loss says how much left the specimen; the condensable figure says
  how much of it came back down on a cold surface. Clearing one and
  missing its partner is a failure, because the two describe different
  hazards: lost mass changes the part, condensed mass changes everything
  looking at it.
- The limits belong to the application, not to the material. The same
  potting compound is comfortably inside a general limit and nowhere
  near the condensable limit that applies beside a cold optic, so a
  materials list cannot be graded until the destination is named.
- Mass loss that was only regained water can be credited back. The
  recovered mass loss is the total with the water-vapour figure removed,
  and where the application allows the credit the loss is graded on that
  instead. It is not universally available: at a cryogenic surface water
  deposits like any other species, so the credit would forgive exactly
  the mass that does the damage.
- A condensable result under the balance quantification floor is a
  bound. It demonstrates compliance when the bound itself sits at or
  under the limit, and demonstrates nothing at all when the floor is
  coarser than the limit — a common trap for the tightest applications.
- A material over a limit is not automatically out, but the route is
  narrow. An approved deviation plus a contamination assessment that
  shows what the excess does to the budget is a decision; either one on
  its own is an assertion, and a reviewer cannot tell the two apart from
  a verdict alone.

## Workflow

1. Validate each result: material name, total mass loss, and either a
   condensable value or a sub-floor bound. Refuse a condensable figure
   larger than the total mass loss and a water-vapour figure larger than
   the total, since neither is physically available.
2. Resolve the application class and read its mass-loss limit,
   condensable limit and whether the water credit is available.
3. Pick the mass-loss basis: the recovered loss when a water-vapour
   figure is present and the application allows the credit, the total
   loss otherwise. Record which basis was used.
4. Compare the basis value with the mass-loss limit and the condensable
   value with the condensable limit, absorbing floating-point
   representation error at the boundary with a named tolerance rather
   than by relaxing the limit.
5. For a sub-floor condensable result, compare the bound instead, and
   raise a finding when the bound cannot clear the limit.
6. Record a finding when a water-vapour figure was supplied for an
   application that cannot use it, so the submitter learns why the
   tighter basis was applied.
7. Assign the verdict: accepted when nothing blocks, accepted on
   deviation when a deviation and a contamination assessment both stand
   behind a failing value, rejected otherwise — naming the missing half
   of an incomplete deviation package.
8. Aggregate across the list, keeping accepted, on-deviation and
   rejected materials in separate groups.

## Pitfalls

- Grading a materials list against one pair of limits. The list spans
  applications, and a single pass of the general limits both clears
  parts that will sit beside an optic and rejects parts sealed inside a
  warm box.
- Applying the water credit everywhere. It is a credit for mass that
  returns as humidity on the ground, which is worth nothing at a surface
  cold enough to keep water.
- Reading a sub-floor condensable result as a pass. When the balance
  floor is coarser than the limit the result is silent, not compliant,
  and the material owes a measurement on a larger specimen mass.
- Accepting a deviation reference as the entire justification. Without
  the contamination assessment nobody has said what the excess costs the
  budget.
- Widening a limit so a value on the boundary passes. Equality at the
  limit is a representation question, handled by the tolerance inside
  the comparison; the limit itself stays as specified.

## Behavior contract (gate 3)

The result validation, class-limit lookup, recovered-mass-loss basis
selection, limit comparison with tolerance, sub-floor bound handling,
deviation-package rule and list aggregation are exercised by the gate 3
contract test: scripts/test_q7002_acceptance_criteria.py against
scripts/q7002_acceptance_criteria_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q7002_acceptance_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
