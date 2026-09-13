---
name: e2006-sputtering-simulation-analysis
description: "Use when compute sputter erosion of spacecraft external surfaces from simulated ion trajectories under ECSS-E-ST-20-06C clause 11.3.4: categorize every simulated ion population as primary-beam, beam-wing, charge-exchange or backflow, decide whether its trajectory crosses the angular span a surface subtends from the thruster exit-plane, evaluate the energy-dependent and incidence-angle-dependent sputter-yield of the target material against its sputter-threshold, integrate the removed thickness across the firing duration, and compare that erosion-depth with the erosion-allowance held for the surface while confirming the trajectory sample-count clears the simulation-fidelity floor. Trigger: ecss, e-st-20-electrical-scope, e2006-sputtering-simulation-analysis, sputter-erosion, ion-trajectory-simulation, charge-exchange-ion-flux, electric-propulsion-plume, sputter-yield, erosion-depth-allowance, thruster-exit-plane-geometry."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-sputtering-simulation-analysis, sputter-erosion, ion-trajectory-simulation, charge-exchange-ion-flux, electric-propulsion-plume, sputter-yield, erosion-depth-allowance]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical Scope — Sputtering Simulation Analysis (space-systems/ecss/e2006-sputtering-simulation-analysis)

Use when the task is the ion-trajectory sputter-erosion analysis of
ECSS-E-ST-20-06C clause 11.3.4 -- turning the trajectories produced by an
electric-propulsion plume simulation into a removed-thickness number for
each external surface reached during normal thruster operation, and
checking that number against the erosion-allowance carried by the surface.

## Domain quick reference

- Clause 11.3.4 asks for simulated ion trajectories, not a bounding
  flux. A plume simulation delivers several distinct ion populations and
  each is categorized before it is used: primary-beam ions inside the
  dense core half-angle, beam-wing ions at the same energy but wider
  emission angle, charge-exchange ions produced by resonant exchange
  with plume neutrals (slow, broadly distributed, and the dominant
  erosion driver on surfaces outside the core), and backflow ions
  emitted past the exit-plane towards the vehicle body.
- A population only erodes a surface it geometrically reaches. Each
  surface subtends an angular span seen from the thruster exit-plane;
  a trajectory whose emission angle falls outside that span contributes
  nothing and is dropped rather than kept as a worst case.
- Removal rate is governed by the sputter-yield, the atoms ejected per
  incident ion. It is exactly zero at or below the sputter-threshold of
  the target material, grows with the excess energy, rolls off at high
  energy as the ion deposits its momentum below the near-surface layer,
  and is scaled by an incidence-angle factor that is unity at normal
  incidence, rises through oblique incidence, and collapses at grazing
  incidence where the ion reflects instead of sputtering.
- The yield is converted to a depth through the atomic volume implied by
  the target molar mass and density, integrated over the firing
  duration, and summed over every population reaching the surface. The
  surface is compliant when that depth sits within the erosion-allowance
  set by the thermal, optical or electrical requirement owning it.
- Statistical adequacy is part of the result. A population carried by
  too few simulated trajectories yields a depth with no defensible
  confidence, so the sample-count is a recorded, checkable quantity.

## Workflow

1. Normalize every simulated ion population: resolve the propellant ion
   species and charge state, convert the net acceleration voltage into a
   per-ion energy, and read the emission angle, the incident flux and
   the trajectory sample-count. Reject an unrecognized species or a
   non-positive acceleration voltage before it enters the analysis.
2. Categorize each population as primary-beam, beam-wing,
   charge-exchange or backflow from its energy and emission angle, so
   the erosion contribution can later be attributed to a physical
   mechanism rather than an anonymous flux.
3. For each external surface, test every population against the angular
   span the surface subtends from the exit-plane. Drop the pairs that do
   not intercept; for the rest, take the incidence angle as the offset
   between the trajectory and the surface normal.
4. Evaluate the sputter-yield for the species, target material, ion
   energy and incidence angle. Return zero at or below the material
   sputter-threshold and at or beyond the grazing limit.
5. Convert the yield into a removed thickness using the incident flux,
   the firing duration and the atomic volume of the target material, and
   sum the contributions across every population reaching the surface.
6. Compare the summed depth with the erosion-allowance on record. Flag
   an exceedance; flag separately a surface that ion trajectories do
   reach but which carries no allowance at all, and flag any population
   whose trajectory sample-count sits below the fidelity floor.
7. Aggregate across the campaign: report the worst-eroded surface and
   treat the analysis as closed only when no surface carries a finding.

## Pitfalls

- Analysing only the primary-beam population and declaring surfaces
  outside the core safe. Charge-exchange ions are slow but spread over a
  far wider solid angle and are usually what erodes radiators, antenna
  feeds and solar-array surfaces; omitting them understates the depth on
  exactly the surfaces the clause is protecting.
- Applying a single normal-incidence yield to every surface. The
  incidence-angle factor varies by more than an order of magnitude
  between normal and near-grazing incidence, and it does not vary
  monotonically -- it rises with obliquity then collapses at the grazing
  limit, so taking the normal value as conservative is wrong in one
  direction and the grazing value as conservative is wrong in the other.
- Treating a sub-threshold impact as a small erosion rate instead of
  zero. Below the material sputter-threshold no atom leaves the surface,
  and smearing a nominal rate across a long firing duration manufactures
  a depth that the physics does not produce.
- Leaving the erosion-allowance unset and reading "no exceedance" as
  compliance. An absent allowance means the owning requirement was never
  captured for that surface; that is itself a finding, not a pass.
- Accepting a depth from a population carried by a handful of simulated
  trajectories. The clause calls for simulated trajectories because the
  angular distribution matters; too thin a sample gives an angular
  distribution, and therefore a depth, that is not reproducible.

## Behavior contract (gate 3)

The population-categorization, trajectory-interception, sputter-yield,
erosion-depth and allowance-comparison logic is exercised by the gate 3
contract test: scripts/test_e2006_sputtering_simulation_analysis.py
against scripts/e2006_sputtering_simulation_analysis_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2006_sputtering_simulation_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
