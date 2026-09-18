---
name: e2007-inrush-current-test-equipment
description: "Determine whether the instruments listed for an ECSS-E-ST-20-07C clause 5.4.4.2 inrush measurement can actually capture the surge: derive the chain bandwidth from the expected rise time, the sample rate from that bandwidth and the record depth from the capture window, size the current-probe peak rating from the surge and its low-corner ceiling from the allowed droop, bound the spike-generator edge that still proves the chain rather than the source, compare each declared item with its requirement, categorize every one as adequate, marginal or inadequate, and name the governing shortfall. Use when assembling or reviewing an inrush-current test bench. Trigger: ecss, e-st-20-07c, inrush-current-test-equipment, inrush-oscilloscope-bandwidth, inrush-current-probe-rating, inrush-probe-low-corner-droop, inrush-spike-generator-fitness, inrush-recording-depth, inrush-chain-rise-time."
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
  tags: [ecss, e-st-20-electrical-scope, e2007-inrush-current-test-equipment, inrush-oscilloscope-bandwidth, inrush-current-probe-rating, inrush-probe-low-corner-droop, inrush-spike-generator-fitness, inrush-recording-depth, inrush-chain-rise-time]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EMC — Inrush-Current Test Equipment (space-systems/ecss/e2007-inrush-current-test-equipment)

Use when the task is the equipment list of ECSS-E-ST-20-07C clause 5.4.4.2
-- deciding whether the oscilloscope, the current probe, the spike
generator and the recording arrangement declared for a switch-on surge
measurement can actually follow the surge that is expected, before the
bench is built rather than after a capture turns out to be unusable.

## Domain quick reference

- Every requirement on the bench comes from two numbers about the event:
  how fast the edge rises and how tall it gets. The rise time sets the
  bandwidth the whole chain must carry, through the rise-time bandwidth
  product of a well-behaved chain (about 0.35 over the rise time); the
  peak sets what the probe has to survive without saturating.
- Bandwidth and sample rate are separate requirements and a fast digitiser
  does not rescue a slow front end. The rate has to oversample the chain
  bandwidth several times over, or the peak lands between two samples and
  is recorded shorter and lower than it was.
- Record depth is the third leg and the one most often forgotten. The
  capture window has to reach past the settled draw so the surge ratio can
  be formed, and at the required rate that window is a point count. A
  scope with the bandwidth and the rate but not the memory forces the rate
  down at capture time, which quietly removes the bandwidth again.
- A current probe has a low-frequency corner as well as a high one, and
  for a pulse the low corner is what bites. A single-pole corner droops
  the recorded amplitude by roughly two pi times the corner times the
  pulse duration, so a long pulse through a probe with a high corner reads
  a peak that decays when the real current did not. Holding that droop to
  an allowed fraction bounds the corner from above.
- The spike generator is there to prove the chain end to end, so its edge
  has to be faster than the chain it is proving. A generator no faster
  than the chain measures the generator, and the chain passes or fails on
  the source's rise time instead of its own.
- Fitness is three-valued, not pass or fail. A capability comfortably past
  its requirement is adequate; one sitting on the requirement is usable
  but carried as a limitation, because instrument specifications are
  typical rather than guaranteed; one short of it is inadequate and the
  bench cannot take the measurement.
- When several items are short, the one that governs is the one short by
  the largest factor, not the first one listed. That is the item whose
  replacement changes the answer.

## Workflow

1. Validate the expected surge: positive rise time and peak, a pulse
   duration longer than the rise, and a capture window that at least
   reaches the pulse.
2. Derive the chain bandwidth from the rise time, the sample rate from the
   bandwidth and the oversampling factor, and the record depth from the
   window and the rate, rounding a partial sample up.
3. Derive the probe peak rating from the expected peak and its headroom,
   and the probe low-corner ceiling from the pulse duration and the
   allowed droop.
4. Derive the generator peak output from the expected peak and its rise
   time ceiling from the chain rise time.
5. Normalize the declared inventory, rejecting an unrecognized item and a
   duplicate declaration, and record every required item that is absent.
6. Compare each declared quantity with its requirement in the right sense
   -- a floor for bandwidth, rate, rating and depth, a ceiling for the
   probe low corner and the generator rise time -- and categorize it
   adequate, marginal or inadequate.
7. Reduce the inadequate checks to the governing shortfall and aggregate
   findings and limitations. The bench is fit only when no finding stands.

## Pitfalls

- Sizing the scope on the pulse duration rather than the rise time. The
  duration sets the window; the edge sets the bandwidth, and it is
  typically three orders of magnitude faster.
- Reading the sample rate off the data sheet headline, which is often the
  rate with every channel interleaved onto one, and finding it quartered
  once the probe and a voltage channel are both live.
- Checking bandwidth and rate but never the memory depth, then shortening
  the window at capture time so the settled draw is never reached and the
  surge ratio cannot be formed.
- Choosing the probe on its peak rating and its upper bandwidth alone. The
  low corner is what droops a millisecond pulse, and a probe built for
  radio-frequency work frequently has the worst corner of the set.
- Proving the chain with a generator no faster than the chain, so the
  recorded edge is the generator's and the chain's own rise time is never
  measured.
- Reporting the first inadequate item found as the problem, when another
  item is short by a far larger factor and is what actually has to change.
- Treating a capability that exactly equals its requirement as headroom.
  Instrument figures are typical, and the next unit off the shelf sits on
  the other side.

## Behavior contract (gate 3)

The surge validation, bandwidth, sample-rate and record-depth derivation,
probe rating and low-corner ceiling, generator rise-time bound, inventory
normalization, floor and ceiling categorization and governing-shortfall
reduction is exercised by the gate 3 contract test:
scripts/test_e2007_inrush_current_test_equipment.py against
scripts/e2007_inrush_current_test_equipment_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2007_inrush_current_test_equipment.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
