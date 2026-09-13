---
name: e2001-pre-test-vacuum-bakeout
description: "Use when size and grade the vacuum-bakeout an RF-item receives before any multipactor-test under ECSS-E-ST-20-01C clause 6.2: check the bakeout setpoint against the non-operating temperature allowance reduced by its thermal-margin, convert the dwell at that setpoint into an equivalent dwell at the reference temperature through the desorption Arrhenius relation, track the power-law outgassing-rate decay down to the target rate, grade the chamber pressure actually reached, and decide whether the hold between bakeout completion and test start preserved the bakeout or voided it through an ambient-air break. Trigger: ecss, e-st-20-01c, pre-test-vacuum-bakeout, bakeout-dwell-equivalence, outgassing-rate-decay, chamber-pressure-requirement, inert-backfill-hold, desorption-activation-energy."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-pre-test-vacuum-bakeout, pre-test-vacuum-bakeout, bakeout-dwell-equivalence, outgassing-rate-decay, chamber-pressure-requirement, inert-backfill-hold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Pre-Test Vacuum Bakeout (space-systems/ecss/e2001-pre-test-vacuum-bakeout)

Use when the task is the pre-test vacuum-bakeout of ECSS-E-ST-20-01C
clause 6.2 -- driving adsorbed gas and residual volatiles out of an
RF-item before it is powered in vacuum, so that the multipactor-test
measures the hardware and not the gas film still bound to its surfaces.

## Domain quick reference

- The bakeout window has two bounds, not one. Above, the setpoint is
  capped by the item's non-operating temperature allowance reduced by
  a thermal-margin that covers sensor tolerance and gradient across the
  item. Below, there is a temperature under which desorption is too
  slow for the dwell to buy anything. A setpoint outside either bound
  is a finding; a window whose upper bound has fallen below its lower
  bound means the margin or the allowance is wrong, not the setpoint.
- Dwell and temperature trade against each other through desorption
  kinetics. The Arrhenius ratio between the setpoint and the reference
  temperature the requirement is written at converts a short hot dwell
  into a long dwell at the reference, so a requirement stated as hours
  at a reference temperature is met by any pairing whose equivalent
  hours reach it. The activation energy is a programme input; a wrong
  one moves the equivalence by orders of magnitude.
- Outgassing rate decays as a power law in pumping time, anchored an
  hour after pump-down. That gives both directions of the sizing
  question: the rate reached after a given dwell, and the dwell needed
  to reach a target rate. The bakeout is finished against the rate, not
  against a wall-clock habit.
- Pressure is a separate check from rate. The chamber has to actually
  reach the required pressure during the bakeout; a chamber that never
  gets there has not performed the bakeout however long it ran.
- The bakeout is perishable. Repressurising to ambient air re-adsorbs a
  surface layer and voids the bakeout outright, independent of how
  quickly the test follows. A dry inert backfill preserves it, but only
  for a bounded hold before the test starts.

## Workflow

1. Establish the bakeout window: derate the non-operating allowance by
   the thermal-margin for the upper bound and take the effective
   desorption floor as the lower bound. Reject a collapsed window.
2. Place the setpoint inside that window and record the headroom. Treat
   a setpoint landing exactly on either bound as acceptable.
3. Convert the planned dwell at the setpoint into equivalent hours at
   the reference temperature using the desorption activation energy,
   and compare against the required equivalent hours.
4. From the initial outgassing rate and the decay exponent, compute
   both the dwell needed to reach the target rate and the rate actually
   reached at the end of the planned dwell; flag a dwell that ends
   above the target.
5. Grade the chamber pressure reached during the bakeout against its
   requirement, and record the decades of margin.
6. Categorise the repressurisation medium and grade the hold between
   bakeout completion and test start: an ambient break voids the
   bakeout, an inert backfill holds it for a bounded period only.
7. Aggregate: the item is not ready for the multipactor-test until the
   setpoint, the equivalent dwell, the outgassing target, the chamber
   pressure and the hold are all clear.

## Pitfalls

- Sizing the dwell at the setpoint and reporting it against a
  requirement written at a different reference temperature -- without
  the Arrhenius conversion the two numbers are not comparable, and the
  error runs in whichever direction the setpoint differs.
- Setting the setpoint from the item's allowance with no thermal-margin.
  The controlling sensor is not at the hottest point of the item, so an
  unmargined setpoint routinely overshoots the allowance locally.
- Running the bakeout to a wall-clock duration inherited from a past
  programme and never checking the outgassing rate it actually reached.
- Crediting a bakeout the chamber never supported: a pressure above the
  requirement throughout means the desorbed gas was not being removed.
- Treating a short ambient break as harmless because the test follows
  immediately -- re-adsorption is fast, and the break voids the bakeout
  regardless of the hold that follows.
- Letting an exact-boundary dwell or pressure read as a violation. A
  value assembled from several terms can land a few units in the last
  place beyond its requirement, so the comparison absorbs the
  representation error rather than relaxing the requirement.

## Behavior contract (gate 3)

The bakeout-window, Arrhenius-equivalence, outgassing-decay,
chamber-pressure and post-bakeout-hold logic is exercised by the gate 3
contract test: `scripts/test_e2001_pre_test_vacuum_bakeout.py` against
`scripts/e2001_pre_test_vacuum_bakeout_logic.py` (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_pre_test_vacuum_bakeout.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
