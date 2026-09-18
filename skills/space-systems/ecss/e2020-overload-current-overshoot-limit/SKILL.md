---
name: e2020-overload-current-overshoot-limit
description: "Compute the current overshoot that appears at the input and the output of a power supply interface when an overload arrives, and bound it. Use when clause 5.4.1.1.1 of ECSS-E-ST-20-20C is assessed: take the limitation value, the overload onset and the sampled waveform of each port, read each peak as a factor on the limitation value, integrate the time the current stays above it with interpolated crossings rather than whole sample intervals, compare both ports against the permitted factor and the settling window, and observe when the input peak exceeds the output one. Trigger: ecss, e-st-20-20c-clause-5-4-1-1-1, overload-current-overshoot, input-port-current-peak, output-port-current-peak, limitation-value-overshoot-factor, overshoot-settling-window, interpolated-limit-crossing, overload-onset-instant."
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
  tags: [ecss, e-st-20-20-power-supply-interface-scope, e2020-overload-current-overshoot-limit, overload-current-overshoot, input-port-current-peak, output-port-current-peak, limitation-value-overshoot-factor, overshoot-settling-window, interpolated-limit-crossing, overload-onset-instant]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply Interfaces -- Overload Current Overshoot Limit (space-systems/ecss/e2020-overload-current-overshoot-limit)

Use when the task is clause 5.4.1.1.1 of ECSS-E-ST-20-20C -- an overload
has just appeared on a protected branch, the limiter has not yet
finished taking control, and the question is how far the current is
allowed to run past the limitation value at each port of the interface
while that happens.

## Domain quick reference

- The limitation value is a settled quantity, not an instantaneous one.
  On the arrival of an overload the branch current runs past it while
  the control loop is still closing, and what the ports see during that
  interval is the subject of the clause.
- The two ports do not see the same excursion, so they are measured
  separately. At the output port the capacitance downstream of the pass
  element dumps straight into the fault, so the peak there is set by the
  fault path and the loop has almost no say in it. At the input port the
  same event arrives through the input filter, which softens the peak
  and stores energy that lengthens what is left.
- Each port is bounded twice, because a peak alone does not describe the
  event. A high peak lasting a microsecond is a rate-of-change problem
  for everything sharing the bus; a modest peak held for a millisecond
  is an energy problem for the pass element and a trip risk for the
  upstream protection, which may read it as a real overload and act. So
  the bound is a factor on the limitation value together with a window
  the current has to have settled back inside.
- The time above the limitation value is an integral, not a count of
  sample intervals. The crossings fall between samples, so they are
  interpolated; rounding each crossing to the nearest sample can double
  a short excursion or erase it.
- A current sitting exactly at the limitation value is not an overshoot.
  The excursion is what lies strictly above it, and the settling instant
  is the last return to it, which for a record with two humps is the
  later crossing and not the first.
- The comparison between the ports is the observation an analyst reads
  next. An input peak above the output peak says the excursion is being
  fed from the input filter rather than from the downstream
  capacitance, which points the investigation at a different component.

## Workflow

1. Validate each port waveform as at least two samples with strictly
   increasing instants and no negative current, and the overload onset
   as an instant inside the sampled span.
2. Validate the permitted factor; a bound below unity is not an
   overshoot bound and is refused rather than clamped.
3. Take the peak of each port, earliest instant winning an equal peak so
   the result is reproducible, and express it as a ratio and as a
   fractional excess above the limitation value.
4. Integrate the time each port spends strictly above the limitation
   value, interpolating the crossing instant inside every sample
   interval that spans the value.
5. Take the settling time as the last crossing back to the limitation
   value measured from the overload onset; a record still above the
   value at its end has no settling time and is reported as such rather
   than given the record length.
6. Compare each peak with its own bound and each settling time with the
   window, absorbing representation error so a value placed exactly on
   the bound reads as inside it.
7. Close with the verdict, every port finding, and the cross-port
   observation when the input peak is the larger one.

## Pitfalls

- Bounding the peak and stopping there. A peak inside the factor that
  takes ten times the allowed window to settle is still a failed
  interface, and it is the one the upstream protection trips on.
- Measuring only the output port because the fault is downstream. The
  input port carries what the filter passes on, and that is what the
  rest of the bus and the upstream limiter actually see.
- Counting whole sample intervals as time above the limit. A crossing
  falls between samples, so an excursion two samples wide can be
  reported at twice its length or, with a coarser record, at zero.
- Taking the first return below the limit as the settling instant. A
  ringing excursion crosses several times, and only the last crossing
  ends the event.
- Reading a record that never returns below the limit as a long
  settling time. Nothing in that record says when it settles; the
  measurement is missing, not large.
- Treating a current exactly at the limitation value as an overshoot,
  or judging a peak sitting exactly on its bound by bare arithmetic.
  Peaks, ratios and interpolated crossings are all products of floats,
  so each comparison absorbs representation error while the bound
  itself stays as declared.

## Behavior contract (gate 3)

The waveform validation, factor validation, overshoot bound, peak
selection, ratio and fractional overshoot, interpolated time above the
limitation value, last crossing, settling time, per-port assessment and
the cross-port observation are exercised by the gate 3 contract test:
scripts/test_e2020_overload_current_overshoot_limit.py against
scripts/e2020_overload_current_overshoot_limit_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_overload_current_overshoot_limit.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
