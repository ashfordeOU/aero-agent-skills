---
name: e20-battery-specification-for-energy-balance
description: "Use when size a spacecraft secondary battery so that the ECSS-E-ST-20C clause 5.6.2 energy balance closes in every declared mission phase: convert each phase into produced, consumed and net energy over its duration, divide the phase discharge by the discharge-path efficiency and the allowable depth of discharge to obtain the capacity it demands, carry the driving phase back to a beginning-of-life rating through capacity fade, confirm the charge window restores what the discharge window drew, and prove the contingency and safe modes are inside the phase set. Trigger: ecss, e-st-20-electrical-scope, e20-battery-specification-for-energy-balance, battery-capacity-sizing, mission-energy-balance, depth-of-discharge-limit, eclipse-discharge-energy, contingency-mode-sizing, capacity-fade-end-of-life."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-specification-for-energy-balance, battery-capacity-sizing, mission-energy-balance, depth-of-discharge-limit, eclipse-discharge-energy, contingency-mode-sizing, capacity-fade-end-of-life]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering — Battery Specification for Energy Balance (space-systems/ecss/e20-battery-specification-for-energy-balance)

Use when the task is specifying the capacity of an on-board secondary battery
under ECSS-E-ST-20C clause 5.6.2 -- the capacity that keeps generation, load
and storage in balance across every mission phase the spacecraft will see,
with the contingency and safe modes counted in, not appended afterwards.

## Domain quick reference

- A mission phase is a window with a duration, a load demand and a generation
  capability. Multiplying power by duration turns it into energy: available
  energy from the array, consumed energy at the loads raised by the losses of
  the distribution path, and the net of the two. A negative net is the energy
  the store has to deliver; a positive net is the surplus available to put
  back into it.
- Capacity is not the phase discharge. The store delivers through a discharge
  path with its own efficiency, and it is allowed to give up only a fraction
  of its rated energy -- the allowable depth of discharge, which is set by the
  cycle life the mission needs and is deliberately deeper for a mode the
  spacecraft enters rarely than for one it repeats every orbit. Dividing the
  phase discharge by both fractions gives the capacity that phase demands.
- The sizing is set by the single phase demanding the most capacity, not by
  the sum and not by the nominal case. A short deep safe-mode survival window
  routinely beats the eclipse that dominates the cycle count, which is why the
  contingency modes belong in the phase set from the start: a set with no
  contingency phase has not been shown to balance outside nominal operation.
- Capacity fades with age and cycling, so the demand is an end-of-life demand
  and the specification is a beginning-of-life rating. Dividing the end-of-life
  demand by the retained fraction after the mission duration gives the rating
  to procure; reading the sizing as a beginning-of-life number silently spends
  the whole fade allowance.
- Closing the balance needs one check the per-phase numbers do not give: over
  the phases that recur, the surplus has to at least restore the discharge.
  A cycle whose net energy is negative depletes the store no matter how large
  the capacity is, because every repetition starts lower than the last.

## Workflow

1. Normalize every mission phase: name, category, duration, load power and
   generated power, plus an allowable depth of discharge that defaults from
   the category when the project has not set one. Reject an unrecognized
   category, a non-positive duration and a negative power before sizing.
2. Convert each phase to energy: available, consumed at the distribution
   efficiency, net, and from the net the phase discharge or surplus.
3. Compute the capacity each phase demands -- phase discharge divided by the
   discharge efficiency and by that phase's allowable depth of discharge. A
   phase that runs in surplus demands none.
4. Take the maximum over all phases as the end-of-life demand, record which
   phase drove it, and divide by the fraction of capacity retained after the
   mission duration to get the beginning-of-life rating to specify.
5. Verify the declared capacity: convert it to its end-of-life value, compute
   the resulting depth of discharge phase by phase against each allowance, and
   sum the net energy over the recurring phases to confirm the cycle does not
   run down.
6. Check the phase set itself contains at least one contingency or safe mode,
   and check every charge window restores, at the charge efficiency, what the
   discharge window it follows drew. The specification is complete only when
   the finding list is empty.

## Pitfalls

- Sizing on the nominal eclipse alone and treating the safe mode as a later
  delta -- the survival window is usually longer and allowed deeper, so it can
  be the driving case, and discovering that after the cells are procured is a
  capacity change, not an analysis update.
- Taking the phase discharge as the capacity -- the store never delivers its
  full rating, and skipping the discharge efficiency and the depth-of-discharge
  allowance under-sizes it by a factor of three or more on a typical cycle.
- Specifying the sizing result as the beginning-of-life capacity -- the demand
  it answers is an end-of-life demand, so procuring exactly that rating means
  the balance stops closing on the first year of fade.
- Reading a set of in-limit per-phase depths of discharge as a closed balance
  -- if the recurring surplus does not exceed the recurring discharge, the
  store walks down cycle by cycle and every single-phase check still passes.
- Folding the contingency phases into the recurring cycle sum -- they are not
  repeated, so counting their discharge in the cycle net turns a healthy
  balance into a false negative and hides the real one.

## Behavior contract (gate 3)

The phase normalization, phase-energy, capacity-demand, fade-carryback,
recharge-feasibility and cycle-balance logic is exercised by the gate 3
contract test: scripts/test_e20_battery_specification_for_energy_balance.py
against scripts/e20_battery_specification_for_energy_balance_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_battery_specification_for_energy_balance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
