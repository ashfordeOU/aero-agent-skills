---
name: e2007-inrush-current-data-presentation
description: "Evaluate the current-against-time graph a switch-on surge result must be presented as, under ECSS-E-ST-20-07C clause 5.4.4.5. Use when inrush-current results are drawn up or reviewed: confirm the axes really carry current against time in units belonging to those quantities, require the plotted span to open before the switching instant and close after the draw has settled, detect a peak running past full scale or sitting too low in it to read, count the samples landing on the rising edge, compare the peak with the settled draw, list the stated conditions the trace is missing, and return the presentation verdict. Trigger: ecss, e-st-20-07c, inrush-current-data-presentation, current-against-time-graph, switch-on-surge-trace, inrush-peak-full-scale-clipping, inrush-rising-edge-sampling, inrush-stated-test-conditions."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-inrush-current-data-presentation, current-against-time-graph, switch-on-surge-trace, inrush-peak-full-scale-clipping, inrush-rising-edge-sampling, inrush-stated-test-conditions]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Inrush-Current Data Presentation (space-systems/ecss/e2007-inrush-current-data-presentation)

Use when the task is the data-presentation requirement of
ECSS-E-ST-20-07C clause 5.4.4.5 -- showing that a switch-on surge result
reaches the reader as current drawn against time, spanning the whole
transient, with the conditions the trace was taken under stated on it.

## Domain quick reference

- The deliverable is a graph, not a peak. A single worst-case ampere
  figure cannot show the shape the clause asks for: how fast the draw
  rose, how long it stayed up and what it settled back to. Those are
  read off the trace or not at all.
- The span has to start before the switching instant. Without the
  quiescent draw ahead of the surge there is no baseline to measure the
  rise against, and a plot that opens on the transient already in
  progress hides where it began.
- The span also has to close after settling. A trace cut at the peak
  leaves the recovery unproven, which is the half of the transient that
  shows the unit reached its steady draw rather than latching at a
  higher one.
- Vertical scale is a reporting decision with two failure directions. A
  peak past full scale is reported as the scale rather than the surge, a
  hard finding. A peak occupying a small share of the scale is legible
  but coarse, which limits the resolution of the reported value rather
  than invalidating it.
- The rising edge is only as real as its sampling. A handful of samples
  on the edge is a drawing of the digitizer, not of the unit, so the
  sample interval is compared with the edge it is meant to resolve.
- Stated conditions make the trace reproducible. Bus voltage, source
  impedance, ambient temperature, load configuration and which switching
  event this was are what let a later reader repeat the run; a graph
  without them reports a number nobody can obtain again.

## Workflow

1. Validate the graph record: recognized axis quantities and units, a
   real plotted span, positive full scale, peak and sample interval, a
   settled draw not exceeding the peak, and condition labels normalized
   to comparison tokens.
2. Check the axes carry current against time and that each unit belongs
   to the quantity on its axis.
3. Compare the plotted span with the switching instant and the settling
   time, reporting either end that is not shown.
4. Test the peak against full scale for clipping, and compute the share
   of the scale the peak actually uses.
5. Count the samples falling on the rising edge and compare with the
   number needed to draw it.
6. Compute the peak-to-settled ratio the graph reports.
7. List the required conditions the graph does not state.
8. Aggregate: wrong axes, an uncovered span end, a clipped peak, an
   unresolved edge or missing conditions are findings; a coarse vertical
   scale and a surge barely above the settled draw are limitations.

## Pitfalls

- Reporting the inrush as one number in a table. The clause asks for the
  transient behaviour, and a table row cannot carry a shape.
- Starting the plot at the switching instant. The baseline immediately
  before it is what the rise is measured from.
- Zooming the vertical scale onto the peak until it clips. The trace
  then reports the axis limit, and nothing on the page says so.
- Treating a low peak on a wide scale as the same defect as clipping. It
  costs resolution, not validity, and belongs in the report as a
  limitation.
- Leaving the conditions to the surrounding text. The graph travels on
  its own into review packs, and the conditions have to travel with it.

## Behavior contract (gate 3)

The graph validation, condition normalization, axis quantity and unit
checks, span-shortfall detection, clipping and scale-utilisation tests,
edge-sample counting, peak-to-settled ratio, missing-condition listing
and the aggregate verdict are exercised by the gate 3 contract test:
scripts/test_e2007_inrush_current_data_presentation.py against
scripts/e2007_inrush_current_data_presentation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_inrush_current_data_presentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
