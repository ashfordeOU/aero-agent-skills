---
name: e2020-reverse-current-peak-tolerance
description: "Verify that a latching current limiter tolerates the reverse current peak its channel will actually see, per clause 5.4.1.2.1 of ECSS-E-ST-20-20C. Use when a reverse current capability is called for and a bus transient, a capacitive discharge or a reversed load has to be graded before the rating is frozen. Derive the tolerated peak from the nominal limitation current and the rated peak multiple, derate it for a pulse longer than the rated duration and for repeated events, compare the applied peak against it, and report the margin and the multiple the rating would have to carry. Trigger: ecss, e-st-20-20c, lcl-reverse-current-peak-tolerance, latching-limiter-reverse-current-capability, reverse-current-peak-withstand-rating, reverse-peak-pulse-duration-derating, repetitive-reverse-transient-derating."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-20c, e2020-reverse-current-peak-tolerance, reverse-current-peak-tolerance, lcl-reverse-current-peak-tolerance, latching-limiter-reverse-current-capability, reverse-current-peak-withstand-rating, reverse-peak-pulse-duration-derating, repetitive-reverse-transient-derating]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Supply — Reverse Current Peak Tolerance (space-systems/ecss/e2020-reverse-current-peak-tolerance)

Use when the task is clause 5.4.1.2.1 of ECSS-E-ST-20-20C: how much reverse
current peak a latching current limiter withstands, where a reverse current
capability is called for on the channel. This leaf turns a declared withstand
rating into the peak the channel actually tolerates for the event in front of
it, and grades the event against that number.

## Domain quick reference

- The rating is a peak, a duration and an event count together. A withstand
  quoted as a multiple of the limitation current means nothing until the pulse
  it was rated for is named, and a design that carries the multiple across to
  a longer pulse has changed the rating without saying so.
- Duration moves the tolerated peak. A reverse pulse longer than the rated one
  carries more charge into the same silicon, so the peak the channel survives
  falls with the square root of the duration ratio. A channel rated four times
  its limitation current for a short pulse tolerates half that at four times
  the duration.
- Repetition moves it again, and differently. Repeated reverse events erode
  the withstand a step at a time rather than with duration, and below a floor
  the single-event rating has stopped bounding the event count at all — at
  that point a repetitive figure has to be declared in its own right rather
  than inferred from the single-shot one.
- The capability is a precondition, not an assumption. The clause places a
  reverse peak rating on the channel only where a reverse current capability
  is called for. A channel with no such capability is outside the clause, but
  a reverse transient presented to it is then bounded by nothing here, and
  saying so is more use than a silent pass.
- The categories matter. The clause addresses the latching category;
  retriggerable, foldback and high power limiters handle reverse conditions
  through their own provisions, and grading one here is a scope error reported
  as out of scope rather than as a failure.
- The useful output is not a verdict alone. A review needs the multiple the
  rating would have to carry for the transient to sit inside it, because that
  is the number the next revision of the rating has to beat.

## Workflow

1. Normalise the limiter category and the reverse capability state, and decide
   whether the clause applies at all; report an out-of-scope channel rather
   than failing it, and name the transient it leaves unbounded.
2. Validate the rating: a positive limitation current, a positive rated peak
   multiple and the positive pulse duration that multiple is rated for.
3. Validate the transient: a positive peak, a positive duration and an integer
   event count of at least one.
4. Compute the duration derating, taking a pulse exactly on the rated duration
   as fully rated through a named tolerance rather than by moving the bound.
5. Compute the repetition derating and note when it has reached its floor.
6. Derate the rating to the tolerated peak for this event and take the margin
   in amperes against the applied peak.
7. Compute the peak multiple the rating would need to carry the transient.
8. Return the verdict with the rated peak, both derating factors, the derated
   tolerated peak, the margin, the required multiple and every finding.

## Pitfalls

- Grading against the catalogue peak. The headline multiple is a single-shot,
  rated-duration figure; comparing a long or repeated transient against it
  passes events the channel does not survive.
- Treating duration as pass or fail. A pulse beyond the rated duration is not
  a violation on its own — it derates the tolerated peak, and the finding is
  whether the applied peak still fits underneath.
- Inferring a repetitive rating from the single-event one. Past the derating
  floor the extrapolation has no engineering content left; the honest result
  is that a repetitive peak rating is missing.
- Defaulting the reverse capability to applicable. A channel that never
  declared one is outside the clause, and silently grading it as compliant
  hides a transient this clause does not bound.
- Failing a retriggerable, foldback or high power limiter here. Those are
  covered by their own provisions; an out-of-scope report is the accurate one.
- Reporting only pass or fail. Without the multiple the transient demands, a
  non-compliance gives the designer no target to size the next rating to.

## Behavior contract (gate 3)

The category and capability normalisation, rating and transient validation,
the square-root duration derating with its bound-equality tolerance, the
linear repetition derating and its floor, the derated tolerated peak, the
ampere margin, the required peak multiple and the verdict ladder — compliant,
non-compliant, out of scope — are exercised by the gate 3 contract test:
scripts/test_e2020_reverse_current_peak_tolerance.py against
scripts/e2020_reverse_current_peak_tolerance_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_reverse_current_peak_tolerance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
