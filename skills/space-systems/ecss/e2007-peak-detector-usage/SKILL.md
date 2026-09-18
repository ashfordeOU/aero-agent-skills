---
name: e2007-peak-detector-usage
description: "Validate that every frequency-domain emission or susceptibility measurement uses peak detection under ECSS-E-ST-20-07C clause 5.2.8.2: reject averaging, root-mean-square, sample and quasi-peak detectors that report below the true peak, derive the dwell each measured point receives from the sweep time and point count, compare it against the resolution-bandwidth response time and the pulse repetition interval, check the frequency step against the resolution bandwidth so a narrow signal cannot slip between bins, and return the governing run. Use when a receiver setup or a test report must be shown to record peaks rather than averages. Trigger: ecss, e-st-20-07c, frequency-domain-peak-detector, resolution-bandwidth-response-time, receiver-dwell-per-bin, pulse-repetition-interval-dwell, spectrum-bin-step-check."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-peak-detector-usage, frequency-domain-peak-detector, resolution-bandwidth-response-time, receiver-dwell-per-bin, pulse-repetition-interval-dwell, spectrum-bin-step-check, emc-receiver-detector-choice]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Peak Detector Usage (space-systems/ecss/e2007-peak-detector-usage)

Use when the task is the clause 5.2.8.2 obligation of ECSS-E-ST-20-07C: any
emission or susceptibility quantity read against frequency is read with the
peak detector. The clause is short, and the defect it prevents is quiet — a
setup that names the right detector but sweeps too fast for it records a
number that is neither the peak nor an honest average.

## Domain quick reference

- The detector decides what a single measured point means. A peak detector
  holds the maximum the resolution-bandwidth filter reached inside that point;
  an average, root-mean-square or sample detector reports something lower for
  every signal that is not a steady sine, which is most of what a spacecraft
  unit emits. Quasi-peak is weighted for human perception of interference and
  also sits below the peak.
- Naming the detector is only half of it. The peak detector has to be given
  time to reach a peak. The resolution-bandwidth filter settles in roughly the
  reciprocal of its bandwidth, so the dwell on each measured point must reach
  at least that reciprocal before the reading means anything.
- Pulsed emissions raise the bar again. If the unit emits at a repetition rate,
  a point whose dwell is shorter than the interval between pulses can fall
  entirely between two of them and record the floor. The governing dwell is
  the larger of the filter response time and the pulse repetition interval.
- Dwell is derived, not declared. It is the sweep time divided by the number of
  measured points, so halving the sweep time or doubling the point count both
  erode it, and a setup can be made non-compliant by a change that looks like
  a resolution improvement.
- The frequency step between points is a separate trap. A step wider than the
  resolution bandwidth leaves frequencies no point ever looked at; keeping the
  step to half the bandwidth or less means a narrow signal always lands inside
  a measured point.
- The clause covers susceptibility as well as emissions. A susceptibility
  quantity measured against frequency — the level actually injected or
  radiated at each point — is read with the same detector, or the applied
  stress is understated and the unit is graded against a field it never saw.
- A run set is governed by its tightest run: the one whose dwell sits closest
  to the dwell it needed, not the one with the longest sweep.

## Workflow

1. Validate each frequency-domain run: an identifier, a recognized purpose
   (emission or susceptibility), a recognized detector, a positive span, an
   integer point count of at least two, a positive sweep time, a positive
   resolution bandwidth, and a positive pulse repetition rate where the
   emission is pulsed.
2. Report any detector other than peak, naming the run and the purpose, since
   averaging and weighted detectors understate by construction rather than by
   accident.
3. Derive the dwell per measured point from the sweep time and the point count,
   and the required dwell from the resolution-bandwidth response time, raised
   to the pulse repetition interval where one is declared.
4. Compare the two, absorbing float representation error at equality rather
   than relaxing the bound, and where the sweep is too fast report the minimum
   sweep time the point count implies so the setup can be corrected directly.
5. Derive the frequency step from the span and the point count and compare it
   against the allowed fraction of the resolution bandwidth.
6. Grade the run: compliant when the detector, the dwell and the step all
   hold; marginal when it holds but a pulse repetition rate was never declared,
   so the dwell was sized on the filter alone; otherwise non-compliant.
7. Aggregate: counts per category, the governing run by dwell ratio, the
   findings and the limitations. The set is sound only when no run carries a
   finding.

## Pitfalls

- Accepting a report because the detector field says peak. The detector name
  and the sweep speed are independent, and a fast sweep defeats a correctly
  named detector silently.
- Sizing the dwell on the resolution-bandwidth response time for a pulsed
  emitter. The pulse repetition interval is frequently the longer of the two
  and is the one that governs.
- Reading the sweep time as the dwell. The dwell is the sweep time shared
  across every measured point, so a twenty-second sweep over a thousand points
  gives twenty milliseconds each, not twenty seconds.
- Increasing the point count to improve resolution while holding the sweep
  time fixed. That shortens the dwell on every point and can turn a compliant
  setup non-compliant while appearing to refine it.
- Stepping in frequency by more than the resolution bandwidth. The gaps
  between points are then never measured, and a narrow emission sitting in one
  is reported as absent.
- Applying the clause to emissions only. Susceptibility levels read against
  frequency are governed too, and understating the applied level grades the
  unit against a stress it never received.
- Substituting an average detector to make a noisy trace look cleaner. The
  trace is cleaner because the peaks the clause asks for have been removed
  from it.

## Behavior contract (gate 3)

The detector normalisation, setup validation, dwell and bin-step derivation,
pulse-interval dominance, per-run grading and aggregation logic is exercised
by the gate 3 contract test:
scripts/test_e2007_peak_detector_usage.py against
scripts/e2007_peak_detector_usage_logic.py (stdlib unittest, offline,
deterministic). Run:
python3 scripts/test_e2007_peak_detector_usage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
