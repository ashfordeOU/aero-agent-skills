---
name: e50-time-synchronization
description: "Determine whether two spacecraft sharing an inter-spacecraft network really hold their clocks together under ECSS-E-ST-50C clause 5.7.4.5. Recover the offset and the round trip from the four timestamps of one exchange, then budget what the exchange cannot cancel: static path asymmetry, the asymmetry relative motion opens while the responder holds the reply, timestamp resolution and jitter, plus the walk-apart at the relative drift rate before the next exchange. Use when sizing a synchronization interval, budgeting a coordination window, or reviewing a two-way transfer design on a formation, relay or rendezvous pair. Trigger: ecss, e-st-50c-clause-5-7-4-5, inter-spacecraft-time-synchronization, two-way-time-transfer-exchange, clock-offset-estimate-error, range-rate-reciprocity-error, synchronization-interval-sizing, relative-clock-drift-budget."
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
  tags: [ecss, e-st-50c-clause-5-7-4-5, e50-time-synchronization, inter-spacecraft-time-synchronization, two-way-time-transfer-exchange, clock-offset-estimate-error, range-rate-reciprocity-error, synchronization-interval-sizing, relative-clock-drift-budget]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Time Synchronization (space-systems/ecss/e50-time-synchronization)

Use when two spacecraft on an inter-spacecraft network have to keep their
clocks together, per ECSS-E-ST-50C clause 5.7.4.5 — how well one exchange
pins the offset, and how long that answer survives before the next one.

## Domain quick reference

- Synchronization between a pair is a different problem from
  distributing a reference down a tree. Here there is no master to walk
  away from: the two clocks are measured against each other, and the
  quantity under control is the offset between them.
- The four-timestamp exchange cancels whatever is reciprocal about the
  path. Request and reply share the same range and the same media, so
  the common part drops out of the offset and only the difference
  survives — which is why the whole budget is a list of the ways the
  two directions are not the same.
- Relative motion breaks reciprocity even on a perfect link. While the
  responder holds the reply the range changes, so the reply travels a
  different distance from the request; the error scales with range rate
  and with hold time, which makes the hold time a design parameter
  rather than an implementation detail.
- An offset of any size is the measurement, not an error. A responder
  clock reading minutes away from the initiator is exactly what the
  exchange exists to find, so ordering checks apply within each clock's
  own frame and never across the two.
- Between exchanges the pair walks apart at the relative drift rate,
  not at either clock's absolute rate. Two oscillators of the same
  build can hold each other far better than either holds an absolute
  scale, and budgeting with the absolute figure over-synchronizes.
- The interval is the knob, and it inverts cleanly. The window less the
  exchange error, divided by the relative drift, is the longest
  interval that still holds — and when the exchange alone spends the
  window, no interval does.

## Workflow

1. Take the four timestamps of one exchange and check ordering inside
   each clock's own frame only. Reject a reply that precedes its
   request, or a responder hold longer than the round trip.
2. Recover the round trip with the responder hold removed, the one-way
   delay, and the clock offset.
3. Budget the exchange error: half the static path asymmetry, half the
   motion asymmetry from range rate over the hold time, half the
   timestamp resolution, and the jitter carried separately.
4. Compute how far the pair walks apart over the synchronization
   interval at the relative drift rate.
5. Compare the sum against the coordination window with a relative
   tolerance, so a budget landing exactly on the window passes on every
   build host.
6. Invert for the remedy: the longest interval that still fits. Report
   zero where the exchange alone spends the window, and unconstrained
   where the pair has no declared relative drift.
7. Say which term dominates. Where motion beats static asymmetry, the
   cheaper fix is a shorter responder hold, not a better cable.

## Pitfalls

- Treating a large measured offset as a bad exchange. The offset is the
  output; validating timestamps across the two clocks rejects exactly
  the case the exchange was built to measure.
- Leaving the responder hold time out of the round trip. Including it
  inflates the one-way delay and biases the offset by half the hold,
  which is usually larger than every other term combined.
- Assuming reciprocity because the link is symmetric. Range rate breaks
  it without any hardware asymmetry at all, and a formation closing at
  kilometres per second breaks it by more than the cable ever could.
- Budgeting the interval with an absolute oscillator stability figure.
  The pair is graded on relative drift, and using the absolute number
  buys synchronization traffic the design did not need.
- Deciding the window with a bare inequality. Two arithmetically
  identical budgets can straddle the window on different machines, and
  the verdict then depends on the build host.
- Answering a missed window with a shorter interval without checking
  the exchange error first. When the exchange alone spends the window,
  synchronizing more often changes nothing and the honest answer says
  which term to attack instead.

## Behavior contract (gate 3)

Timestamp validation inside each clock frame, offset and round-trip
recovery, the half-weighted asymmetry and resolution terms, the range
rate and hold-time motion term, the relative-drift walk, the exact
window boundary, the longest-interval inverse with its zero and
unconstrained cases and the dominant-term finding are exercised by the
gate 3 contract test:
scripts/test_e50_time_synchronization.py against
scripts/e50_time_synchronization_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_time_synchronization.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
