---
name: e50-doppler-shift-and-doppler-rate
description: "Compute the Doppler shift and Doppler rate a space link sees from the radial motion between spacecraft and ground station, under ECSS-E-ST-50C clause 5.6.11.1, and compare both against what the receiver can acquire and track. Derive the offset from carrier frequency and radial velocity, the rate from radial acceleration, the search width once oscillator error is added, the sweep dwell it costs, and the radial velocity and acceleration the equipment tolerates. Report which limit binds. Use when assessing carrier acquisition for a fast-moving or low-orbit spacecraft link. Trigger: ecss, e-st-50-communications, link-doppler-shift, link-doppler-rate, carrier-acquisition-sweep-range, receiver-frequency-uncertainty, doppler-tracking-loop-limit."
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
  tags: [ecss, e-st-50-communications, e50-doppler-shift-and-doppler-rate, link-doppler-shift, link-doppler-rate, carrier-acquisition-sweep-range, receiver-frequency-uncertainty, doppler-tracking-loop-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Doppler Shift and Doppler Rate (space-systems/ecss/e50-doppler-shift-and-doppler-rate)

Use when a space communication link has to work across the Doppler its own
geometry produces, per ECSS-E-ST-50C clause 5.6.11.1 — how much offset and how
much sweep, against what the receiver can actually do.

## Domain quick reference

- Two quantities, two different receiver capabilities. The shift is
  carrier times radial velocity over light speed and is judged against
  the acquisition range; the rate is carrier times radial acceleration
  over light speed and is judged against what the tracking loop can
  follow. They are separate numbers and a link can pass one and fail
  the other.
- The sign carries information. Closing motion raises the received
  carrier, opening lowers it, and a sweep plan that only knows the
  magnitude has to search twice the span it needed to.
- What the receiver must search is not the Doppler. Oscillator error
  at both ends adds to it, and on a modest reference at a high carrier
  the reference term is the larger of the two — in which case a better
  oscillator buys more than a wider sweep.
- The search spans both sides of nominal, so the sweep width is twice
  the worst-case uncertainty, and dividing it by the sweep rate gives
  the dwell an acquisition attempt costs inside the pass.
- Read the model backwards for the useful answer. The radial velocity
  that just fills the acquisition range, and the radial acceleration
  the loop can just follow, are the two limits an orbit designer and a
  receiver supplier can both act on.
- Keep the arithmetic to multiplication and division. Exponentials and
  logarithms are not correctly rounded, and a verdict at an exact bound
  would then depend on the machine the check ran on.

## Workflow

1. State the carrier frequency, the signed radial velocity and the
   signed radial acceleration at the worst point of the geometry — not
   the mean over the pass.
2. Compute the Doppler shift and the Doppler rate, keeping the signs.
3. Add the oscillator contribution from the reference stability in
   parts per million, and report it separately from the Doppler so the
   dominant term is visible.
4. Report the full sweep width as twice the worst-case uncertainty, and
   the dwell time one sweep costs at the receiver's sweep rate.
5. Compare the uncertainty with the acquisition range and the rate
   magnitude with the tracking capability, both with a relative
   tolerance so a geometry landing exactly on a limit passes.
6. Name the binding limit even when both pass. It says which way the
   design has least room, and which supplier number to press on.
7. Where either fails, report the inverse: the radial velocity and the
   radial acceleration the equipment tolerates as stated.

## Pitfalls

- Sizing the sweep on Doppler alone. Reference error adds to it, and
  at a high carrier a few parts per million is thousands of hertz.
- Dropping the sign of the range rate. The offset lands either side of
  nominal, and a one-sided sweep misses half the geometries.
- Judging the rate against the acquisition range. Acquiring a large
  offset and following a fast-moving one are different capabilities
  with different numbers.
- Taking the mean Doppler over a pass. Acquisition happens at the
  worst point, usually near closest approach, where the rate peaks.
- Using exponentials to convert the ratios. They round differently
  across platforms, and a geometry sitting exactly on the acquisition
  bound then passes on one build host and fails on another.

## Behavior contract (gate 3)

Carrier, velocity, acceleration and stability validation, the signed
shift and rate, the oscillator contribution, the two-sided sweep width
and its dwell, the three-way verdict with a tolerance at each receiver
bound, the binding-limit report and the two inverse limits checked
against the same model are exercised by the gate 3 contract test:
scripts/test_e50_doppler_shift_and_doppler_rate.py against
scripts/e50_doppler_shift_and_doppler_rate_logic.py
(stdlib unittest, offline).
Run:
python3 scripts/test_e50_doppler_shift_and_doppler_rate.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
