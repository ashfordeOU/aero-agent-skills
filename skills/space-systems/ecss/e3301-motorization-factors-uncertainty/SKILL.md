---
name: e3301-motorization-factors-uncertainty
description: "Derive the factored resistive torques and forces a mechanism actuation function has to be sized against under ECSS-E-ST-33-01 clause 4.7.5.3.1. Use when every resistive contribution, from dry friction and harness stiffness to stiction, seal drag, spring hysteresis and inertia, needs the minimum uncertainty factor its own kind and knowledge basis carry, applied line by line instead of once to the sum, and evaluated at end of life and at the worst point of travel rather than at a nominal mid-stroke value. Trigger: ecss, e-st-33-01-mechanisms, mechanism-motorization-uncertainty-factor, resistive-torque-build-up, mechanism-friction-uncertainty, end-of-life-resistive-torque, mechanism-travel-worst-case, harness-resistive-torque."
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
  tags: [ecss, e-st-33-01-mechanisms, e3301-motorization-factors-uncertainty, mechanism-motorization-uncertainty-factor, resistive-torque-build-up, mechanism-friction-uncertainty, end-of-life-resistive-torque, mechanism-travel-worst-case, harness-resistive-torque]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Mechanisms — Motorization Factors and Uncertainty (space-systems/ecss/e3301-motorization-factors-uncertainty)

Use when the task is the resistive side of ECSS-E-ST-33-01 clause
4.7.5.3.1 -- building the factored torque or force an actuation
function has to overcome, before any actuator capability is brought
into the comparison.

## Domain quick reference

- The budget is a list of contributions, not a single number. Dry
  friction, lubricated friction, harness and cable resistance, adhesion
  and stiction after a long dwell, seal and lubricant drag, viscous
  damping, spring hysteresis, latch release and the inertia the
  actuator accelerates are separate line items because each is known to
  a different accuracy.
- The minimum uncertainty factor has two inputs. The kind of resistance
  sets the floor, because some terms scatter badly in service and
  others barely move. The knowledge basis then uplifts it: a
  measurement on flight-standard hardware adds nothing, a measurement
  on a representative unit a little, a validated analysis more, and a
  heritage estimate the most.
- The factor is applied per contribution. Factoring the sum once lets a
  tightly measured inertia subsidise a guessed stiction term, and the
  resulting total is smaller than any of the individual clause
  requirements would allow.
- A declared project factor is accepted only at or above the floor. A
  number below it is not a tailoring decision made here; the floor is
  carried and the shortfall is reported so that the tailoring is argued
  where tailoring belongs.
- Every contribution owes a worst-case over life and travel. Friction
  and drag grow with cycles and with contamination, and a hinge is
  rarely worst at mid-stroke, so a value taken once at begin of life in
  the middle of the range has not been shown to bound anything.
- The dominant factored contribution is the one worth measuring
  properly. Reporting it turns the budget into a plan: it names the
  single test that would buy back the most margin.

## Workflow

1. Declare the function: identifier, whether it is budgeted in torque
   or in force, the travel range, and the life points it is dimensioned
   at.
2. Enter each resistive contribution with its kind, its knowledge
   basis, its nominal worst-case value, any declared factor, the life
   points it was evaluated at, and either an explicit worst-case-over-
   travel claim or the travel stations it was evaluated at.
3. Resolve the minimum factor for each contribution from the kind and
   the basis, and hold any declared factor to that floor.
4. Grade coverage: flag a contribution that skips a required life point
   and one whose station schedule leaves a gap wider than the policy
   allows or stops short of either end of travel.
5. Factor each contribution, then sum. Report the nominal total, the
   factored total and the difference between them as the uncertainty
   allowance the design is carrying.
6. Name the dominant factored contribution and every contribution with
   a finding, and hand the factored total to the actuation and holding
   dimensioning steps.

## Pitfalls

- Applying one uncertainty factor to the summed resistance. It is the
  most common shortcut and it produces a number that satisfies no
  per-kind minimum; the sum is only correct when every term happens to
  carry the same factor.
- Pricing the kind and forgetting the basis. A friction coefficient
  copied from a heritage report is not the same evidence as one
  measured on the flight bearing, and the factor is where that
  difference is recorded.
- Reading a declared factor below the floor as a project decision. It
  silently overrides the minimum; the floor is carried instead and the
  shortfall is reported rather than absorbed.
- Taking the resistive value at begin of life. Lubricant degradation,
  wear debris and cold welding after a long unactuated dwell all push
  the resistance up, so the end-of-life value is the one that sizes the
  actuator.
- Sampling travel at the two end points only. A cable loom or a harness
  wrap can peak in the middle of the stroke, and a two-station schedule
  steps straight over it.
- Comparing a declared factor with its floor by bare arithmetic. A
  factor written to exactly the minimum can land a few units in the
  last place below it, so the comparison absorbs that representation
  error rather than raising a phantom shortfall.

## Behavior contract (gate 3)

The per-kind and per-basis factor tables, the declared-factor floor,
per-contribution factoring, life-point coverage, travel-station gap
coverage, the factored total and its uncertainty allowance, and the
dominant contribution are exercised by the gate 3 contract test:
scripts/test_e3301_motorization_factors_uncertainty.py against
scripts/e3301_motorization_factors_uncertainty_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_e3301_motorization_factors_uncertainty.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
