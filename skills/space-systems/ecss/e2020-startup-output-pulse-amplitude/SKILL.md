---
name: e2020-startup-output-pulse-amplitude
description: "Evaluate the voltage pulse an output throws while the main bus powers up, against clause 5.4.2.4.1 of ECSS-E-ST-20-20C. Use when a recorded start up capture has to show the excursion stays inside its declared amplitude limit rather than merely settling eventually: average the tail for the settled output, refuse a tail still moving, open the excursion window at the first arrival at that value so the ramp is not read as an undershoot, take the largest departure each way, widen each by the probe and digitiser uncertainty, and report the worst side with its margin. Trigger: ecss, e-st-20-20c, bus-startup-output-pulse-amplitude, output-overshoot-peak-excursion, startup-settled-output-baseline, pulse-amplitude-probe-uncertainty, undershoot-below-settled-output, main-bus-power-up-transient."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-startup-output-pulse-amplitude, bus-startup-output-pulse-amplitude, output-overshoot-peak-excursion, startup-settled-output-baseline, pulse-amplitude-probe-uncertainty, undershoot-below-settled-output, main-bus-power-up-transient]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Start-Up Output Pulse Amplitude (space-systems/ecss/e2020-startup-output-pulse-amplitude)

Use when the task is the output pulse amplitude question of
ECSS-E-ST-20-20C clause 5.4.2.4.1 — bounding how far the output of a
unit departs from its own settled value while the main bus is powering
up, rather than showing only that it settles in the end.

## Domain quick reference

- The quantity bounded is a departure, not a voltage. Whatever is wired
  downstream sees the difference between the instantaneous output and
  the value the output holds, so the peak is read against the settled
  output and never against the nameplate figure. A unit regulating a
  little high carries a standing offset, and charging that offset to the
  pulse fails a design that is compliant.
- The settled value comes from the tail of the capture. A tail that is
  still moving is not a settled value — it is a record that stopped
  early — and averaging a slope invents a baseline the unit never held.
  The flatness of the tail is therefore a check in its own right, and
  its result decides whether the rest of the assessment can run at all.
- The start-up ramp is not an undershoot. Before the output first
  reaches the settled value, every sample sits below it, so subtracting
  the baseline across the whole record reports the ramp as an excursion
  the size of the rail. The window opens at the first arrival at the
  settled value; everything earlier is the unit starting.
- The two directions are bounded separately. An overshoot stresses the
  insulation and the input stage of the loads; an undershoot drops the
  rail below what those same loads need to stay up. A design may be
  granted more of one than the other, so an undershoot limit that is
  declared is used, and the overshoot limit is the fallback only when
  none is.
- A recorded peak is not the peak. Probe attenuation, digitiser gain and
  the quantisation of the capture all sit between the pulse and the
  number in the file, so the recorded amplitude is widened by the
  declared relative and absolute uncertainty before it is judged.
- A capture that already sits at the settled value at its first point
  may have been armed late. That is not a failure, but the pulse it was
  meant to catch could have happened before the record opened, and the
  result says so.

## Workflow

1. Validate the capture: at least three points, times that rise, and
   finite voltages. A record that repeats or reverses in time is an
   input error, not a resortable list.
2. Average the tail over the declared settling window for the settled
   output value, and take the peak-to-peak spread of that tail.
3. Compare the spread with the flatness limit. Above it, stop and report
   that the record ended before the output held, naming the spread and
   the limit rather than returning a baseline nobody can rely on.
4. Find the first point that comes within the arrival tolerance of the
   settled value. Advise when that tolerance is tighter than the settled
   ripple, and stop when no point qualifies, because the instant the
   ramp completed cannot then be placed.
5. Take the largest positive and the largest negative departure from the
   first arrival onwards, each with the instant it happened, breaking a
   tie on the earlier instant so the answer is reproducible.
6. Widen both amplitudes by the relative and absolute measurement
   uncertainty, then compare each with its own limit, reporting the
   margin in volts and the share of the limit consumed.
7. Name the worst side as the one eating the larger share of its own
   limit — not the larger voltage — and close with a verdict plus an
   advisory where a passing peak leaves almost no room.

## Pitfalls

- Reading the peak against the nominal output. The clause bounds the
  departure from what the unit actually holds, and a standing regulation
  offset quoted as pulse amplitude fails a compliant design.
- Averaging a tail that has not settled. The number returned looks like
  a baseline and is a point on a slope; every departure computed from it
  is wrong by however far the output still had to go.
- Subtracting the baseline across the whole record. The start-up ramp
  then appears as an undershoot the size of the rail, which is the
  largest excursion in the file and has nothing to do with the clause.
- Applying the overshoot limit to the undershoot without saying so. When
  the design declares only one value, using it both ways is defensible,
  but it is an assumption and belongs in the report.
- Comparing the raw recorded peak with the limit. A peak that exceeds
  the limit by less than the instrument chain can resolve then passes,
  which is the one case the uncertainty allowance exists to catch.
- Ranking the two directions on raw volts. With different limits the
  smaller excursion can be the one closer to failing, so the worst side
  is the one consuming the larger share of its own limit.
- Judging a peak against the limit by bare arithmetic. The amplitude is
  built from a mean, a subtraction and a product, so a case meant to sit
  exactly on the limit can land a few units in the last place outside
  it; the comparison absorbs that while the limit stays as declared.

## Behavior contract (gate 3)

The capture validation, settled-baseline extraction and flatness check,
arrival detection, windowed peak departures, uncertainty widening,
per-direction limit comparison, worst-direction selection and overall
verdict are exercised by the gate 3 contract test:
scripts/test_e2020_startup_output_pulse_amplitude.py against
scripts/e2020_startup_output_pulse_amplitude_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_startup_output_pulse_amplitude.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
