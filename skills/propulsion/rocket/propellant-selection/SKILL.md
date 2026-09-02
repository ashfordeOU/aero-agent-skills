---
name: propellant-selection
description: "Use when you must select and screen rocket propellants for a mission: classify propellant families (cryogenic, storable, hypergolic, solid, hybrid), compare specific impulse and density impulse, compute the mixture bulk density and the O/F ratio optimum, derive the required propellant mass fraction from a delta-v budget with the rocket equation, and judge storability and handling for the mission. Produces the propellant family classification, the density-impulse ranking, the O/F verdict, the mass fraction, and the suitability verdict, in SI units (s, kg/m^3, m/s). Trigger: propellant selection, specific impulse, density impulse, mixture ratio, O/F ratio, hypergolic, cryogenic, storable, solid propellant, storability."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: propulsion
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [propellant-selection, specific-impulse, density-impulse, mixture-ratio, o-f-ratio, hypergolic, cryogenic, storable, solid-propellant, storability]
  version: 0.1.0
  author: Aero Agent Skills
---

# Propellant Selection (propulsion/rocket/propellant-selection)

Use when the task is rocket propellant selection for a mission:
propellant families, specific impulse, density impulse, mixture ratio
and bulk density, O/F ratio optimum, storability and handling, and the
propellant mass fraction from the delta-v budget.

## Domain quick reference

- Propellant families: cryogenic (LOX, LH2, LCH4), storable
  (RP-1, H2O2), hypergolic (MMH/UDMH with NTO or IRFNA, ignites on
  contact), solid (HTPB/APCP composite grain), and hybrids.
- Specific impulse Isp (s) measures propellant performance; density
  impulse = Isp * bulk density (kg s/m^3) measures it per unit tank
  volume, the figure that drives tank and vehicle size.
- The mixture bulk density at an O/F mass ratio r, fuel density rho_f,
  and oxidizer density rho_o is rho = (1 + r) / (1/rho_f + r/rho_o).
- The propellant mass fraction needed for a delta-v at Isp is
  1 - exp(-delta_v / (g0 * Isp)), with g0 = 9.80665 m/s^2. It is the
  inverted rocket equation, kept lightweight here: staging and stage
  masses live in the rocket-sizing skill.
- The O/F ratio optimum sits near the maximum Isp; running away from it
  trades performance for bulk density and burn time.
- Storability decides the mission: cryogens boil off, hypergolics and
  storables hold indefinitely, solids cannot throttle or restart.
- ECSS space-systems standards frame the launch-vehicle propulsion
  context.

## Workflow

1. Name the candidate propellants and classify each with
   propellant_family.
2. Rank candidates on specific impulse and density impulse with
   density_impulse.
3. Compute the mixture bulk density with bulk_density at the chosen
   O/F ratio.
4. Check the O/F ratio against the optimum with o_f_optimum_verdict.
5. Derive the required propellant mass fraction with
   required_mass_fraction from the delta-v budget.
6. Screen storability and handling for the mission with
   propellant_verdict.

## Pitfalls

- Ranking on Isp alone while ignoring density impulse: a dense
  low-Isp pair can beat a light high-Isp pair on tank volume.
- Treating hypergolic as separate from storable: hypergolics are
  storables that ignite on contact, not a third liquid state.
- Computing bulk density as an arithmetic mean of the two densities
  instead of the mass-weighted harmonic mean.
- Confusing the mixture ratio (O/F) with the rocket equation mass
  ratio (m0/mf).
- Expecting solid motors to throttle, shut down, or restart.
- Ignoring boil-off and loading time for cryogens on long-duration or
  quick-response missions.

## Behavior contract (gate 3)

The family classification, density impulse, bulk density, O/F verdict,
mass fraction, and mission verdict logic is exercised by the gate 3
contract test: scripts/test_propellant_selection.py against
scripts/propellant_selection_logic.py (stdlib unittest, offline). Run:
python3 skills/propulsion/rocket/propellant-selection/scripts/test_propellant_selection.py

## Compliance

- Standards referenced, not reproduced: ECSS is a free ESA download
  (ecss.nl/standards); propellant performance and selection methodology
  is standard propulsion practice, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
