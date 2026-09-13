---
name: e2001-measurement-vacuum-conditions
description: "Use when verify that an emission-yield measurement genuinely runs under the high-vacuum conditions ECSS-E-ST-20-01C clause 9.4.1.3 demands: categorize the chamber working-pressure into a vacuum-regime, compute the mean-free-path and Knudsen-number so the primary-electron path stays free-molecular across the chamber, derive the residual-gas impingement-rate and the monolayer-formation-time and require it to outlast the scan with declared margin, audit the residual-gas partial-pressure inventory and its hydrocarbon-fraction, then screen the run pressure-log for excursions above the operating limit and check the bake-out record. Trigger: ecss, e-st-20-electrical-scope, e2001-measurement-vacuum-conditions, high-vacuum-facility, working-pressure-regime, monolayer-formation-time, residual-gas-inventory, mean-free-path-check, bake-out-substantiation."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-measurement-vacuum-conditions, high-vacuum-facility, working-pressure-regime, monolayer-formation-time, residual-gas-inventory, mean-free-path-check]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor — Emission-Yield Measurement Vacuum Conditions (space-systems/ecss/e2001-measurement-vacuum-conditions)

Use when the task is the clause 9.4.1.3 check of ECSS-E-ST-20-01C: an
emission-yield measurement has to be performed inside a high-vacuum
facility held at low pressure, and the declared facility state has to be
turned into numbers that either carry the run or do not.

## Domain quick reference

- Two physically distinct conditions hide behind the single word
  "vacuum" in this clause. The primary-electron path has to be
  collisionless end to end, and the coupon surface has to stay as
  prepared for the whole scan. The first is a mean-free-path question,
  the second an adsorption-rate question, and a pressure that satisfies
  one can still fail the other.
- The working-pressure is the peak of the run pressure-log, not the base
  pressure quoted on the facility datasheet. Outgassing from the coupon,
  the holder and the electron-source filament raises pressure once the
  beam is on, and the clause is about the state during the measurement.
- The regime ladder is coarse but decisive: ambient above 1e5 Pa, then
  low, medium, high, ultra-high and extreme-high vacuum stepping down
  through 1e2, 1e-1, 1e-6 and 1e-10 Pa. The clause floor is the
  high-vacuum band; a pressure sitting exactly on a ladder bound belongs
  to the cleaner regime the bound opens.
- Mean-free-path follows kinetic theory and scales inversely with
  pressure. Divided by the chamber dimension the beam crosses it gives
  the Knudsen-number: at or above ten the flow is free-molecular and the
  beam is collisionless, below one hundredth it is continuum, and the
  band between is transitional.
- Monolayer-formation-time comes from the Hertz-Knudsen wall flux of the
  dominant residual-gas species, divided into the adsorption-site
  density and scaled by the sticking-coefficient. The dominant species
  matters: at equal partial pressure a light molecule impinges faster
  than a heavy one, so a hydrogen-dominated residual gas re-covers a
  coupon sooner than a water-dominated one.
- The partial-pressure inventory has to be self-consistent — listed
  partials cannot exceed the measured total — and the hydrocarbon share
  is called out separately, because cracked pump-oil carbon on the
  coupon shifts the yield curve rather than merely adding gas load. A
  bake-out that never reached the water-desorption floor for long enough
  leaves that inventory unsubstantiated.

## Workflow

1. Screen the run pressure-log: peak, floor, mean, decade swing, and any
   sample above the declared operating limit. Take the peak as the
   working-pressure for everything that follows.
2. Categorize the working-pressure into a vacuum-regime and check it
   against the high-vacuum floor of the clause.
3. Compute the mean-free-path at the working-pressure and chamber
   temperature, form the Knudsen-number with the chamber dimension, and
   confirm free-molecular flow along the beam path.
4. Audit the residual-gas inventory: consistency against the total,
   dominant species, and hydrocarbon-fraction against its limit.
5. Compute the monolayer-formation-time for the dominant species at the
   working-pressure with the declared sticking-coefficient, and require
   it to exceed the scan duration multiplied by the declared margin.
6. Confirm the bake-out record clears the water-desorption floor in both
   temperature and duration, then aggregate. The run satisfies the
   clause only when the finding list is empty.

## Pitfalls

- Quoting the base pressure reached overnight and calling the clause
  satisfied — the beam-on peak is what the coupon and the beam actually
  saw, and it is routinely one to two decades higher.
- Checking the regime and stopping there — a pressure deep inside the
  high-vacuum band can still lay down a monolayer well inside a long
  scan, which is the condition the yield curve is sensitive to.
- Using a fixed molar mass for the monolayer calculation — the dominant
  residual species changes with the pump set and the bake-out, and the
  wall flux goes as the inverse square root of molecular mass.
- Treating the hydrocarbon share as ordinary gas load — carbon deposited
  by the beam changes the surface being measured, so it carries its own
  fraction limit rather than being folded into the total.
- Letting a boundary case fail on representation: a pressure or a
  monolayer time that lands a few units in the last place on the wrong
  side of a bound it physically equals is compliant, and the tolerance
  belongs in the comparison, never in a relaxed pressure limit.
- Accepting a partial-pressure list that sums above the gauge total as
  merely conservative — it means the gauge, the analyser or the
  calibration disagree, and the inventory cannot be used until that is
  resolved.

## Behavior contract (gate 3)

The regime-ladder, mean-free-path, Knudsen/flow, impingement,
monolayer-formation, inventory-audit, pressure-log and bake-out logic is
exercised by the gate 3 contract test:
scripts/test_e2001_measurement_vacuum_conditions.py against
scripts/e2001_measurement_vacuum_conditions_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e2001_measurement_vacuum_conditions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
