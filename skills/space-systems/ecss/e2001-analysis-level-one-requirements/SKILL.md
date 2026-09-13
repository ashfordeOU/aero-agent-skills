---
name: e2001-analysis-level-one-requirements
description: "Use when determine whether the first, simpler multipaction analysis level of ECSS-E-ST-20-01C clause 5.3.2.2.1 may be used for a component and what that level then demands: check the chart-covered canonical gap-geometry, the field-homogeneity ratio across the critical gap, a charted surface-material, the absence of dielectric-loading, a single-dominant-mode region and a frequency-gap product inside the charted span; escalate to the second level on any failing criterion, otherwise derive the worst-case gap from the dimensional tolerance-stack, read the charted breakdown-voltage threshold there, and report the achieved margin plus any missing evidence item. Trigger: ecss, e-st-20-01c, multipaction-first-analysis-level, level-escalation, canonical-gap-geometry, field-homogeneity-ratio, tolerance-stack-gap, charted-threshold, secondary-emission-chart."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-analysis-level-one-requirements, multipaction, first-analysis-level, canonical-gap-geometry, field-homogeneity-ratio, tolerance-stack-gap, charted-threshold]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — First Analysis Level (space-systems/ecss/e2001-analysis-level-one-requirements)

Use when the task is the first-level branch of the multipaction design
analysis of ECSS-E-ST-20-01C clause 5.3.2.2.1 — establishing whether a
component may be assessed with the simpler charted route at all, and, if
it may, what that route has to produce as evidence.

## Domain quick reference

- The first level is the chart-based route: the critical region is
  reduced to a canonical geometry whose breakdown behaviour is already
  tabulated against the frequency-gap product, and the assessment is a
  lookup plus a margin statement rather than an electron-trajectory
  simulation. Its cheapness comes entirely from the assumptions behind
  the chart, so its applicability is a set of hard criteria, not a
  judgement call.
- Six criteria have to hold together. The gap geometry has to be one of
  the canonical charted forms. The field across the critical gap has to
  be close enough to homogeneous — a peak-to-mean ratio inside the
  declared limit — because the charted curves assume a near-uniform gap
  field. The surface has to be a material with standard
  secondary-emission chart data. There has to be no dielectric inside
  the gap, whose surface charging is outside the chart basis. The region
  has to carry a single dominant mode. And the worst-case frequency-gap
  product has to lie inside the charted span.
- Failure of any one criterion escalates the component to the second,
  simulation-based level. Escalation is per component and the failing
  criteria are named, because a design change that removes the failing
  criterion restores the cheaper route.
- The worst-case gap is not the drawing dimension. The tolerance stack
  gives a minimum and a maximum gap, and because the charted curve has
  an interior minimum, either extreme can be the worse one. Both are
  evaluated and the one with the lower charted threshold is carried
  forward; an exact tie resolves to the smaller gap so the result is
  reproducible.
- A first-level assessment is only complete with its evidence: the gap
  from the tolerance stack, the worst-case in-band frequency it was
  evaluated at, the charted threshold for the actual surface condition,
  and the achieved margin statement.

## Workflow

1. Build the gap extremes from the nominal dimension and the minus and
   plus tolerances; a minus tolerance that closes the gap is an input
   error and stops the assessment.
2. Evaluate the charted threshold at both gap extremes for the selected
   worst-case in-band frequency and keep the lower one as the worst
   case, together with its frequency-gap product and gap value.
3. Evaluate the six applicability criteria, using the worst-case
   frequency-gap product for the charted-span criterion. Normalise
   geometry and material names first; an empty or non-string value is an
   input error rather than a failing criterion.
4. Select the level: all criteria met keeps the component at the first
   level; any failure returns the second level plus the list of failing
   criteria, in criterion order.
5. Convert the worst-case charted threshold into a breakdown power
   through the local impedance and voltage-magnification factor, and
   compare the achieved margin in dB with the required value, absorbing
   floating-point representation error at the equality with a named
   tolerance rather than moving the required value.
6. Check the assessment record against the demanded evidence items and
   report the missing ones. The component is first-level compliant only
   when it stays at the first level, meets its margin and carries the
   full evidence set.

## Pitfalls

- Reading "the geometry looks like a parallel plate" as the canonical
  geometry criterion. The criterion is that a charted geometry applies;
  a shaped or three-dimensional region that merely resembles one is an
  escalation, not an approximation.
- Evaluating the nominal gap only. The tolerance stack moves the
  component along the charted curve, and on a curve with an interior
  minimum the larger gap can be the worse one, so both extremes are
  evaluated.
- Taking the first level because the margin came out comfortable. The
  margin is computed after applicability is settled; a comfortable
  number from an inapplicable chart is not evidence.
- Escalating silently. A component moved to the second level has to name
  which criteria failed, otherwise the design cannot be changed to
  recover the cheaper route and the escalation cannot be reviewed.
- Declaring the assessment complete with the margin alone. Without the
  tolerance-stack gap, the frequency it was evaluated at and the charted
  threshold for the actual surface condition, the margin cannot be
  reproduced.

## Behavior contract (gate 3)

The tolerance-stack gap extremes, charted-threshold interpolation,
worst-case gap selection, the six applicability criteria, the level
selection, the margin comparison and the evidence check are exercised by
the gate 3 contract test:
scripts/test_e2001_analysis_level_one_requirements.py against
scripts/e2001_analysis_level_one_requirements_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2001_analysis_level_one_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
