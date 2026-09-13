---
name: e2001-level-one-geometry-criteria
description: "Use when screen a radio-frequency gap under ECSS-E-ST-20-01C clause 5.3.2.2.2 to decide whether the first multipactor analysis level applies: categorize the critical-region gap as a parallel-plate or a coaxial shape, reject shapes the level-one charts never covered, derive the effective gap from the plate separation or from the coaxial radius difference, check the quasi-parallel tilt tolerance and the surface-extent-to-gap ratio that keeps edge effects negligible, confirm the coaxial radius ratio sits inside the charted band, compute the frequency-gap product and verify it falls inside the charted range, then escalate every gap that fails a criterion to a level-two or three-dimensional treatment. Trigger: ecss, e-st-20-01c, e-st-20-electrical-scope, multipactor-geometry-criteria, parallel-plate-gap, coaxial-gap, frequency-gap-product, level-one-multipaction-screening, critical-region-gap, edge-effect-ratio."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-level-one-geometry-criteria, multipactor-geometry-criteria, parallel-plate-gap, coaxial-gap, frequency-gap-product, level-one-multipaction-screening]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Level-One Geometry Criteria (space-systems/ecss/e2001-level-one-geometry-criteria)

Use when the task is the geometry gate of ECSS-E-ST-20-01C clause
5.3.2.2.2 -- deciding whether a radio-frequency gap is simple enough to
be assessed with the first analysis level, whose charts are built for
parallel or coaxial gap shapes, and escalating every gap that is not.

## Domain quick reference

- The first analysis level replaces a field solution with a chart
  lookup, so it is only admissible where the gap resembles the shape
  the chart was derived for: two quasi-parallel facing surfaces, or
  the annular gap of a coaxial line. A gap that resembles neither --
  a wedge, a stepped iris, a corrugated surface, a dielectric-loaded
  gap -- is uncategorized at this level and goes to a level-two or
  three-dimensional treatment instead of being forced into a chart.
- The effective gap is the quantity the chart is indexed on. For a
  plane gap it is the separation of the facing surfaces. For an
  annular gap it is the radial difference of the outer and inner
  conductor radii, which is only a fair stand-in while the radius
  ratio stays inside a modest band; a very thin or a very wide annulus
  curves the field enough that the plane-gap equivalence breaks.
- Two shape tolerances protect the plane-gap idealisation. The facing
  surfaces must be quasi-parallel, because a residual wedge angle
  makes the resonant condition drift across the gap, and their extent
  must be large against the separation, because a short overlap lets
  electrons leave sideways before a resonant trajectory establishes.
- The chart itself is only drawn over a finite frequency-gap band. A
  product below the charted floor or above its ceiling is outside the
  charted evidence, and reading a threshold there is extrapolation,
  not a lookup -- it is a finding, not a pass.
- The gap with the smallest frequency-gap product drives the
  assessment: it sits deepest in the susceptible part of the chart, so
  it is the region carried into the single-carrier or multicarrier
  method of the following clauses.

## Workflow

1. Inventory every critical region of the item and record each gap's
   declared shape, dimensions and, for a plane gap, its facing-surface
   extent and residual tilt. Reject an unrecognized shape descriptor
   before it enters the screen.
2. Categorize each gap as parallel-plate, coaxial, or uncategorized.
   An uncategorized gap is escalated immediately, with no effective
   gap and no chart entry.
3. Derive the effective gap: the plate separation for a plane gap, the
   outer-minus-inner radius for an annular gap. Reject radii that do
   not describe a physical annulus.
4. Apply the shape tolerances. For a plane gap, check the
   surface-extent-to-gap ratio against the edge-effect limit and the
   tilt against the quasi-parallel limit. For an annular gap, check
   the radius ratio against the charted band floor and ceiling.
5. Compute the frequency-gap product from the operating frequency and
   the effective gap, and verify it lies inside the charted band.
6. Collect the findings per gap. A gap with an empty finding list is
   eligible for the level-one chart lookup; any finding escalates that
   gap to the higher analysis level.
7. Select the eligible gap with the smallest frequency-gap product as
   the driving region and carry it into the single-carrier or
   multicarrier level-one method.

## Pitfalls

- Forcing an uncategorized shape into the nearest chart by quoting an
  equivalent gap -- the chart's trajectory assumptions do not hold
  there, and the resulting threshold is unsupported rather than
  conservative.
- Treating the radial difference of a coaxial gap as a plane gap
  whatever the radius ratio -- the equivalence is only defensible
  inside a band, and a very thin or very wide annulus falls outside it.
- Checking the gap dimension but not the facing-surface extent -- a
  small, locally parallel patch passes a separation check and still
  fails the quasi-infinite-plate assumption the chart rests on.
- Extrapolating the chart past its plotted frequency-gap range and
  reading the extrapolated number as a threshold.
- Screening only the nominal gap and ignoring the manufacturing and
  thermal excursions that make it smaller, so the region actually
  driving the assessment is never screened.
- Reading "no violation" as eligible when the tilt or extent was never
  recorded -- a missing input is an incomplete screen, not a pass.

## Behavior contract (gate 3)

The shape-categorization, effective-gap, shape-tolerance,
frequency-gap-product and escalation logic is exercised by the gate 3
contract test: scripts/test_e2001_level_one_geometry_criteria.py
against scripts/e2001_level_one_geometry_criteria_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_level_one_geometry_criteria.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
