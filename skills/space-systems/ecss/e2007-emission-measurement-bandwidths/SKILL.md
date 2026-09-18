---
name: e2007-emission-measurement-bandwidths
description: "Determine the receiver bandwidth of ECSS-E-ST-20-07C clause 5.2.9.1. Use when an emission sweep over a test frequency range must be planned or audited: select the range a frequency falls in, read the bandwidth that range prescribes, hold the bandwidth a receiver was set to against it, derive the coarsest step as a fraction of that bandwidth and the shortest dwell from it, split a requested span at every range boundary, cost each segment in points and seconds, then walk an executed sweep for coarse steps, short dwells and under-sampling. Trigger: ecss, e-st-20-07c, emission-measurement-bandwidths, receiver-resolution-bandwidth, emission-range-bandwidth, emission-sweep-step-limit, emission-sweep-dwell, emission-sweep-point-count, prescribed-measurement-bandwidth."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-emission-measurement-bandwidths, receiver-resolution-bandwidth, emission-range-bandwidth, emission-sweep-step-limit, emission-sweep-dwell, prescribed-measurement-bandwidth]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Emission Measurement Bandwidths (space-systems/ecss/e2007-emission-measurement-bandwidths)

Use when the task is the bandwidth rule of ECSS-E-ST-20-07C clause
5.2.9.1 -- the receiver bandwidth that each emission test frequency
range is measured with, and the step, dwell and point count that
bandwidth then forces on the sweep.

## Domain quick reference

- The bandwidth is a property of the range, not of the emission and not
  of the operator. The measured frequency selects a range; the range
  hands back one bandwidth. Nothing about what the sweep happens to find
  at that frequency may change it.
- The bandwidth widens as the range rises. A low range needs a narrow
  bandwidth to separate the lines it is looking for and can afford the
  time that costs; a high range would take an unbearable number of
  points at the same bandwidth, so it is measured wider.
- The ranges are contiguous and a boundary frequency belongs to exactly
  one of them. The convention has to be fixed and stated, because the
  two ranges meeting at a boundary prescribe different bandwidths and a
  point sitting on the boundary would otherwise be arguable.
- The step follows from the bandwidth, not from the span. A sweep steps
  by at most a fraction of the bandwidth in force, so that an emission
  falling between two adjacent points is still inside the skirt of one
  of them. Expressing the step as a fraction of the span, or as a fixed
  number of points, leaves gaps exactly where the bandwidth is narrow.
- The dwell also follows from the bandwidth: a receiver needs a number
  of bandwidth time-constants to settle before its indication means
  anything, so a narrow bandwidth implies a long dwell. A floor sits
  under the derived value, because a wide bandwidth would otherwise
  imply a dwell shorter than any receiver honours.
- A span that crosses a range boundary is not one sweep. It is a
  sequence of segments, each with its own bandwidth, step, dwell and
  point count, and the cost of the whole span is the sum over the
  segments rather than anything computed from the end points.
- The point count is a ceiling, and a ceiling taken on a quotient of
  floats will add a whole spare point when the division lands a few
  units in the last place above an integer. That quotient is snapped to
  the nearby integer first, so the count is the same on every platform.

## Workflow

1. Validate the frequency: a non-numeric, non-finite, zero or negative
   value is an input error, and a frequency outside the measured range
   is refused rather than clamped to an edge.
2. Select the range that owns the frequency and read the bandwidth it
   prescribes. Carry the range with the answer so a reviewer can see
   which one was used.
3. Compare the bandwidth a receiver was actually set to with the
   prescribed one, reporting the ratio as well as the verdict, and
   treating a last-place difference as equality.
4. Derive the coarsest permitted step as a fraction of the prescribed
   bandwidth, and the shortest permitted dwell from the bandwidth
   subject to its floor.
5. For a planned span, break it at every range boundary it crosses,
   then cost each segment: interval count by a tolerance-aware ceiling,
   point count as intervals plus one, and sweep time as points times
   dwell. Sum over the segments.
6. For an executed sweep, evaluate every point against the bandwidth
   and dwell its range requires, then walk adjacent pairs: flag a point
   that does not advance in frequency, and check every genuine step
   against the allowance of the frequency it stepped from.
7. Compare the number of points actually taken with the number the
   bandwidths require across the same span, and report an under-sampled
   sweep as a finding of its own.
8. Aggregate: report the conforming fraction, the step count and the
   required plan, and accept the sweep only when no finding remains.

## Pitfalls

- Choosing the bandwidth from the span or the available test time
  instead of the range. The range fixes it; a sweep that cannot afford
  the resulting point count is a schedule problem, not a licence to
  widen the receiver.
- Deriving the step from the span, typically as a round number of
  points. The step must be a fraction of the bandwidth, so a span-based
  step leaves unmeasured gaps in exactly the narrow-bandwidth ranges
  where an emission is hardest to find.
- Sweeping a boundary-crossing span with one bandwidth, usually the
  wider of the two. The part of the span in the lower range is then
  measured with a bandwidth it never prescribed and its levels are not
  comparable with anything.
- Taking the dwell from the receiver default rather than the bandwidth.
  A narrow bandwidth needs a long dwell; a default dwell reads a level
  the receiver had not yet settled to.
- Letting a float quotient decide the point count. The ceiling of a
  quotient that lands a few units in the last place above an integer
  adds a spare point on one platform and not on another, so the planned
  sweep stops being reproducible.
- Arguing a boundary frequency into whichever range gives the wider
  bandwidth. The convention is fixed once; re-deciding it per point is
  how two sweeps of the same article stop agreeing.

## Behavior contract (gate 3)

The range selection, the prescribed-bandwidth lookup, the applied
bandwidth comparison, the step and dwell derivations, the boundary
splitting, the tolerance-aware point count and sweep-time costing, and
the whole-sweep acceptance are exercised by the gate 3 contract test:
scripts/test_e2007_emission_measurement_bandwidths.py against
scripts/e2007_emission_measurement_bandwidths_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2007_emission_measurement_bandwidths.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
