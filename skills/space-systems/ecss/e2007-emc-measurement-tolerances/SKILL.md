---
name: e2007-emc-measurement-tolerances
description: "Use when verify the deviations permitted while a compatibility measurement is performed, anchored at ECSS-E-ST-20-07C clause 5.2.1: hold the antenna separation to a fractional allowance with an absolute floor, the tuned frequency to its fractional allowance, and the applied or indicated level to its decibel allowance; select the frequency-band that fixes the resolution-bandwidth, the scan-step coarseness and the dwell duration; combine the measurement-uncertainty terms as a root-sum-square against their budget; then accept or reject the swept run point by point. Trigger: ecss, e-st-20-07c, emc-measurement-tolerances, measurement-distance-tolerance, frequency-tolerance-percent, amplitude-tolerance-db, scan-step-coarseness, dwell-duration, measurement-uncertainty-budget."
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
  tags: [ecss, e-st-20-electrical-scope, e-st-20-07c, e2007-emc-measurement-tolerances, measurement-distance-tolerance, frequency-tolerance-percent, amplitude-tolerance-db, scan-step-coarseness, measurement-uncertainty-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — EMC Measurement Tolerances (space-systems/ecss/e2007-emc-measurement-tolerances)

Use when the task is the measurement-tolerance rule of ECSS-E-ST-20-07C
clause 5.2.1 -- the deviations allowed on separation, frequency and
amplitude while an electromagnetic compatibility measurement is
performed, and the band-dependent scan-step and dwell that make a swept
run repeatable.

## Domain quick reference

- Three quantities carry a stated allowance at every measured point.
  The separation between the item under measurement and the antenna may
  deviate by a fraction of the nominal separation, floored by a small
  absolute band so that a short separation is still workable. The tuned
  frequency may deviate by a fraction of the intended frequency. The
  applied or indicated level may deviate from its target by a fixed
  number of decibels. Each allowance is two-sided.
- The deviation is judged on the quantity itself, not on its percentage
  alone: a separation allowance expressed as a fraction collapses to
  almost nothing at short range, which is why the absolute floor exists.
- The frequency-band the point sits in fixes three further parameters:
  the resolution-bandwidth of the receiver, the coarsest step permitted
  to the next point (as a fraction of the current frequency), and the
  shortest dwell at the point. Low bands need a long dwell and tolerate
  a relatively coarse fractional step; the high bands step more finely
  in fraction and dwell far more briefly.
- A swept run is a sequence, not a set. Each point must follow the
  previous one in frequency, and the gap between adjacent points is
  checked against the step allowance of the band the earlier point sits
  in. A run whose points repeat or run backwards is not sweepable and
  the step check for that pair is meaningless.
- Not every measurement carries all three quantities: a conducted
  measurement has no antenna separation, and an emission measurement
  has no applied-level target. A point must carry at least one
  toleranced quantity, and a quantity declared with only its nominal or
  only its measured half is malformed input, not a passing point.
- Measurement-uncertainty terms (antenna-factor calibration, cable-loss,
  receiver accuracy, site attenuation) are independent and combine as a
  root-sum-square, not a sum. The combined value is then held against
  the budget the campaign declared.
- A tolerance met exactly is met. A deviation computed as a difference
  or a product can land a few units in the last place outside an
  exactly-met allowance; absorb that in the comparison, never by
  widening the allowance.

## Workflow

1. Normalize the measured point: identifier, nominal and measured
   frequency, nominal and measured separation, target and measured
   level, dwell. Reject an unknown key, a blank identifier, a
   half-declared quantity, a non-numeric or non-finite value, and a
   point carrying no toleranced quantity at all.
2. Check the tuned frequency against the fractional frequency
   allowance, reporting both the absolute and the percentage deviation.
3. Check the separation against the greater of the fractional allowance
   and the absolute floor; report the deviation in metres and percent.
4. Check the level against its decibel allowance, in both directions;
   a tighter campaign-specific allowance may be imposed.
5. Select the band from the nominal frequency and check the dwell
   against the minimum that band requires.
6. Across the run, walk adjacent points: flag a point that does not
   advance in frequency, and check every genuine step against the step
   allowance of the band the earlier point sits in.
7. If an uncertainty budget is declared, combine the terms as a
   root-sum-square and compare with the allowance; the terms and the
   allowance are declared together or not at all.
8. Aggregate: report the conforming fraction of the points and accept
   the run only when no finding remains.

## Pitfalls

- Applying the fractional separation allowance at short range and
  accepting a millimetre-scale band that no fixture can hold -- the
  absolute floor is the point of that rule.
- Judging the step between adjacent points against the band of the
  later point: the allowance belongs to the frequency the sweep is
  stepping from, and the two differ exactly where the bands change.
- Treating a run whose points repeat a frequency as merely redundant --
  a non-advancing sweep leaves the step unverifiable and the repeated
  point indistinguishable in the record.
- Summing the uncertainty terms arithmetically, which inflates the
  combined uncertainty and can reject an acceptable run; independent
  terms combine as a root-sum-square.
- Reading a percentage deviation as the whole story when the campaign
  imposed a tighter absolute allowance, or vice versa -- report both
  and judge against the allowance actually in force.
- Rounding an exactly-met allowance away: absorb the representation
  error of the difference, never widen the allowance to make a point
  conform.

## Behavior contract (gate 3)

The separation, frequency and amplitude tolerance checks, the band
selection, the scan-step and dwell checks, the root-sum-square
uncertainty combination and the whole-run acceptance are exercised by
the gate 3 contract test:
scripts/test_e2007_emc_measurement_tolerances.py against
scripts/e2007_emc_measurement_tolerances_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_emc_measurement_tolerances.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
