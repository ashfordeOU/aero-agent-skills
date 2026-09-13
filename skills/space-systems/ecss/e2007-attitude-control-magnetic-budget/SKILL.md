---
name: e2007-attitude-control-magnetic-budget
description: "Use when maintain the three-axis dipole budget of a spacecraft magnetic moment required by ECSS-E-ST-20-07C clause 4.2.5.2: categorize every contributor as permanent-magnetization, induced-magnetization, a current-loop-moment or a compensation-moment, add the signed axis components to a nominal vehicle-dipole vector, combine the per-contributor uncertainties by root-sum-square, form the worst-case vector with a declared coverage-factor, check each axis and the resultant magnitude against the budget allocation, and cross the worst-case dipole with the ambient geomagnetic-field vector to size the magnetic-disturbance-torque against the attitude-control torque authority. Trigger: ecss, e-st-20-electrical-scope, attitude-control-magnetic-budget, magnetic-dipole-budget, three-axis-dipole-moment, residual-magnetic-moment, magnetic-disturbance-torque, compensation-magnet, geomagnetic-field-vector."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-attitude-control-magnetic-budget, magnetic-dipole-budget, three-axis-dipole-moment, residual-magnetic-moment, magnetic-disturbance-torque, compensation-magnet, geomagnetic-field-vector]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Attitude-Control Magnetic Budget (space-systems/ecss/e2007-attitude-control-magnetic-budget)

Use when the task is the vehicle magnetic dipole budget of
ECSS-E-ST-20-07C clause 4.2.5.2 — maintaining the three axis components
of the spacecraft magnetic moment, rolling up every contributor with
its uncertainty, and showing the resulting magnetic-disturbance-torque
stays inside the attitude-control authority.

## Domain quick reference

- Clause 4.2.5.2 asks for a maintained budget, not a single number: the
  vehicle magnetic moment is a vector with three axis components in the
  spacecraft frame, and it is maintained through the programme as
  contributors are added, measured and compensated. A budget quoting
  only a magnitude has thrown away the sign information that makes
  compensation possible.
- Contributors fall into four categories. Permanent-magnetization is
  the remanent moment of hard magnetic material and of any
  permanent-magnet device. Induced-magnetization is the moment a soft
  magnetic material takes on in the ambient field, so it turns with the
  field rather than with the vehicle. A current-loop-moment is the area
  integral of a powered loop, which exists only in the powered state
  and changes with the operating mode. A compensation-moment is a trim
  magnet or a compensation loop deliberately installed with the
  opposite sign. Each contributor is categorized into exactly one
  category before roll-up.
- Roll-up is a signed vector sum per axis, because opposing
  contributors genuinely cancel — that cancellation is the whole point
  of installing a compensation-moment. Uncertainties do not cancel:
  they combine by root-sum-square per axis, and the worst-case axis
  value is the magnitude of the signed sum plus the coverage-factor
  times that root-sum-square uncertainty.
- The budget is checked twice: per axis against the axis allocations,
  and on the resultant magnitude against the magnitude allocation. Both
  are needed, because three axes each inside their allocation can still
  produce a resultant outside a tighter magnitude requirement.
- The reason attitude control cares is torque. The
  magnetic-disturbance-torque is the cross product of the vehicle
  dipole with the ambient geomagnetic-field vector, so it is
  perpendicular to both and vanishes when the dipole is aligned with
  the field. Comparing that torque with the attitude-control torque
  authority is what turns a dipole number into an attitude-control
  finding; the ratio of authority to disturbance is the torque margin.

## Workflow

1. Inventory every magnetic contributor with its three axis components,
   its per-axis uncertainty and its category. Reject a vector that is
   not three components, a negative uncertainty or an unrecognized
   category before it enters the budget.
2. Categorize each contributor and sum the signed axis components into
   the nominal vehicle-dipole vector, keeping the per-category subtotals
   so a compensation-moment can be traced.
3. Combine the per-axis uncertainties by root-sum-square and form the
   worst-case axis value as the magnitude of the nominal sum plus the
   coverage-factor times the combined uncertainty.
4. Compare each worst-case axis value with its axis allocation and the
   worst-case resultant magnitude with the magnitude allocation. Treat
   an exactly on-limit result as compliant by absorbing the
   floating-point representation error, never by raising the allocation.
5. Cross the worst-case dipole with the ambient geomagnetic-field
   vector to obtain the magnetic-disturbance-torque, and compare its
   magnitude with the attitude-control torque authority to obtain the
   torque margin.
6. Aggregate the axis, magnitude and torque findings; the budget is not
   compliant until all three lists are empty. Report the driving axis
   as the one with the least remaining allocation.

## Pitfalls

- Adding contributor magnitudes instead of signed vectors: that throws
  away cancellation, makes every compensation-moment look like an extra
  source, and can overstate the vehicle moment by a large factor.
- Summing uncertainties algebraically along with the nominals, which
  lets an uncertainty cancel another uncertainty; uncertainties combine
  by root-sum-square and only ever grow the worst case.
- Treating an induced-magnetization contributor as fixed in the
  spacecraft frame: it follows the ambient field, so its worst-case
  orientation is not the orientation it had during the measurement.
- Booking a current-loop-moment once when the loop only carries current
  in one operating mode, or omitting it because the vehicle was
  unpowered during the magnetic test.
- Checking the three axes and never the resultant magnitude, or the
  magnitude and never the axes; each check lets a different violation
  through.
- Reading a compliant dipole as a compliant attitude-control case
  without forming the cross product — the same dipole gives zero torque
  aligned with the field and its full torque perpendicular to it.
- Widening an axis allocation so an exactly on-limit arithmetic sum
  passes; absorb the representation error in the comparison instead and
  leave the allocation untouched.

## Behavior contract (gate 3)

The contributor categorization, signed vector roll-up, uncertainty
combination, axis and magnitude checks and disturbance-torque logic is
exercised by the gate 3 contract test:
scripts/test_e2007_attitude_control_magnetic_budget.py against
scripts/e2007_attitude_control_magnetic_budget_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_attitude_control_magnetic_budget.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
