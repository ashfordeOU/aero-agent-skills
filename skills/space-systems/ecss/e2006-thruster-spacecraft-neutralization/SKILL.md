---
name: e2006-thruster-spacecraft-neutralization
description: "Use when verify that the electron-emitting neutralizer of an electric-propulsion unit holds emission capacity above the extracted beam-current plus the natural charging currents of the worst-case environment, under ECSS-E-ST-20-06C clause 11.2.1: compute the random-flux electron and ion collection currents from ambient plasma-density and plasma-temperature, add photoemission, secondary-electron and backscattered-electron escape currents, net them into the natural current driving the body positive, give an electron-rich plasma no credit against the beam, apply the sizing-margin, rank the mission environments to find the worst case, and grade the declared emission capability against it. Trigger: ecss-e-st-20-06c, clause-11-2-1, neutralizer-emission-capacity, beam-current-neutralization, worst-case-charging-environment, photoemission-current, secondary-electron-emission, spacecraft-floating-potential."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-thruster-spacecraft-neutralization, ecss-e-st-20-06c, neutralizer-emission-capacity, beam-current-neutralization, worst-case-charging-environment, photoemission-current, secondary-electron-emission]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Spacecraft Charging — Thruster/Spacecraft Neutralization (space-systems/ecss/e2006-thruster-spacecraft-neutralization)

Use when the task is sizing or checking the neutralizer of an
electric-propulsion unit against ECSS-E-ST-20-06C clause 11.2.1 --
proving the emission capacity stays above the beam-current the thruster
extracts plus the natural charging currents the spacecraft sees in the
worst-case environment of the mission.

## Domain quick reference

- An ion-extracting thruster removes positive charge from the
  spacecraft at the beam-current rate. Without an equal electron
  emission the body charges negative until the beam is electrostatically
  returned to it, so the neutralizer requirement is a current-balance
  requirement, not a comfort factor.
- The balance is not the beam alone. Sunlit surfaces lose electrons by
  photoemission, energetic electrons striking a surface release
  secondary and backscattered electrons, and collected ambient ions
  deposit positive charge. All four drive the body positive and add to
  the electron current the neutralizer must supply. Collected ambient
  electrons are the only natural term supplying negative charge.
- The natural terms are computed from the random-flux current density
  of a Maxwellian population, q n sqrt(kT / 2 pi m), applied over the
  exposed collecting area. The electron flux exceeds the ion flux for
  the same density and temperature by roughly the square-root of the
  mass ratio, which is why a dense cold plasma over-supplies electrons
  while a hot tenuous plasma does not.
- Worst case is per-environment, not per-term. A hot tenuous
  geosynchronous substorm plasma with a large sunlit area produces a
  net positive-driving current; a dense cold low-Earth-orbit plasma
  over-supplies electrons. The requirement is evaluated in each
  declared environment and the largest demand is the sizing case.
- An electron-rich environment earns no credit against the beam. The
  natural term is floored at zero before the margin is applied, because
  the plasma cannot be relied on to return beam charge and the thruster
  can fire while the spacecraft passes into a depleted region.

## Workflow

1. Validate each declared environment: name, ambient electron density
   and temperature, collecting area, sunlit area (never larger than the
   collecting area), optional ion population, secondary-emission yield,
   backscatter current and photoemission density.
2. Per environment, compute the ambient electron and ion collection
   currents from the random-flux density over the collecting area, the
   photoemission current over the sunlit area, and the
   secondary-electron current from the collected electron current and
   the surface yield.
3. Sum the positive-driving terms (photoemission, secondary emission,
   backscatter, collected ions) and subtract the collected electron
   current to get the net natural current.
4. Floor a negative net natural current at zero, add the beam-current,
   and multiply by the agreed sizing margin to get the required
   emission capacity for that environment.
5. Rank the environments by required capacity, breaking ties by name,
   and take the largest as the sizing case.
6. Grade the declared neutralizer capability against that requirement,
   reporting utilisation and any shortfall. Raise a separate finding
   when the natural current alone exceeds the beam-current, which means
   the environment, not the thruster, sets the emission demand.

## Pitfalls

- Sizing the neutralizer on the beam-current alone. The natural terms
  are small against a several-ampere beam but dominate a low-thrust or
  throttled-down operating point, where they can exceed it.
- Crediting ambient electron collection against the beam. A dense
  plasma does supply electrons, but it is not present in every part of
  the orbit and it is not a controlled source; the credit is floored at
  zero, which is what the workflow enforces.
- Evaluating the environment terms separately and summing the worst of
  each. The terms trade against one another inside one environment --
  the plasma that maximises photoemission-driven demand also maximises
  electron collection -- so the worst case is chosen per environment.
- Using the electron temperature for the ion population by default and
  forgetting to say so. The default is explicit here; a mission with a
  distinct ion temperature must declare it, or the ion collection term
  is wrong in both magnitude and sign of its effect on the margin.
- Grading a capability that equals the requirement with a bare
  arithmetic comparison. Both sides are sums and products of
  floating-point terms, so an exactly compliant unit can land a few
  units in the last place low; absorb that representation error rather
  than raising the required capacity.

## Behavior contract (gate 3)

The random-flux current densities, photoemission and
secondary-electron terms, environment current-balance, worst-case
ranking, margin application and capability grading are exercised by the
gate 3 contract test:
scripts/test_e2006_thruster_spacecraft_neutralization.py against
scripts/e2006_thruster_spacecraft_neutralization_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_thruster_spacecraft_neutralization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
