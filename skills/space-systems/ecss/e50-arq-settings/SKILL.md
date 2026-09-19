---
name: e50-arq-settings
description: "Configure the automatic repeat request parameters of a space data transfer protocol under ECSS-E-ST-50C clause 5.6.13.5, whose single normative item asks that the retransmission settings be adjustable in flight and consistent with the link they run over. Derive the retransmission timeout floor from the round trip, the acknowledgement delay and the jitter, the transmit window the bandwidth-delay product needs, the worst case delivery time a retry limit allows, and the residual loss it leaves. Report every setting that is fixed in the build rather than commandable. Use when tuning retransmission timers or reviewing an ARQ configuration. Trigger: ecss, e-st-50-communications, arq-retransmission-timeout, arq-transmit-window-sizing, arq-retry-limit-budget, ground-settable-arq-parameters, automatic-repeat-request-configuration."
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
  tags: [ecss, e-st-50-communications, e50-arq-settings, arq-retransmission-timeout, arq-transmit-window-sizing, arq-retry-limit-budget, ground-settable-arq-parameters, automatic-repeat-request-configuration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — ARQ Settings (space-systems/ecss/e50-arq-settings)

Use when the retransmission behaviour of a space data transfer protocol has
to be set up, per ECSS-E-ST-50C clause 5.6.13.5 — which parameters the design
exposes, whether the values chosen fit the link, and whether the operator can
change them once the spacecraft is flying.

## Domain quick reference

- Adjustability is half the obligation and the half designs drop. A
  retransmission timer compiled into the flight software is a timer nobody
  can fix when the link turns out slower than the analysis said, and the
  mission then flies the wrong value for its whole life.
- The timeout floor is the round trip plus what the far end spends before
  it answers plus the jitter the path adds. A timeout under that floor
  retransmits units that were never lost, and the duplicate traffic makes
  the congestion that caused the delay worse.
- The window has to cover the bandwidth-delay product or the transmitter
  stops and waits. That is a throughput question, separate from the
  timeout, and a conservative timeout does not compensate for a short
  window.
- The retry limit sets both a worst case and a residual. Worst case
  delivery is the attempts times the timeout plus the final round trip;
  residual loss is the per-attempt loss raised to the attempt count, and a
  design owes both numbers rather than one of them.
- Per-attempt loss compounds by multiplication, so the attempt count to
  reach a target is found by multiplying until the target is crossed.
  Raising a small probability to a power and comparing floats at the
  boundary is a worse way to answer the same question.
- Settings interact. Lengthening the timeout to stop spurious
  retransmissions lengthens the worst case delivery, which may then miss
  the deadline the retry limit was sized for; the set has to be checked
  together, not one parameter at a time.

## Workflow

1. State the link as the round trip, the acknowledgement delay at the far
   end, the jitter on the path, the data rate and the unit size.
2. State the configuration as the timeout, the window, the retry limit and
   the per-attempt loss probability, each with a flag saying whether it is
   commandable in flight.
3. Compute the timeout floor and compare the configured timeout against
   it with a relative tolerance, so a timeout set exactly at the floor is
   acceptable on every build host.
4. Compute the window the bandwidth-delay product asks for and compare it
   with the configured window, rounding the requirement up because a
   partial unit still occupies the link.
5. Compute the worst case delivery time the retry limit allows and the
   residual loss probability it leaves.
6. Where the residual misses the target, report the attempt count that
   would reach it, found by multiplying attempt by attempt.
7. Report any parameter that is not commandable as a finding in its own
   right, whatever its value, and summarise the recommended set so an
   operator can uplink it.

## Pitfalls

- Setting the timeout to the round trip alone. The far end still has to
  notice the unit and build an acknowledgement, and the path still has
  jitter; both sit on top of the propagation.
- Treating a short window as a timing problem. It costs throughput and no
  timer setting recovers it; the window is the parameter that moves.
- Quoting a retry limit without the worst case it implies. A generous
  limit can push the delivery of a single unit past the contact window,
  and the retransmissions then continue into a pass that is already over.
- Reporting the residual loss and calling the configuration adequate. A
  configuration that meets the residual and cannot be changed in flight
  still fails the clause.
- Tuning one parameter and re-reporting the whole set as sound. The
  timeout, the window and the retry limit trade against each other, so a
  changed value means the set is assessed again.

## Behavior contract (gate 3)

Parameter validation, the timeout floor, the bandwidth-delay window, the
worst case delivery time, the residual loss and the attempt count that
reaches a target, acceptance exactly at the timeout floor and the
commandability findings are exercised by the gate 3 contract test:
scripts/test_e50_arq_settings.py against
scripts/e50_arq_settings_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_arq_settings.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
