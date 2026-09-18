---
name: e2007-inrush-current-test-purpose
description: "Verify that the inrush aim of ECSS-E-ST-20-07C clause 5.4.4.1 is actually demonstrated: confirm every required switch-on condition was captured on every power line, take the peak surge and the settled steady-state draw off each transient record, form the surge ratio, measure how long the draw stays above the specified envelope and the excess charge it carries there, categorize each event as within-bound, at-bound or an exceedance, reduce every line to its worst event and name the governing line, and refuse a record whose sample times do not advance. Use when grading a switch-on current surge against its specified bounds. Trigger: ecss, e-st-20-07c, inrush-current-test-purpose, switch-on-current-surge, inrush-peak-bound-margin, inrush-steady-state-surge-ratio, inrush-envelope-dwell-time, governing-inrush-line, switch-on-condition-coverage."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-inrush-current-test-purpose, switch-on-current-surge, inrush-peak-bound-margin, inrush-steady-state-surge-ratio, inrush-envelope-dwell-time, governing-inrush-line, switch-on-condition-coverage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Inrush-Current Test Purpose (space-systems/ecss/e2007-inrush-current-test-purpose)

Use when the task is the aim of ECSS-E-ST-20-07C clause 5.4.4.1 -- deciding
whether a captured set of switch-on events actually shows that the current
surge a unit draws as it is connected to its power bus stays inside the
bounds the interface specifies, so a neighbour on the same bus is not
dragged below its undervoltage threshold and the protection upstream is not
tripped.

## Domain quick reference

- The surge exists because the input filter of the unit is a discharged
  capacitor at the instant of switch-on. The bus sees a near short circuit
  for a few hundred microseconds, and the size and length of that event is
  what the interface bounds, not the steady draw that follows.
- Two quantities carry the demonstration and they answer different
  questions. The peak decides whether the upstream protection trips or a
  bus rail sags; the time spent above the envelope, and the excess charge
  carried there, decide whether the bus can supply the event out of its
  own decoupling without the sag reaching a neighbour.
- The surge ratio -- peak over settled draw -- is the number that travels
  between documents, because the settled draw is what the power budget
  holds and the ratio is what turns it into a bus-transient case. It is
  undefined when the record never settles, and that is a property of the
  capture window, not of the unit.
- Switch-on is not one condition. A cold start charges an empty filter; a
  warm restart charges a partly charged one and surges less; minimum bus
  voltage draws more current for the same power once the converter is in
  regulation; maximum bus voltage charges the filter faster. The
  demonstration is only complete when every specified condition was
  actually captured on every power line.
- Every power line is judged separately. A primary positive lead and its
  return do not see the same event once a secondary bus or a filter
  return path is in the picture, and the governing result is the worst
  line at its worst condition, never an average across lines.
- Grading is three-valued. A peak comfortably below the bound is a pass; a
  peak sitting on the bound is a pass carried as a limitation, because the
  next unit build or the next bus impedance will move it; a peak past the
  bound is an exceedance and the aim is not demonstrated.
- A transient record whose sample times do not advance is not a transient.
  It cannot be integrated, and reordering it silently invents an event
  that was never captured.

## Workflow

1. Validate each transient record: at least two samples, times strictly
   advancing, currents finite and non-negative.
2. Take the peak from the record, and the settled draw from the mean over
   the tail of the capture window, then form the surge ratio when the
   settled draw is positive.
3. Clip the record to the stretches sitting above the specified envelope,
   interpolating the crossings rather than snapping to the nearest sample,
   and reduce those stretches to a dwell time and an excess charge.
4. Categorize the peak against the specified bound as within-bound,
   at-bound or an exceedance, absorbing representation error at the bound
   with a named tolerance rather than by relaxing the bound.
5. Compare the dwell above the envelope with its allowance when one is
   specified; leave it ungraded, and say so, when none is.
6. Reduce every line to its worst event, then reduce the lines to the
   governing line and condition.
7. Check that every required switch-on condition was captured on every
   line, and aggregate findings and limitations. The aim stands only when
   no finding stands.

## Pitfalls

- Grading the peak alone. A modest peak held above the envelope for
  milliseconds can sag the bus further than a tall, short spike the bus
  decoupling swallows.
- Reading the settled draw off the last sample instead of the tail of the
  window, so one noisy sample sets the surge ratio.
- Measuring the dwell by counting samples above the envelope. The crossing
  falls between samples, and snapping to the nearest sample biases the
  dwell by up to a whole sample interval at each end.
- Capturing only the cold start. It is the largest peak but not always the
  longest event, and minimum bus voltage frequently governs the dwell.
- Testing the positive lead and assuming the return follows, then finding
  the return path carries the event on a later build.
- Treating a peak that lands exactly on the bound as a clean pass and
  recording nothing, so the next build has no warning that there was never
  any margin.
- Reordering a record whose times do not advance to make it integrable,
  which fabricates a transient rather than rejecting a bad capture.

## Behavior contract (gate 3)

The trace validation, peak and settled-draw extraction, surge-ratio
formation, envelope crossing interpolation, dwell and excess-charge
reduction, three-valued peak grading, per-line worst-case reduction and
condition-coverage aggregation is exercised by the gate 3 contract test:
scripts/test_e2007_inrush_current_test_purpose.py against
scripts/e2007_inrush_current_test_purpose_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_inrush_current_test_purpose.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
