---
name: e2006-thruster-neutral-gas-effects
description: "Use when verify that neutral gas emitted by an electric-propulsion thruster leaves the local plasma-density too low to sustain an electrical discharge under ECSS-E-ST-20-06C clause 11.2.5: categorize every gas-emission source (beam-directed efflux, unionized-propellant, neutralizer-flow, valve-leak), propagate the plume number-density to each high-voltage-surface including the backflow region behind the exit plane, convert it to a local-gas-pressure and an electron-mean-free-path, evaluate the Paschen-breakdown-voltage of each biased gap against its applied-bias, derive the ionized-plasma-density from the ionization-fraction, and record the discharge-margin evidence the clause demands. Trigger: ecss, e-st-20-electrical-scope, thruster-neutral-gas, plume-backflow, neutral-number-density, paschen-breakdown, discharge-inception, ionization-fraction, high-voltage-surface."
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
  tags: [ecss, e-st-20-electrical-scope, e2006-thruster-neutral-gas-effects, thruster-neutral-gas, plume-backflow, neutral-number-density, paschen-breakdown, discharge-inception, high-voltage-surface]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electric Propulsion — Thruster Neutral Gas Effects (space-systems/ecss/e2006-thruster-neutral-gas-effects)

Use when the task is the clause 11.2.5 evidence of ECSS-E-ST-20-06C: showing
that the neutral gas a thruster emits raises the plasma-density around the
spacecraft's high-voltage-surfaces too little to strike or sustain an
electrical discharge, and that the demonstration rests on a computed
number-density field rather than an assertion.

## Domain quick reference

- A thruster emits neutral gas from four distinct sources, and each is
  categorized before its density is propagated: beam-directed efflux
  (propellant that left with the accelerated beam), unionized-propellant
  (neutral fraction that traversed the discharge-chamber without being
  ionized), neutralizer-flow (the cathode's own gas feed), and valve-leak
  (internal-leakage past a closed feed valve). An uncategorized source type
  is rejected, never silently treated as beam-directed.
- The neutral field of a point-like emitter in free-molecular expansion is a
  cosine-power lobe: the number-density at range r and off-axis angle theta
  falls as the emitted particle-rate divided by exhaust-speed and r-squared,
  weighted by a normalized cosine-power directionality. Behind the exit plane
  (theta above ninety degrees) the lobe is zero, so the backflow region is
  modelled separately as a small named fraction of the on-axis directionality
  decaying exponentially with angle. Backflow is the branch that actually
  reaches rear-mounted high-voltage-surfaces, and dropping it is the classic
  way a neutral-gas case passes on paper.
- A discharge needs three things simultaneously: an electron-mean-free-path
  shorter than the gap (below that the gap is collisionless and no avalanche
  can multiply), an applied-bias at or above the Paschen-breakdown-voltage for
  the pressure-gap-product of that gap, and an ionized-plasma-density at or
  above the density that sustains the discharge once struck. Clause 11.2.5 is
  satisfied by breaking any one of the three with a stated margin — the
  density criterion is the one the clause names, the other two are the
  supporting physics.
- Paschen's fit is only single-valued above its own minimum: below a
  pressure-gap-product threshold the logarithm argument drops to unity or
  less and no breakdown voltage exists at any bias. That is a pass, but it
  must be reported as "no breakdown branch", not as a numeric margin.

## Workflow

1. Categorize each gas-emission source of the thruster and reject any source
   type outside the four recognized families.
2. For every (source, high-voltage-surface) pair compute the neutral
   number-density at the surface from emitted mass-flow, species mass,
   exhaust-speed, range and off-axis angle, using the forward cosine-power
   lobe ahead of the exit plane and the decaying backflow branch behind it.
   Sum the contributions per surface.
3. Convert the summed number-density into a local-gas-pressure at the surface
   gas-temperature and into an electron-mean-free-path at the ionization
   cross-section.
4. Evaluate the Paschen-breakdown-voltage for each biased gap from the
   pressure-gap-product, the gas fit coefficients and the
   secondary-emission coefficient; report no-breakdown-branch when the fit
   has no solution.
5. Derive the ionized-plasma-density from the neutral number-density and the
   local ionization-fraction, and compare it with the sustaining threshold.
6. Declare the surface compliant when at least one of the three criteria is
   broken with margin; record the governing criterion and the margin ratio as
   the clause 11.2.5 evidence. A surface with no declared bias, no gap or no
   ionization-fraction on record is an evidence gap, not a pass.

## Pitfalls

- Evaluating only the forward lobe and reporting zero density behind the
  exit plane — rear-mounted high-voltage-surfaces are reached through the
  backflow branch, and omitting it removes the only path that mattered.
- Reading "applied-bias below the Paschen-breakdown-voltage" as a complete
  case while the ionized-plasma-density sits above the sustaining threshold:
  an externally-supplied plasma keeps a discharge alive at a bias far under
  the striking voltage, so the density criterion is evaluated in its own
  right.
- Treating an absent breakdown solution as a failure of the calculation. Below
  the Paschen minimum the fit genuinely has no root; the correct record is
  no-breakdown-branch with the pressure-gap-product that produced it.
- Leaving the ionization-fraction unset and reading the resulting zero plasma
  density as compliance — an unset fraction means the ionization state was
  never assessed, which is itself a clause finding.
- Widening the sustaining-density limit to make a boundary case pass. A value
  that equals the limit to within the named representation tolerance is
  compliant by absorbing the floating-point error, never by moving the limit.

## Behavior contract (gate 3)

The source-categorization, plume and backflow density, pressure,
mean-free-path, Paschen, ionization and discharge-margin logic is exercised by
the gate 3 contract test: scripts/test_e2006_thruster_neutral_gas_effects.py
against scripts/e2006_thruster_neutral_gas_effects_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2006_thruster_neutral_gas_effects.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
