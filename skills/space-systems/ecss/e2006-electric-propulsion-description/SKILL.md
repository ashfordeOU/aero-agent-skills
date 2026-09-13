---
name: e2006-electric-propulsion-description
description: "Use when map an electric-propulsion unit onto its thruster family and the spacecraft-charging interactions its operation drives under ECSS-E-ST-20-06C clause 11.1.1: sort each designation into the electrostatic, electromagnetic or electrothermal family, derive exhaust-velocity, propellant mass-flow and extracted beam-current from thrust, specific-impulse and propellant ion-mass, decide whether the unit ejects a net charged beam and so needs an electron-emitting neutralizer, enumerate the charging interactions that follow -- beam-space-charge, charge-exchange-plasma-backflow, neutralizer-coupling-voltage, plume-sputter-deposition, floating-potential-shift -- check the declared input-power split, and raise a finding for an unneutralized beam or an undeclared propellant. Trigger: ecss-e-st-20-06c, clause-11-1-1, electric-propulsion-description, thruster-family-taxonomy, gridded-ion-thruster, hall-effect-thruster, beam-current-estimate, charge-exchange-plasma-backflow, neutralizer-requirement."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-electric-propulsion-description, ecss-e-st-20-06c, electric-propulsion-description, thruster-family-taxonomy, gridded-ion-thruster, hall-effect-thruster, charge-exchange-plasma-backflow, neutralizer-requirement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Electric-Propulsion Description (space-systems/ecss/e2006-electric-propulsion-description)

Use when the task is the introductory survey of ECSS-E-ST-20-06C
clause 11.1.1 -- naming the range of electric thrusters a spacecraft
may carry and stating, per unit, which spacecraft-charging
interactions its operation produces.

## Domain quick reference

- Electric thrusters sort into three acceleration families.
  Electrostatic units (gridded-ion, field-emission-electric-propulsion,
  colloid) extract ions or charged droplets across a biased gap.
  Electromagnetic units (hall-effect, pulsed-plasma,
  magnetoplasmadynamic) accelerate a plasma with a crossed or
  self-induced Lorentz force. Electrothermal units (arcjet, resistojet)
  heat a neutral propellant and expand it through a nozzle. The family
  is the first thing fixed, because it bounds the interaction set.
- The charging-relevant split is not the family but whether the exhaust
  carries net charge. A gridded-ion or hall-effect unit ejects a net
  ion current and leaves the spacecraft body an equal and opposite
  charge to shed; an ablation-fed or self-field plasma unit ejects a
  quasi-neutral exhaust; an electrothermal unit ejects neutral gas.
  Only the net-charge units impose an electron-emitting-neutralizer
  requirement, and that requirement is what clause 11.2 then sizes.
- Beam-current follows from the thrust and specific-impulse already in
  the propulsion budget: exhaust-velocity is specific-impulse times
  standard-gravity, mass-flow is thrust divided by exhaust-velocity,
  and beam-current is the ionised share of that mass-flow times the
  ion charge-to-mass ratio (elementary-charge times charge-state over
  ion mass). Xenon, krypton, argon and iodine give markedly different
  currents for the same thrust, so the propellant has to be declared.
- The interactions a unit produces are: beam-space-charge (net-charge
  units only), charge-exchange-plasma-backflow, floating-potential-shift,
  plume-sputter-deposition, neutralizer-coupling-voltage where a
  neutralizer is fitted, pulsed-electromagnetic-emission for
  electromagnetic units, and neutral-gas-pressure-rise for
  electrothermal units. A net-charge unit with no neutralizer instead
  produces unneutralized-beam-charging, which is a finding.

## Workflow

1. For each unit, sort the designation into its acceleration family
   and record the paraphrased acceleration mechanism. Reject an
   uncategorized designation before it enters the survey.
2. Derive exhaust-velocity from specific-impulse and mass-flow from
   thrust; reject a non-positive thrust or specific-impulse.
3. Decide whether the unit ejects net charge. If it does, require a
   declared propellant and compute beam-current from mass-flow, the
   ionised-share fraction and the ion charge-to-mass ratio; if it does
   not, record zero beam-current and no neutralizer requirement.
4. Where an input-power split is declared, confirm the shares are
   positive and do not exceed the input power, and carry the residual
   thermal share into the record.
5. Enumerate the charging interactions for the unit from its family and
   its neutralizer state.
6. Aggregate the set: union the interactions, sum the beam-currents,
   reject duplicate unit identifiers, and collect findings. The set is
   description-complete only when the finding list is empty.

## Pitfalls

- Reading the family as the neutralizer trigger. Electromagnetic covers
  both hall-effect, which ejects a net ion current, and pulsed-plasma,
  which does not; keying the neutralizer requirement off the family
  invents one requirement and misses another.
- Quoting the manufacturer beam-current for a unit throttled to a
  different operating point. Beam-current scales with the mass-flow
  actually commanded, so it is derived from the thrust and
  specific-impulse of the operating point being assessed.
- Assuming singly-charged ions. A doubly-charged population carries
  twice the current per unit mass-flow and shifts both the
  neutralizer-sizing and the sputter-yield estimate.
- Treating an electrothermal unit as charging-inert. It ejects no
  charge, but the neutral-gas-pressure-rise it produces can support a
  discharge near a high-voltage surface, so it stays in the survey.
- Leaving the propellant undeclared and computing a current anyway.
  The charge-to-mass ratio differs by a factor of three across the
  qualified propellants; an undeclared propellant is a finding, not a
  default.

## Behavior contract (gate 3)

The family sorting, beam-current derivation, power-split validation
and interaction-enumeration logic is exercised by the gate 3 contract
test: scripts/test_e2006_electric_propulsion_description.py against
scripts/e2006_electric_propulsion_description_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_electric_propulsion_description.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
