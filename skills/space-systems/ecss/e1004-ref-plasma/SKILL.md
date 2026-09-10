---
name: e1004-ref-plasma
description: "Use when determine the ECSS-E-ST-10-04C Annex H plasma-environment reference region for a mission orbit regime (ionosphere, plasmasphere, auroral, outer magnetosphere, solar wind, magnetosheath, magnetotail/L2), validate a candidate density or temperature value against that region's reference order-of-magnitude range, derive a log-space representative value for margin analysis, and identify the hot, tenuous plasma condition associated with spacecraft surface-charging risk. Trigger: ecss, e-st-10-04c, annex h, plasma environment, plasma density, plasma temperature, ionosphere, plasmasphere, auroral, magnetosphere, solar wind, magnetosheath, magnetotail, spacecraft charging."
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
  tags: [ecss, e-st-10-04c, plasma, plasma-environment, ionosphere, plasmasphere, magnetosphere, spacecraft-charging]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Plasma Region Reference Data (space-systems/ecss/e1004-ref-plasma)

Use when the task needs an order-of-magnitude plasma density and
temperature reference for a spacecraft's orbit regime under
ECSS-E-ST-10-04C Annex H (info) -- selecting the applicable reference
region, checking a candidate value against that region's range, and
screening for the hot, tenuous plasma condition that drives spacecraft
surface charging.

## Domain quick reference

- Annex H tabulates order-of-magnitude plasma density and temperature
  reference values per space-environment region, for use when no
  mission-specific plasma model is available. Seven regions are
  covered here: ionosphere, plasmasphere, auroral, outer
  magnetosphere, solar wind, magnetosheath, and the magnetotail/L2
  environment.
- The regions split into two rough regimes: cold and dense (ionosphere,
  plasmasphere -- high density, sub-eV to low-eV temperature) and hot
  and tenuous (auroral, outer magnetosphere, magnetotail/L2 -- low
  density, hundreds to thousands of eV). Solar wind and magnetosheath
  sit between the two, with moderate density and moderate temperature.
- The hot, tenuous regions are the recognized drivers of spacecraft
  surface charging: a low ambient density limits the return current
  that would otherwise neutralize a charging surface, while the high
  temperature raises the incident current from energetic particles.
  This leaf flags that condition as a screening signal, not a
  computed charging voltage.
- Each region's reference range is an order-of-magnitude bound, not a
  precise design value; a candidate reading outside the range is a
  finding that the reference table does not cover the case, not
  necessarily an error in the reading.

## Workflow

1. Identify the mission orbit regime (e.g. a LEO pass through the
   ionosphere, a GEO mission in the outer magnetosphere, an
   interplanetary cruise in the solar wind, an L2 mission in the
   magnetotail/L2 environment) and select the applicable Annex H
   region for that regime. Reject a regime with no defined mapping
   before it enters the assessment.
2. Pull that region's reference density and temperature ranges.
3. Validate any candidate density or temperature reading (from a
   mission-specific model, a measurement, or an assumption) against
   the region's reference range: below, within, or above range.
4. When a single representative value is needed for a margin
   analysis (rather than a measured or modeled reading), derive it by
   log-space interpolation between the range's low and high bound at
   the desired fraction (0.0 = low bound, 1.0 = high bound, 0.5 = the
   geometric mean).
5. For a hot, tenuous region (auroral, outer magnetosphere,
   magnetotail/L2), screen the density/temperature pair for the
   surface-charging condition: flagged only when the region carries
   the charging-risk designation, the density reading is not above
   the reference range, and the temperature reading is not below it.
6. Record the selected region, the range-validation results, and the
   charging screen result as the plasma-environment basis for the
   downstream charging and materials analyses.

## Pitfalls

- Selecting a region by altitude alone and ignoring the mission
  regime -- the auroral region and the ionosphere can overlap in
  altitude but have very different reference density and temperature,
  and the wrong choice under- or over-states the environment.
- Treating an "above_range" or "below_range" classification as
  automatically wrong -- Annex H gives an order-of-magnitude bound for
  when no mission-specific model exists; an out-of-range reading means
  the table does not cover this case and a dedicated model is needed,
  not that the reading itself is invalid.
- Using the geometric-mean (fraction 0.5) representative value as a
  worst case -- for a margin analysis the worst case is typically the
  low-density/high-temperature end of a charging-risk region, which
  is the high end of the temperature range and the low end of the
  density range, not the midpoint of either.
- Flagging surface charging for any hot, tenuous region regardless of
  the actual reading -- a region's charging-risk designation is a
  property of the region, not a guarantee that a specific reading is
  in the hot/tenuous part of its range; the screen still checks the
  reading against the range.

## Behavior contract (gate 3)

The region-reference, range-validation, log-interpolation,
source-selection, and surface-charging-screen logic is exercised by
the gate 3 contract test: scripts/test_e1004_ref_plasma.py against
scripts/e1004_ref_plasma_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_ref_plasma.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
