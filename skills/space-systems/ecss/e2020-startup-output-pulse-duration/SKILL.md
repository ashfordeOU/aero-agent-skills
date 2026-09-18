---
name: e2020-startup-output-pulse-duration
description: "Determine how long an output stays away from its settled value while the main bus powers up, against clause 5.4.2.5.1 of ECSS-E-ST-20-20C. Use when a start up capture has to bound the excursion in time and not only in amplitude: centre a permitted band on the settled output, open the window where the ramp finishes, place both band crossings by interpolating across the crossing segment rather than counting whole samples, absorb re-entries shorter than the declared dead time into one event, flag an excursion the sample rate rather than the unit bounded, and compare the longest stay with its limit. Trigger: ecss, e-st-20-20c, bus-startup-output-pulse-duration, excursion-threshold-crossing-interpolation, pulse-duration-sample-rate-resolution, coalesced-pulse-re-entry-glitch, permitted-output-band-crossing, main-bus-power-up-transient-window."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-startup-output-pulse-duration, bus-startup-output-pulse-duration, excursion-threshold-crossing-interpolation, pulse-duration-sample-rate-resolution, coalesced-pulse-re-entry-glitch, permitted-output-band-crossing, main-bus-power-up-transient-window]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power — Start-Up Output Pulse Duration (space-systems/ecss/e2020-startup-output-pulse-duration)

Use when the task is the output pulse duration question of
ECSS-E-ST-20-20C clause 5.4.2.5.1 — bounding how long the output of a
unit is allowed to sit away from its settled value while the main bus
powers up, as a separate requirement from how far it went.

## Domain quick reference

- Amplitude and duration are independent requirements. A small departure
  held for milliseconds browns out every load behind it; a large one
  gone in a microsecond is absorbed by the decoupling of those same
  loads. A report that answers only the amplitude clause has answered
  half the question, and the two limits are not traded against each
  other.
- Duration runs between band crossings, not between samples. The output
  leaves the band somewhere inside the segment joining the last in-band
  point to the first out-of-band one, and returns somewhere inside the
  segment back. Counting whole samples rounds at both ends and
  understates a short pulse on a slow capture, so both ends are placed
  by linear interpolation across the crossing segment.
- Interpolation is honest only down to the sample spacing. An excursion
  shorter than the gap between the points bracketing it was never really
  recorded — the capture may have stepped over the peak — so it is
  reported with a note that the sample rate, not the unit, bounded it.
  The action is a faster capture, not acceptance of the number.
- A momentary return to the band is not the end of the pulse. An output
  ringing in and out serves one disturbance to the loads, so re-entries
  shorter than a dead time declared by the design are absorbed into the
  surrounding excursion. The dead time is a property of what is
  connected and is declared, never guessed.
- Open ends have to be named. A window that opens with the output
  already outside the band cannot say when that excursion began, and a
  record that ends outside the band cannot say when it ended. Either way
  the duration is a lower bound: a lower bound past the limit is a
  failure, one inside it is simply not yet an answer.
- The band centre is the settled output. It is read from the tail of the
  capture, or taken from a declared value when the record deliberately
  ends mid-excursion; in that second case a declared value far from the
  tail is worth saying out loud rather than trusting silently.
- A total-time budget is a separate question from the longest single
  event. Several short excursions can each pass and still hold the
  output away for longer than the design allowed in aggregate.

## Workflow

1. Validate the capture: at least three points, times that rise, finite
   voltages. A record that repeats or reverses in time is an input
   error, not a resortable list.
2. Fix the band centre. Average the tail over the settling window, and
   stop when that tail is still moving unless a settled output value is
   declared; when one is, use it and advise if it disagrees with the
   tail by more than the flatness limit.
3. Build the permitted band as the larger of a share of the settled
   output and an absolute floor, so a low rail is not given a band
   narrower than its own measurement noise. A zero-width band is refused.
4. Open the excursion window at the first point inside the band, which
   is where the start-up ramp finishes; stop when no point qualifies.
5. Walk the window and cut every unbroken stay outside the band,
   interpolating the entry and exit crossings on the edge actually
   crossed, and flagging an excursion left open at either end.
6. Coalesce excursions separated by no more than the declared re-entry
   dead time, keeping the worst departure and widening the direction to
   both sides when the merged parts disagree.
7. Compare the longest stay with the duration limit, and the sum of all
   stays with the total-time budget when one is declared, reporting each
   as its own finding.
8. Close with a verdict, an advisory for every resolution-limited or
   coalesced event, and one where a passing duration leaves almost no
   room.

## Pitfalls

- Counting samples to get a duration. Both ends then move by up to a
  sample period, which on a slow capture is most of a short pulse; the
  crossings belong inside the segments, placed by interpolation.
- Trusting an interpolated duration below the sample spacing. The number
  looks precise and the event was never resolved; it is a finding about
  the capture, not a result about the unit.
- Timing the start-up ramp. Before the output first enters the band
  every point is outside it, so the whole ramp reads as one enormous
  excursion that has nothing to do with this clause.
- Splitting a ringing event into several short pulses. Each can then sit
  inside the limit while the loads saw one long disturbance; that is
  what the declared re-entry dead time exists to prevent.
- Treating an excursion still running at the end of the record as
  finished. The measured value is a lower bound, and reporting it as the
  duration claims a bound the capture never demonstrated.
- Answering only the longest event when a total-time budget exists. The
  aggregate is a separate requirement and can fail on its own.
- Comparing a duration with its limit by bare arithmetic. The duration
  is built from two interpolated crossings, so a case meant to sit
  exactly on the limit can land a few units in the last place outside
  it; the comparison absorbs that while the limit stays as declared.

## Behavior contract (gate 3)

The capture validation, band construction, ramp-completion window,
interpolated crossing placement, open-ended excursion handling,
re-entry coalescing, sample-rate resolution check, longest and total
duration comparison and overall verdict are exercised by the gate 3
contract test: scripts/test_e2020_startup_output_pulse_duration.py
against scripts/e2020_startup_output_pulse_duration_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_startup_output_pulse_duration.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
