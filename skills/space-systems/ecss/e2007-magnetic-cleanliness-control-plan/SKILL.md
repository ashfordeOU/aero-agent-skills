---
name: e2007-magnetic-cleanliness-control-plan
description: "Use when audit the documented magnetic-cleanliness control plan required by ECSS-E-ST-20-07C clause 4.2.5.1: check the plan carries its mandatory parts — design-guidelines, source-emission-limits, magnetic-screening procedure, verification-approach and dipole-budget maintenance — then allocate the system stray-field requirement down to each item by equal-share or root-sum-square, evaluate each item's dipole-moment contribution at the reference-distance in the axial or equatorial orientation, categorize every item into its magnetic-screening level from its permanent-magnet content, ferromagnetic mass and declared moment, and flag any item that exceeds its allocation or has no screening record. Trigger: ecss, e-st-20-electrical-scope, magnetic-cleanliness-control-plan, stray-magnetic-field, dipole-emission-limit, magnetic-screening, residual-magnetic-moment, demagnetization-procedure, magnetometer-reference-distance."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-magnetic-cleanliness-control-plan, magnetic-cleanliness, stray-magnetic-field, dipole-emission-limit, magnetic-screening, residual-magnetic-moment, demagnetization-procedure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Magnetic Cleanliness Control Plan (space-systems/ecss/e2007-magnetic-cleanliness-control-plan)

Use when the task is the magnetic-cleanliness control plan of
ECSS-E-ST-20-07C clause 4.2.5.1 — confirming the plan is documented
with its mandatory parts, allocating the system stray-field
requirement into per-item source-emission-limits, and categorizing
every item into the magnetic-screening level its construction demands.

## Domain quick reference

- Clause 4.2.5.1 asks for a plan, not a measurement: a documented
  control plan carrying design-guidelines for magnetically quiet
  construction, source-emission-limits allocated to items, a
  magnetic-screening procedure, a verification-approach, and the rule
  by which the dipole-budget is maintained through the programme. A
  plan missing any of those parts is incomplete even when every item
  measures clean, because the control mechanism was never written down.
- The driving requirement is a stray-field level at a reference-distance,
  typically the mounting position of a science magnetometer or of the
  attitude-determination sensor. Allocation turns that single system
  number into per-item limits. Equal-share divides it by the item count
  and is conservative; root-sum-square divides it by the square root of
  the item count and assumes the item moments add incoherently, which
  is the usual assumption for randomly oriented residual moments.
- An item's contribution is modelled as a point magnetic-dipole: the
  field falls with the cube of distance, is twice as strong along the
  dipole axis as in the equatorial plane, and scales linearly with the
  dipole-moment. Halving the reference-distance multiplies the field by
  eight, so the distance the plan declares is as load-bearing as the
  limit itself.
- The magnetic-screening level is set by construction, not by wish. An
  item containing a permanent-magnet, or declaring a moment at or above
  the mapping threshold, needs full three-axis dipole mapping followed
  by compensation or demagnetization. An item with ferromagnetic mass
  above the soft-material threshold needs full dipole mapping. An item
  carrying a current-loop needs powered current-loop mapping, because
  its moment only exists when it is energized. A small, non-magnetic,
  unpowered item below the exemption threshold is screening-exempt and
  is recorded as such rather than silently skipped.
- Screening status is part of the control loop: an item whose level is
  anything other than screening-exempt must have screening planned or
  complete. An item requiring screening with no screening on record is
  a plan finding regardless of its declared moment, because the
  declared value is then unverified.

## Workflow

1. Check the plan document for its mandatory parts and list the parts
   that are absent. An absent part is a finding in its own right.
2. Read the system stray-field requirement and the reference-distance
   at which it applies; reject a non-positive limit or distance.
3. Allocate the system limit across the item list by the declared
   allocation method (equal-share or root-sum-square) to obtain each
   item's source-emission-limit, letting an item that carries a
   negotiated allocation of its own override the uniform split.
4. Categorize each item into its magnetic-screening level from its
   permanent-magnet content, ferromagnetic mass, current-loop presence
   and declared dipole-moment.
5. Compute each item's field contribution at the reference-distance in
   the declared orientation and compare it with its allocation. Treat
   an exactly on-limit item as compliant by absorbing the
   floating-point representation error, never by raising the limit.
6. Combine the item contributions by root-sum-square and compare the
   result with the system stray-field requirement. A uniform
   root-sum-square split makes the two agree by construction, so this
   step earns its place when items carry negotiated allocations: then a
   set of individually compliant items can still overspend the system
   requirement, and only the combined check sees it.
7. Aggregate the plan-completeness, screening-record and emission
   findings; the plan is not compliant until all three lists are empty.

## Pitfalls

- Treating the plan as satisfied by a test report — clause 4.2.5.1 is
  about the documented control mechanism, and a report of measurements
  made without guidelines, limits and a screening procedure does not
  replace it.
- Allocating by root-sum-square when the item moments are aligned by
  construction (for example a row of identical actuators mounted the
  same way); incoherent addition is an assumption that must hold, and
  when it does not, equal-share is the defensible allocation.
- Quoting a field without its reference-distance and orientation: the
  same dipole-moment gives an eightfold different field at half the
  distance and a twofold difference between the axial and equatorial
  direction.
- Accepting a declared dipole-moment from an item that was never
  screened — the declaration is a supplier statement until the
  screening procedure verifies it, so a missing screening record is a
  finding even when the number looks comfortable.
- Handing out negotiated per-item allocations without re-checking the
  combined total; a uniform split is self-consistent, but negotiated
  limits are not, and a set of individually compliant items can then
  overspend the system stray-field requirement.
- Widening an emission limit to absorb an exactly on-limit arithmetic
  result; absorb the representation error in the comparison instead.

## Behavior contract (gate 3)

The plan-completeness, allocation, dipole-field, screening-level and
aggregate-compliance logic is exercised by the gate 3 contract test:
scripts/test_e2007_magnetic_cleanliness_control_plan.py against
scripts/e2007_magnetic_cleanliness_control_plan_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_magnetic_cleanliness_control_plan.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
