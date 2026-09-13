---
name: e2001-single-carrier-analysis-levels
description: "Use when evaluate which of the two design-analysis-levels of ECSS-E-ST-20-01C clause 4.6.2.1 applies to a single-carrier multipactor assessment: reduce the gap geometry to a chart-representable family, compute its frequency-gap-product, check that product against the charted band of the electrode material, confirm the gap stays quasi-static against the operating wavelength, and admit the simplified level-one route only when every applicability condition holds; otherwise route the case to the detailed level-two numerical-modelling path and verify its prerequisites, a validated electromagnetic-field solver, traceable secondary-electron-yield data and an electron-seeding model. Trigger: ecss, e-st-20-electrical-scope, single-carrier-multipactor, design-analysis-level-one, design-analysis-level-two, frequency-gap-product, susceptibility-chart-band, quasi-static-gap-check, secondary-electron-yield-data."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-single-carrier-analysis-levels, single-carrier-multipactor, design-analysis-level-one, design-analysis-level-two, frequency-gap-product, susceptibility-chart-band, secondary-electron-yield-data]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Single-Carrier Design Analysis Levels (space-systems/ecss/e2001-single-carrier-analysis-levels)

Use when the task is the route decision of ECSS-E-ST-20-01C clause
4.6.2.1 -- deciding, gap by gap, whether a single-carrier multipactor
case may be closed by the simplified level-one chart route or has to be
carried through the detailed level-two numerical-modelling route, and
what each route obliges the assessment to have on record.

## Domain quick reference

- Level one is the chart route. It reduces a gap to an equivalent
  parallel-plate configuration, forms the frequency-gap-product (the
  carrier frequency in gigahertz times the electrode separation in
  millimetre), and reads the breakdown level off a published
  susceptibility curve for the electrode material. It is fast and
  auditable, and it is only valid inside the envelope those curves
  were built for.
- That envelope has four gates. The geometry must reduce to a
  chart-representable family with a near-uniform separation; the
  electrode material must be one of the charted reference surfaces;
  the frequency-gap-product must fall inside that material's charted
  band; and the gap must be electrically small against the operating
  wavelength, so the field crossing it is quasi-static rather than
  varying along the electron transit. A dielectric filling the gap or
  a static magnetic field across it also puts the case outside the
  chart basis, because both change the electron trajectory the curves
  assume.
- Level two is the modelling route: a full electromagnetic-field
  solution of the actual geometry combined with electron-trajectory
  tracking against project secondary-electron-yield data. It replaces
  the chart envelope with a model, which is why it carries
  prerequisites of its own -- a solver validated against reference
  cases, a traceable yield dataset for the real surface finish, a
  stated electron-seeding model and convergence evidence for the
  chosen discretisation and particle count.
- The two routes are not interchangeable defaults. Level two is always
  admissible; level one is admissible only when every applicability
  gate holds. Requesting level one for a case that fails a gate is the
  error this leaf exists to catch, and the answer is to re-route the
  case, not to relax the gate.

## Workflow

1. Confirm the case is single-carrier. A condition declaring more than
   one carrier belongs to the multi-carrier clause and is rejected
   here rather than graded against single-carrier applicability.
2. Categorize the gap geometry into a family and record whether it
   reduces to a chart-representable equivalent parallel-plate gap;
   check the separation uniformity against the declared limit, since
   a strongly tapered gap has no single equivalent separation.
3. Compute the frequency-gap-product from the carrier frequency and
   the electrode separation, and compare it with the charted band of
   the electrode material; an unknown material is a blocker, not a
   nearest-neighbour substitution.
4. Compute the ratio of the separation to the operating wavelength and
   check it against the quasi-static limit. Treat a ratio exactly at
   the limit as satisfied -- the comparison runs to a declared
   tolerance so a derived ratio landing a few units in the last place
   high is not read as a failure.
5. Collect the blockers. With none, level one is admissible; with any,
   the case routes to level two and every blocker is carried into the
   rationale so the route decision is reviewable.
6. For a level-two case, check the prerequisites on record and report
   each missing one. The assessment is not ready to start until the
   selected route has no open prerequisite.

## Pitfalls

- Reading a susceptibility curve outside its charted band because the
  frequency-gap-product is "only slightly" past the end. The curve has
  no data there; extrapolating it silently invents a breakdown level.
- Substituting the nearest charted material for an uncharted surface
  finish. Secondary-emission behaviour is a surface property, and a
  coating or treatment can move the yield far more than the base metal
  does.
- Applying the chart route to an electrically large gap. Once the
  separation is an appreciable fraction of the wavelength, the field
  varies during the electron transit and the resonance condition the
  curves assume no longer describes the gap.
- Selecting level two and treating the choice itself as the
  justification. Level two moves the burden onto the model: without a
  validated solver, traceable yield data, a seeding model and
  convergence evidence, the detailed route is weaker than the chart it
  replaced.
- Grading a tapered or stepped gap on its minimum separation alone.
  The equivalent parallel-plate reduction needs a near-uniform gap;
  when it is not, the case is a level-two geometry.

## Behavior contract (gate 3)

The geometry reduction, frequency-gap-product computation, charted-band
and quasi-static gates, route selection and level-two prerequisite
check are exercised by the gate 3 contract test:
scripts/test_e2001_single_carrier_analysis_levels.py against
scripts/e2001_single_carrier_analysis_levels_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_single_carrier_analysis_levels.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
