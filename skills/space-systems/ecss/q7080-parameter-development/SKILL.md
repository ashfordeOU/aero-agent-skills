---
name: q7080-parameter-development
description: "Develop powder-bed build parameters for one material from a density-optimisation campaign. Use when a trial matrix of coupons has been run and the parameter set to release has to be chosen and defended: form the volumetric energy density of every trial, convert coupon density into relative density and porosity, group each trial as lack-of-fusion, stable or keyhole against the declared energy band, keep the densest stable trial meeting the target and break ties towards the lower energy, then raise a finding when the campaign is too small, explored too few energy points, or landed its optimum on the edge of the span it explored. Trigger: ecss, q-st-70-80-additive-manufacturing, am-parameter-development, am-volumetric-energy-density, am-density-optimisation, am-trial-matrix-bracketing, am-keyhole-lack-of-fusion-regimes."
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
  tags: [ecss, q-st-70-80-additive-manufacturing, q7080-parameter-development, am-parameter-development, am-volumetric-energy-density, am-density-optimisation, am-trial-matrix-bracketing, am-keyhole-lack-of-fusion-regimes]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Additive Manufacturing — Parameter Development (space-systems/ecss/q7080-parameter-development)

Use when the task is the process clause of ECSS-Q-ST-70-80 that develops
build parameters for a material: deciding which beam power, scan speed,
hatch spacing and layer thickness are released for that feedstock, and
whether the campaign that produced them actually justifies the choice.

## Domain quick reference

- Parameters belong to a material, not to a machine or a part. A set
  developed on one alloy says nothing about the next one, so a trial run
  on a different feedstock is foreign evidence and is refused rather
  than averaged into the matrix.
- The four primary parameters act through one quantity. Volumetric
  energy density E = P / (v * h * t) collapses beam power, scan speed,
  hatch spacing and layer thickness into the energy delivered per unit
  of consolidated material, which is why two different-looking sets can
  behave identically and a single-parameter sweep can miss the optimum.
- Density is the objective, and it has two failure directions. Below the
  stable band the melt pool does not overlap and lack-of-fusion voids
  appear; above it the pool goes into a keyhole and traps gas porosity.
  Both show up as lost density, so a density number alone does not say
  which way the process failed.
- The densest trial is not automatically the one to release. Where two
  sets reach the same density, the lower energy one runs cooler, builds
  faster in most geometries and leaves more room before the keyhole
  boundary, so it is the defensible choice.
- An optimum on the edge of the explored span is not an optimum. It is
  the best point of a matrix that stopped too early, and the true peak
  may lie outside where nothing was measured.
- Relative density is a quotient of measured masses. A coupon exactly on
  the target can land a few units in the last place below it, which the
  comparison absorbs; the target itself is never relaxed.

## Workflow

1. Validate the campaign material, the fully dense reference and the
   declared stable energy band. An inverted or degenerate band cannot
   group anything, and is an input error rather than a wide window.
2. Validate all four primary parameters of every trial. A missing or
   non-positive parameter is refused, because an energy density formed
   from an assumed value evidences a process nobody ran.
3. Form the volumetric and linear energy densities per trial, and reject
   any trial declaring a feedstock other than the campaign material.
4. Convert each coupon density into a relative density and porosity, and
   refuse a measurement above the reference beyond measurement scatter:
   the units or the reference are wrong, not the coupon.
5. Group each trial as lack-of-fusion, stable or keyhole, treating an
   exact band edge as inside the band.
6. Keep the densest stable trial that meets the target, breaking ties
   towards the lower energy density and returning nothing at all when no
   stable trial reaches it.
7. Raise campaign findings independently of the selection: too few
   trials, too few distinct energy points, and a selected optimum
   sitting on an edge of the explored span. Release only when a set was
   selected and no finding stands.

## Pitfalls

- Reading a high density as a qualified parameter set. The coupon says
  the material consolidated at that energy once; the campaign findings
  say whether the matrix around it was ever explored.
- Selecting on density alone across regimes. A keyhole trial can post a
  respectable density while trapping gas porosity that the section plane
  happened to miss, so the regime filter comes before the ranking.
- Sweeping one parameter and calling it a matrix. Energy density moves
  with all four, and a speed-only sweep at fixed power explores a line
  through a space that has to be bracketed in at least two directions.
- Carrying a parameter set to a new feedstock lot or alloy because the
  machine is the same. The melt behaviour follows the powder, which is
  why development is per material.
- Widening the stable band to take in a trial that performed well. That
  redefines the regime boundary from the single point that was supposed
  to be graded against it.

## Behavior contract (gate 3)

The parameter validation, energy-density formation, regime grouping,
relative-density conversion, optimum selection with its tie-break and
the campaign bracketing findings are exercised by the gate 3 contract
test: scripts/test_q7080_parameter_development.py against
scripts/q7080_parameter_development_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_q7080_parameter_development.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
