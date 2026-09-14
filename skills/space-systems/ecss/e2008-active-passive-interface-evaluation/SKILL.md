---
name: e2008-active-passive-interface-evaluation
description: "Use when a single junction cell has to be evaluated for interface activity. Determine whether a single junction gallium arsenide on germanium solar cell carries an active interface layer under ECSS-E-ST-20-08C clause 7.5.18: read the open-circuit voltage sitting above the single junction reference, the share of spectral response beyond the gallium arsenide absorption edge, and the current left under a long-pass filter, hold each against its own pair of thresholds so a reading between them decides nothing, weigh the three independent lines together rather than letting one carry the call, and report an undecided interface as its own outcome instead of defaulting to passive. Trigger: ecss, e-st-20-08c-clause-7-5-18, gallium-arsenide-germanium-active-interface, germanium-sub-bandgap-response-share, single-junction-open-circuit-voltage-excess, long-pass-filtered-current-ratio."
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
  tags: [ecss, e-st-20-08-solar-cell-scope, e2008-active-passive-interface-evaluation, e-st-20-08c-clause-7-5-18, gallium-arsenide-germanium-active-interface, germanium-sub-bandgap-response-share, single-junction-open-circuit-voltage-excess, long-pass-filtered-current-ratio, bare-cell-interface-layer-evaluation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Solar Cells -- Active/Passive Interface Evaluation (space-systems/ecss/e2008-active-passive-interface-evaluation)

Use when the task is clause 7.5.18 of ECSS-E-ST-20-08C: deciding whether
the germanium substrate under a single junction gallium arsenide cell is
carrying a junction of its own. A passive interface is a mechanical
carrier. An active one sits in series with the cell for the whole
mission, and nobody budgeted for it.

## Domain quick reference

- The two cases are not cosmetically different. An active interface adds
  its own voltage, its own temperature coefficient and its own spectral
  dependence, so an array sized on single junction behaviour drifts away
  from its prediction over the year and over the seasons.
- No single measurement settles it. Each of the three available lines
  has a benign explanation that produces the same reading, which is why
  they are read independently and then weighed together.
- Voltage is the quickest line and the easiest to misread. An
  open-circuit voltage above the single junction reference is what an
  extra junction in series looks like, and it is also what a cold cell
  or a generous reference value looks like.
- The spectral line is the most direct. Only germanium converts light
  past the gallium arsenide absorption edge, so response out in that
  band came from somewhere the single junction cell should not have.
- The band is measured clear of the absorption edge on purpose. Starting
  it at the edge sweeps up the steep tail of the gallium arsenide
  response itself, and a passive cell then reports a share that looks
  like evidence.
- The filtered line is the cleanest confirmation and the easiest to get
  wrong in hardware. A long-pass filter that leaks anything the gallium
  arsenide junction absorbs produces current on a passive cell, so a
  filtered current above the unfiltered one is a bench fault.
- A sweep that stops short of the germanium cutoff has not measured the
  band it was pointed at. The share it returns is real over the part it
  covered and silent about the rest, so that line decides nothing.
- Each line carries two thresholds, not one. Between them the
  measurement has not decided, and that gap is the declared uncertainty
  rather than a place to round from.
- An undecided interface is an outcome. Defaulting it to passive is the
  reading that lets an unplanned junction reach a flight array.
- The edge wavelengths, the band start, the six thresholds and the
  agreement rule are declared project policy rather than physical
  constants, so they are stated with the result.

## Workflow

1. Take the batch: one record per cell, with its open-circuit voltage
   and the single junction reference, the spectral response sweep, and
   the short-circuit current with and without the long-pass filter.
2. Read the sweep first: order it, refuse one that never reached past
   the absorption edge or never measured below it, and note whether it
   reached the germanium cutoff.
3. Reduce the three lines: the voltage above the reference, the share of
   integrated response inside the sub-bandgap band, and the share of
   current left under the filter.
4. Read each line against its own upper and lower threshold, so that a
   value between them is recorded as undecided rather than pushed.
5. Force the spectral line to undecided where the sweep stopped short of
   the germanium cutoff, because the band it would speak for was only
   partly measured.
6. Weigh the lines: contradiction between them, or too few that decided,
   both give an indeterminate interface rather than a majority verdict.
7. Roll the batch up: name the undecided cells on their own, and flag a
   batch carrying both outcomes, because the substrates did not all come
   from one process.

## Pitfalls

- Calling an interface active on the voltage alone. A cold measurement
  or an optimistic single junction reference produces the same excess,
  and the other two lines are what tell them apart.
- Integrating the sub-bandgap share from the absorption edge itself. The
  steep edge of the gallium arsenide response falls inside the band, and
  a passive cell then reports a share that reads as evidence.
- Accepting a sweep that stopped at the near infrared. The germanium
  response runs far beyond it, so the share is silent about most of the
  band and must not be allowed to decide.
- Trusting a filtered current higher than the unfiltered one. The filter
  cannot add light, so the record describes the bench rather than the
  cell and the line has to be repeated.
- Taking a majority of two against one as a decision. Lines that
  contradict each other mean one of the three measurements is wrong, and
  which one is wrong is the question to answer next.
- Recording an undecided interface as passive. It is the one reading
  that lets an unplanned junction through, and it is indistinguishable
  from a real passive result once it is in the file.
- Comparing a response share, a voltage excess or a current ratio
  against its threshold by bare arithmetic. Each is a quotient or
  difference of measured quantities, so a cell cut exactly to a
  threshold can evaluate a unit in the last place across it and be
  grouped one way on one platform and the other way on another.

## Behavior contract (gate 3)

The sweep read with its ordering, coverage refusals and germanium-cutoff
truncation, the trapezoidal band integration, the sub-bandgap share, the
voltage excess, the filtered current ratio with its added-light refusal,
the two-threshold reading of each line, the forced-undecided spectral
line, the contradiction and too-few-lines routes to an indeterminate
interface, and the batch uniformity and undecided roll-up are exercised
by the gate 3 contract test:
scripts/test_e2008_active_passive_interface_evaluation.py against
scripts/e2008_active_passive_interface_evaluation_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2008_active_passive_interface_evaluation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
