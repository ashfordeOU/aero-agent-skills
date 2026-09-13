---
name: e2006-neutral-gas-discharge-triggering
description: "Use when assess whether neutral-gas released close to a spacecraft can trigger a gas-discharge on a high-voltage-surface under ECSS-E-ST-20-06C clause 6.9: inventory every release path (propulsion-plume, propellant-leak, pressurant-leak, commanded-vent, material-outgassing, water-desorption, sublimation), compute the local neutral-density and neutral-pressure each one produces at the exposed hardware, form the pressure-gap product, evaluate the Paschen-breakdown voltage for the released species, compare it against the applied electrode-voltage with the required breakdown-margin, and derive the post-launch outgassing-decay time after which high-voltage-activation is permitted. Trigger: ecss, e-st-20-electrical-scope, e2006-neutral-gas-discharge-triggering, neutral-gas-release, paschen-breakdown, paschen-minimum, gas-discharge-triggering, outgassing-decay, high-voltage-activation-inhibit."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-neutral-gas-discharge-triggering, neutral-gas-release, paschen-breakdown, paschen-minimum, gas-discharge-triggering, outgassing-decay, high-voltage-activation-inhibit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Neutral-Gas Discharge Triggering (space-systems/ecss/e2006-neutral-gas-discharge-triggering)

Use when the task is the ECSS-E-ST-20-06C clause 6.9 assessment of gas
released in the vicinity of the vehicle and the gas-discharge risk that
release creates for exposed high-voltage hardware -- where the gas comes
from, how dense it is at the hardware, and whether the resulting
pressure-gap product puts the design near the Paschen-breakdown curve.

## Domain quick reference

- Clause 6.9 exists because vacuum is only an insulator while it stays
  a vacuum. Any neutral-gas release raises the local neutral-density
  around the vehicle, and a high-voltage-surface that is safe at
  ambient orbital density can break down in the transient cloud of its
  own vent, its own thruster, or its own outgassing.
- Release paths fall into three behaviours: continuous (a
  propellant-leak, a pressurant-leak, a steady sublimation),
  commanded-transient (a propulsion-plume, a tank-vent, an active
  gas-release experiment) and decaying (material-outgassing and
  water-desorption, strongest right after launch and falling as an
  inverse power of elapsed time). The behaviour decides whether the
  risk is permanent, schedulable, or bounded by a wait.
- Local neutral-density follows free-molecular expansion: the emitted
  particle-rate divided by the expansion solid-angle, the square of
  the distance, and the flow speed. Converting that density to a
  pressure at the local gas-temperature gives the quantity the
  Paschen-breakdown curve actually takes.
- The Paschen-breakdown voltage depends on the pressure-gap product
  and the released species, not on pressure alone. Each gas carries its
  own ionisation coefficients and its own secondary-emission
  coefficient, so a xenon-plume and a water-vapour cloud at the same
  pressure sit on different curves. Every curve has a minimum: below
  the minimum pressure-gap product no breakdown is possible at any
  voltage, and above it the breakdown voltage climbs again.
- The dangerous region is the left branch and the neighbourhood of the
  minimum, because that is where a few hundred volts is enough. A
  design is acceptable when the breakdown voltage of the worst credible
  released species at the worst credible pressure-gap product exceeds
  the applied electrode-voltage by the required breakdown-margin.
- Post-launch outgassing-decay sets an activation-inhibit window: the
  local pressure falls as an inverse power of time, so the assessment
  yields a time after which high-voltage-activation is permitted rather
  than a permanent prohibition.

## Workflow

1. Inventory every release path near the exposed hardware and place
   each one in its behaviour family. Reject an unrecognized release
   path before the assessment starts.
2. For each path, convert the mass-rate to a particle-rate using the
   species molar-mass, then compute the local neutral-density at the
   hardware from the expansion solid-angle, the distance and the flow
   speed, and convert that density to a local pressure at the gas
   temperature.
3. Form the pressure-gap product for the electrode geometry under
   assessment, and locate it relative to the Paschen-minimum of the
   released species: below the minimum product, no breakdown is
   possible and the path is cleared for that geometry.
4. Where breakdown is possible, evaluate the Paschen-breakdown voltage
   and divide it by the applied electrode-voltage to get the achieved
   breakdown-margin; compare against the required margin, absorbing the
   representation error at an exact-equality boundary rather than
   relaxing the margin.
5. For a decaying release, solve the outgassing-decay law for the time
   at which the local pressure drops below the level that clears the
   geometry, and record that as the high-voltage-activation inhibit
   duration.
6. Aggregate: the hardware is clear of clause 6.9 findings only when
   every release path is either below its Paschen-minimum, above the
   required breakdown-margin, or bounded by an activation-inhibit that
   the operations timeline honours.

## Pitfalls

- Comparing a pressure against a fixed "safe pressure" instead of
  forming the pressure-gap product. The same pressure is harmless
  across a one-millimetre gap and marginal across a ten-centimetre gap.
- Using an air Paschen curve for a released species. Xenon, water
  vapour, helium and carbon dioxide have markedly different ionisation
  and secondary-emission coefficients, and the substitution can move
  the minimum voltage by a factor of several.
- Treating the left branch of the curve as automatically safe without
  checking which side of the minimum the design sits on. The breakdown
  voltage rises on both sides of the minimum, so a "high voltage
  required" result is only meaningful once the branch is known.
- Assessing the on-orbit steady state and skipping the first hours
  after launch, when the water-desorption and material-outgassing rates
  are at their peak and the activation-inhibit window is set.
- Treating the exact-margin case as a failure because a product of
  floating-point powers landed a few units in the last place low. The
  representation error belongs in the comparison, not in the required
  margin.

## Behavior contract (gate 3)

The release-path categorisation, free-molecular density and pressure
model, Paschen-breakdown evaluation, Paschen-minimum location,
breakdown-margin decision and outgassing-decay inhibit logic are
exercised by the gate 3 contract test:
scripts/test_e2006_neutral_gas_discharge_triggering.py against
scripts/e2006_neutral_gas_discharge_triggering_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_neutral_gas_discharge_triggering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
