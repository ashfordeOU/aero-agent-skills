---
name: rendezvous-phasing
description: "Use when you must plan an orbital rendezvous phasing maneuver: compute the drift rate needed to cover a phase angle in a transfer time, size the phasing delta-v around a circular orbit, and check the closing rate against the allowed value. Produces the drift rate, the delta-v estimate, and the closing rate verdict that gate the maneuver plan. Trigger: rendezvous, phasing orbit, closing rate, orbital maneuver, delta-v, chase."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: gnc-autonomy
pack: gnc-autonomy
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: space
  tags: [rendezvous, phasing-orbit, closing-rate, orbital-maneuver, delta-v, chase]
  version: 0.1.0
  author: AeroSkills
---

# Orbital Rendezvous Phasing (gnc-autonomy/space/rendezvous-phasing)

Use when the task is rendezvous phasing: drift rate, phasing
delta-v, and closing rate checks for an orbital chase maneuver.

## Domain quick reference

- Phasing: a chaser behind the target lowers its orbit to speed up
  (higher mean motion), drifts through the phase angle, then
  returns to the target altitude.
- Required drift rate is the phase angle divided by the transfer
  time.
- Delta-v scales with the mean motion and the semi-major axis
  change of the phasing orbit.
- The closing rate during the final approach must stay within the
  allowed value.

## Workflow

1. Collect the phase angle, transfer time, and orbit radius.
2. Compute the drift rate with drift_rate_required.
3. Size the phasing delta-v with delta_v_for_drift.
4. Check the closing rate with closing_rate_ok.
5. Gate the maneuver plan on the verdicts.

## Pitfalls

- Confusing lead and trail phase geometry.
- Sizing the phasing burn without checking the closing rate.
- Using transfer time of zero in the drift computation.

## Behavior contract (gate 3)

The drift, delta-v, and closing rate logic is exercised by the gate
3 contract test: scripts/test_rendezvous_phasing.py against
scripts/rendezvous_phasing_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_rendezvous_phasing.py

## Compliance

- Standards referenced, not reproduced: ECSS-E-ST-10-03C text is
  copyright ESA; the phasing here is common orbital mechanics,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
