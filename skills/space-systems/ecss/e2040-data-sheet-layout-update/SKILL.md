---
name: e2040-data-sheet-layout-update
description: "Derive the revised device data sheet parameters from layout results under ECSS-E-ST-20-40C clause 5.6.6. Use when the task is replacing the pre-layout estimate of a timing, power or interface parameter with the value the layout run actually extracted, picking the worst corner for the direction the parameter is bounded in rather than the typical one, checking the published figure is no more favourable than that corner, grading the revised value against its specification limit, and reporting the remaining margin and the parameters that were never refreshed. Trigger: ecss, e-st-20-40c, device-data-sheet-layout-revision, post-layout-parameter-extraction, worst-pvt-corner-selection, data-sheet-optimistic-figure, device-parameter-margin-fraction, unrefreshed-data-sheet-parameter."
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
  tags: [ecss, e-st-20-electrical-scope, e2040-data-sheet-layout-update, device-data-sheet-layout-revision, post-layout-parameter-extraction, worst-pvt-corner-selection, device-parameter-margin-fraction, data-sheet-optimistic-figure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Device Engineering — Data Sheet Layout Update (space-systems/ecss/e2040-data-sheet-layout-update)

Use when the task is the data-sheet revision of ECSS-E-ST-20-40C clause
5.6.6 -- turning the numbers the layout phase extracted into the
numbers the device's users will design against, and deciding which of
the published figures are still pre-layout estimates.

## Domain quick reference

- Before layout, a data-sheet figure is an estimate from synthesis and
  a wire-load model. After layout the interconnect is real, so the
  parameter has an extracted value; publishing the estimate once the
  extraction exists hands the user a number the device does not meet.
- Every parameter is bounded in one direction, and that direction
  decides which corner is the worst one. A propagation delay, a setup
  time and a supply current are bounded above, so the worst corner is
  the largest extracted value. A maximum clock frequency and a noise
  margin are bounded below, so the worst corner is the smallest. Taking
  the typical corner because it is the one the tool reports first is
  the standard way an optimistic data sheet is produced.
- A published figure is allowed to be more conservative than the worst
  corner and never more favourable. Rounding a delay down or a
  frequency up by a single unit is not tidying; it is a figure the
  device can miss.
- The specification limit and the extracted value are different
  objects. The revision replaces the value; it does not move the limit.
  A revised value outside the limit is a design finding to be carried
  into the phase review, not a reason to restate the requirement.
- Margin is reported as a fraction of the limit, signed so that a
  negative figure always means a violation whichever way the parameter
  is bounded. A raw difference in nanoseconds and one in megahertz
  cannot be ranked against each other; the normalized fractions can.
- Corner coverage is itself a finding. A parameter extracted at one
  corner has no worst case, only a sample, and the data sheet entry
  derived from it inherits that.

## Workflow

1. Validate each parameter record: identifier, bound direction, unit,
   the specification limit, the published data-sheet value, and the
   extracted results keyed by corner. Reject an unknown direction, a
   non-finite number or an empty corner set.
2. Select the worst corner for the direction: the maximum extracted
   value for an upper-bounded parameter, the minimum for a
   lower-bounded one. Break a tie on the corner name so the selection
   is reproducible.
3. Compare the published value with the worst corner. Equality within
   a named relative tolerance is the intended state; a published value
   on the favourable side of the corner beyond that tolerance is an
   optimistic figure and a finding.
4. Flag a parameter whose published value still equals its pre-layout
   estimate while extracted results exist: it was never refreshed.
5. Grade the worst-corner value against the specification limit in the
   sense the direction implies, absorbing representation error with the
   same relative tolerance rather than by moving the limit.
6. Compute the signed margin fraction: for an upper bound, the limit
   less the value over the limit; for a lower bound, the value less the
   limit over the limit. Refuse a zero limit, which has no fraction.
7. Report per parameter the worst corner, the value, the margin and the
   findings, and aggregate into a revision that is complete only when
   no parameter carries one.

## Pitfalls

- Publishing the typical corner. It is the corner the device meets on
  an average day at room temperature, and the qualification campaign is
  not run there.
- Applying one worst-case rule to every parameter. Maximum-is-worst is
  correct for a delay and exactly inverted for a maximum frequency, and
  a single rule silently publishes the best corner for half the table.
- Rounding the published figure in the favourable direction. A rounded
  delay is a delay the device can exceed, and the rounding is invisible
  in the revision record.
- Widening the specification limit so the extracted value fits. The
  revision updates the data sheet, not the requirement; a value outside
  its limit belongs in the layout phase review.
- Extracting at a single corner and treating the result as worst case.
  One corner is a sample, and a parameter with no corner spread has no
  evidence behind the number that was published.

## Behavior contract (gate 3)

The parameter validation, worst-corner selection, optimistic-figure and
unrefreshed-figure detection, limit grading, signed margin fraction and
revision aggregation are exercised by the gate 3 contract test:
scripts/test_e2040_data_sheet_layout_update.py against
scripts/e2040_data_sheet_layout_update_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2040_data_sheet_layout_update.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
