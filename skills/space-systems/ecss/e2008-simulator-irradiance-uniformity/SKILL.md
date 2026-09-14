---
name: e2008-simulator-irradiance-uniformity
description: "Evaluate how evenly a solar simulator spreads irradiance over the nominated test plane under ECSS-E-ST-20-08C clause 10.1.2: validate the declared plane and the sampling policy, refuse a grid too sparse or one bunched over part of the plane only, take the spatial non-uniformity between the extreme readings rather than as a scatter about the mean, name the brightest and dimmest points, categorize the plane against the declared bands, and hold the spread under the limit the measurement was quoted at. Use when a simulator test plane is being mapped, or an existing map has to be judged before a performance measurement is trusted. Trigger: ecss, e-st-20-08c-clause-10-1-2, solar-simulator-irradiance-uniformity, test-plane-irradiance-mapping, spatial-non-uniformity-percent, simulator-uniformity-sampling-grid, test-plane-coverage-fraction."
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
  tags: [ecss, e-st-20-08-photovoltaic-assembly-scope, e2008-simulator-irradiance-uniformity, solar-simulator-irradiance-uniformity, test-plane-irradiance-mapping, spatial-non-uniformity-percent, simulator-uniformity-sampling-grid, test-plane-coverage-fraction]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Photovoltaic Assemblies -- Simulator Irradiance Uniformity (space-systems/ecss/e2008-simulator-irradiance-uniformity)

Use when the task is clause 10.1.2 of ECSS-E-ST-20-08C -- how evenly the
simulator's irradiance is spread over the area nominated as the test
plane, while a measurement is being taken over it. Everything the clause
asks turns on two declarations: which area, and how densely it was
mapped.

## Domain quick reference

- The plane is nominated, not assumed. Every beam is uniform over some
  region and not over a larger one, so a uniformity figure carries no
  meaning until the area it was taken over is named and the mapped
  points are shown to sit inside it.
- The figure is extreme to extreme. Non-uniformity is the spread between
  the brightest and the dimmest reading normalised by their sum, because
  the cell sitting in the dimmest corner is the cell that limits a
  series string. A standard deviation over a hundred points can look
  healthy while two of them are eight per cent apart.
- Sampling is part of the result, not preparation for it. Four points
  cannot find a gradient that lives between them, so the point count and
  the plane coverage are validated before any figure is quoted.
- Coverage and point count fail independently. A dense grid bunched in
  the comfortable middle of the plane has plenty of points and has
  measured a smaller simulator than the one the article will see; a
  sparse grid spanning the corners has the opposite defect.
- The bands are a grouping, not the acceptance limit. A plane can be
  categorized into the second band and still be admissible, or land in
  the first band and still miss the tighter limit the measurement it
  feeds was quoted at, so band and verdict are reported separately.
- The extreme points are worth as much as the number. Two planes at the
  same per cent, one with its dim point at a corner and one with it
  under the centre, have different causes and different repairs.
- A pass with almost no margin is worth saying once. Lamp ageing widens
  a plane over a campaign, and a map that grazed the limit on the day it
  was taken will not clear it at the next remap.

## Workflow

1. Validate the uniformity policy first: the limit, the minimum point
   count, the minimum plane coverage, the grouping bands in widening
   order and the marginal band. A limit at or above a hundred per cent
   is refused rather than used.
2. Read the nominated plane. An absent plane, or one with a blank
   designation, closes the assessment on plane not declared -- there is
   no area for a figure to be uniform over.
3. Read every mapped point: non-blank identifier, no duplicate
   identifier, finite coordinates and a positive reading. An empty map
   is refused rather than reported as a flat plane.
4. Judge the sampling before the irradiance: point count against the
   floor, every point inside the plane, and the span of the mapped
   points against the coverage floor. Name each shortfall separately and
   stop there -- a figure from a map this thin would be quoted as though
   it were measured.
5. Take the spatial non-uniformity between the extreme readings, and
   report the mean, the brightest point and the dimmest point beside it.
6. Group the figure into the declared bands and, separately, hold it
   under the policy limit. A plane over the limit names both extreme
   points in the finding.
7. Close on one verdict: plane not declared, sampling insufficient,
   uniformity out of limit, or uniformity within limit -- with a
   marginal advisory when the pass had almost nothing left.

## Pitfalls

- Quoting a uniformity figure with no plane behind it. The number is
  only as large as the area it was taken over, and a figure without that
  area is unfalsifiable rather than good.
- Reporting a scatter about the mean. It is the friendlier statistic and
  it hides exactly the pair of points a series string will feel.
- Mapping the middle and calling it the plane. Coverage is the check
  that catches it, and a healthy point count does nothing to help.
- Reading the band as the verdict. The bands group simulators; the limit
  comes from the measurement being fed, and the two disagree often
  enough that both are reported.
- Comparing a derived per cent against its limit by bare arithmetic.
  Both sides are floats that can land a unit in the last place either
  side of the bound, so the comparison absorbs that while the limit
  itself is never relaxed.
- Dropping the extreme point identifiers once the per cent is computed.
  Nobody can find the cause of a wide plane from the per cent alone.

## Behavior contract (gate 3)

The policy validation, test plane validation, mapped point validation
and duplicate rejection, the inside-the-plane test, the coverage
fraction, the extreme-to-extreme non-uniformity figure, the mean and the
extreme point identifiers, the band grouping, the sampling findings, the
marginal advisory and the uniformity verdict are exercised by the gate 3
contract test:
scripts/test_e2008_simulator_irradiance_uniformity.py against
scripts/e2008_simulator_irradiance_uniformity_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2008_simulator_irradiance_uniformity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
