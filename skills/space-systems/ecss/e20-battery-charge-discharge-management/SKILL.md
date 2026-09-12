---
name: e20-battery-charge-discharge-management
description: "Use when verify that a spacecraft battery charger can bring a deeply discharged pack, including one taken all the way to zero volts, back into service under ECSS-E-ST-20C clause 5.7.3: categorize the cell terminal state from its measured voltage, select the charge stage that state permits, derive each stage current limit from the rated capacity, time the recovery trickle against its budget, and report a commanded current, cell voltage, charge temperature, depth of discharge or end-of-discharge voltage outside the permitted window. Trigger: ecss, e-st-20-electrical-scope, battery-charge-management, zero-volt-battery-recovery, deep-discharge-recovery, recovery-trickle-charge, charge-stage-selection, depth-of-discharge-limit, charge-temperature-window."
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
  tags: [ecss, e-st-20-electrical-scope, e20-battery-charge-discharge-management, battery-charge-management, zero-volt-battery-recovery, deep-discharge-recovery, recovery-trickle-charge, charge-stage-selection, depth-of-discharge-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Engineering -- Battery Charge and Discharge Management (space-systems/ecss/e20-battery-charge-discharge-management)

Use when the task is the clause 5.7.3 charger-behaviour demonstration
of ECSS-E-ST-20C -- showing that the charge and discharge management
keeps the battery inside its permitted window in normal operation and,
crucially, that the charger can still reanimate a pack that has been
driven deep, down to and including zero volts.

## Domain quick reference

- A cell is categorized once, from its measured terminal voltage, into
  one of four states: zero volt (at or under the reanimation ceiling),
  deep discharge (above that ceiling but under the normal operating
  floor), operating (inside the normal band), or overvoltage (above
  the maximum charge voltage). Every threshold is a design figure the
  caller supplies; the clause fixes the behaviour, not the numbers.
- Each state permits exactly one charge stage. Zero volt permits only
  a reduced recovery trickle, deep discharge a somewhat larger
  precharge, the operating band full bulk constant current, and
  overvoltage no charge at all. Commanding a stage the state does not
  permit is a finding in its own right, separate from whether the
  current happens to be small.
- The current limit of a stage is its C-rate times the rated capacity,
  so the same charger yields different limits for different packs.
  The recovery trickle exists because a cell taken to zero volts can
  be damaged by a full-rate restart; charging it gently until it
  reaches the bulk entry point is the behaviour the clause is after.
- How long that takes is the recovered fraction of rated capacity
  divided by the trickle current. A charger that can technically
  restart from zero volts but needs longer than the operational
  recovery budget has not satisfied the requirement, so the timing is
  checked alongside the capability flag.
- Charge temperature is a two-sided window. The cold side is not
  symmetric with the hot side in consequence -- charging a cell below
  its lower bound plates metal inside it -- so the two edges are
  reported as separate findings rather than a single out-of-range.
- The discharge side carries two limits: depth of discharge as a
  fraction of rated capacity, and a floor on the end-of-discharge
  voltage. A pack can sit inside one and outside the other, so both
  are evaluated and both are reported.
- Limits are met when the measured value sits at or inside them. A
  measured figure that arrives as a sum of samples or a ratio can land
  a few units in the last place past an exactly compliant boundary, so
  the comparisons absorb that representation error rather than moving
  the limit.

## Workflow

1. Categorize the cell terminal state from its measured voltage
   against the zero-volt, deep-discharge and maximum-charge
   thresholds; reject a negative voltage and a threshold set that does
   not increase strictly.
2. Derive the charge stage the state permits and compare it with the
   stage actually commanded; report a mismatch.
3. Derive the commanded stage's current limit from its C-rate and the
   rated capacity, and report a commanded current above it, a charge
   current present while the stage is inhibit, and a commanded cell
   voltage above the maximum charge voltage.
4. Check the cell temperature against the permitted charge window and
   report the cold and hot breaches separately.
5. For a zero-volt or deep-discharge state, confirm the charger
   declares it can restart from there, compute the recovery-trickle
   time from the recovered capacity fraction and the stage current,
   and report a time beyond the recovery budget.
6. Compute the depth of discharge and compare it and the
   end-of-discharge voltage against their limits.
7. Aggregate the stage, charge, thermal, recovery and discharge
   findings; the management is compliant only when all five lists are
   empty.

## Pitfalls

- Reading "the charger works" from a normal-band charge test and
  declaring clause 5.7.3 satisfied -- the clause is specifically about
  the deep case, and a charger that refuses to start into a pack below
  its undervoltage lockout passes every nominal test and still fails.
- Applying the bulk current limit to a recovery restart because the
  commanded value is below the bulk rating -- the limit that applies
  is the one belonging to the stage the cell state permits, which is
  far smaller.
- Treating a declared zero-volt recovery capability as sufficient
  without timing it; a trickle that needs longer than the operational
  budget leaves the battery unusable for the window that matters.
- Reporting a cold charge and a hot charge as the same out-of-range
  condition -- the failure mechanisms differ, and collapsing them
  hides the plating case that has to be inhibited rather than merely
  derated.
- Checking depth of discharge alone and letting the end-of-discharge
  voltage float; an aged pack reaches its voltage floor well before
  the nominal depth limit, and only the voltage check catches it.
- Comparing a measured sum or ratio against a limit with a bare
  inequality -- an exactly compliant discharge can report a breach of
  a few units in the last place, so the comparison must absorb
  representation error without loosening the limit.

## Behavior contract (gate 3)

The cell-state categorization, stage selection, stage current limit,
recovery timing, charge-temperature window, depth-of-discharge and
end-of-discharge logic is exercised by the gate 3 contract test:
scripts/test_e20_battery_charge_discharge_management.py against
scripts/e20_battery_charge_discharge_management_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_battery_charge_discharge_management.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
