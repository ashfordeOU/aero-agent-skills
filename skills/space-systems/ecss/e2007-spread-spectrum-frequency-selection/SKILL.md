---
name: e2007-spread-spectrum-frequency-selection
description: "Derive the discrete operating frequencies at which a spread-spectrum transmitter is exercised under ECSS-E-ST-20-07C clause 5.2.7.3: validate the declared spreading mode, chip rate, hop set and tuning band, compute the bandwidth one emission event occupies, place low, mid and high tune points half a bandwidth inside the band edges, pick representative hop channels, and size the receiver dwell against the hop revisit period so no channel goes unseen. Use when an EMC test plan must state where a spreading unit is measured rather than naming a single carrier. Trigger: ecss, e-st-20-07c, spread-spectrum-frequency-selection, direct-sequence-chip-rate, frequency-hopping-revisit-period, occupied-bandwidth-tune-point, emc-receiver-dwell-sizing."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-spread-spectrum-frequency-selection, spread-spectrum-frequency-selection, direct-sequence-chip-rate, frequency-hopping-revisit-period, occupied-bandwidth-tune-point, emc-receiver-dwell-sizing, spread-spectrum-tune-point-separation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electromagnetic Compatibility — Spread-Spectrum Frequency Selection (space-systems/ecss/e2007-spread-spectrum-frequency-selection)

Use when the task is the clause 5.2.7.3 obligation of ECSS-E-ST-20-07C: the
unit-under-test transmits with a spreading technique, so its emission is not a
single carrier and the test plan cannot close by naming "the operating
frequency". The plan owes a defensible, enumerated set of frequencies the unit
is actually driven on during the emission and susceptibility runs.

## Domain quick reference

- A spreading declaration has three shapes and they do not select the same
  way. A direct-sequence emitter occupies a fixed main lobe around whatever
  carrier it is tuned to; a frequency-hopping emitter occupies one narrow
  channel at a time but visits many; a hybrid does both, spreading inside each
  hop channel. Reading a hopper as if it were a wideband emitter, or a
  direct-sequence unit as if it were narrowband, produces the wrong tune
  points in both directions.
- The bandwidth one emission event occupies is the unit that governs the
  selection. For direct-sequence and hybrid it is the null-to-null main lobe,
  conventionally twice the chip rate; for a pure hopper it is the declared
  instantaneous channel bandwidth, not the span the hop set covers.
- Tune points are placed half an occupied bandwidth inside the tunable band
  edges. Tuning a spread emitter to the exact band edge pushes half its
  spectrum outside the band the limits were written for, and the measurement
  then grades an emission the limit does not apply to.
- A tunable band narrower than one occupied bandwidth admits no valid tune
  point at all. That is a declaration defect, not a case to grade at the band
  centre and move on.
- Adjacent tune points must stay at least one occupied bandwidth apart, or the
  low and high readings are two views of one overlapping spectrum rather than
  two independent points, and the sweep proves less than it appears to.
- A declared hop set is reduced to representative channels — the lowest, the
  highest and the ones nearest the centre of the set — because the band edges
  and the band middle are where the front end, the filtering and the antenna
  match differ most.
- Receiver dwell is the hidden requirement in a hopping run. A hopper visits
  every declared channel once per revisit period, which is the hop dwell times
  the channel count. A receiver that dwells for less than one revisit period
  can sit on a graded channel the whole time the unit is elsewhere and record
  a floor instead of an emission.

## Workflow

1. Validate the declaration: a recognized spreading mode, a tunable band with
   a positive lower edge and a strictly higher upper edge, a positive chip
   rate for direct-sequence and hybrid, and for any hopper a channel bandwidth,
   a positive hop dwell and at least two distinct hop channels that all fall
   inside the tunable band.
2. Compute the occupied bandwidth of a single emission event from the mode:
   twice the chip rate where the unit spreads, the declared channel bandwidth
   where it only hops.
3. Place the tune points: the lowest half an occupied bandwidth above the
   lower band edge, the highest half an occupied bandwidth below the upper
   edge, the rest spaced evenly between them. Reject a band that cannot hold
   one emission rather than clipping the point inward.
4. Check adjacent tune-point separation against the occupied bandwidth,
   absorbing float representation error at equality instead of widening the
   requirement.
5. For a hopper, reduce the declared hop set to representative channels and
   record the reduction as a limitation so the reader knows which channels
   were not exercised.
6. Size the receiver dwell against the hop revisit period and report the
   shortfall of a dwell that cannot see every channel. An undeclared dwell is
   a limitation with the needed value attached, never a silent pass.
7. Aggregate: the selection is usable only when no separation finding and no
   dwell shortfall stands; a selection carrying only limitations is marginal
   and is grouped as such.

## Pitfalls

- Testing a spread-spectrum unit with the spreading disabled and recording the
  unspread carrier. That is a different emission with a different spectrum,
  and the clause asks where the unit is exercised as it flies.
- Taking the hop span as the occupied bandwidth of a hopper. The instantaneous
  occupancy is one channel; using the span pushes the tune points so far
  inside the band edges that the edges go untested.
- Tuning to the band edges exactly, so half the spread spectrum lands outside
  the band whose limits are being applied.
- Selecting hop channels at random or taking the first few in the declared
  order. The lowest, highest and central channels are the ones whose front-end
  and antenna behaviour differ; an arbitrary trio can miss all three.
- Leaving the receiver dwell unstated for a hopping run. A dwell shorter than
  one revisit period records the facility floor on a channel the unit was not
  occupying and reads as a clean pass.
- Widening the separation requirement so two crowded tune points pass. A pair
  landing exactly one occupied bandwidth apart is already compliant; the fix
  is to absorb representation error at the comparison, not to lower the
  requirement.

## Behavior contract (gate 3)

The declaration validation, occupied-bandwidth derivation, tune-point
placement, separation check, hop-channel reduction, revisit-period dwell
sizing and aggregation logic is exercised by the gate 3 contract test:
scripts/test_e2007_spread_spectrum_frequency_selection.py against
scripts/e2007_spread_spectrum_frequency_selection_logic.py (stdlib unittest,
offline, deterministic). Run:
python3 scripts/test_e2007_spread_spectrum_frequency_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
