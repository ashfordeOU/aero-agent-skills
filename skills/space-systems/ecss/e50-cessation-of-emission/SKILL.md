---
name: e50-cessation-of-emission
description: "Evaluate whether a spacecraft radio can be commanded to stop transmitting under ECSS-E-ST-50C clause 5.3.3: size the worst-case time from ground request to carrier off along every inhibit path, separate a path that still works with a transmitter stuck on from one routed through the emitting chain itself or absent in safe mode, and decide whether the capability survives a single failure inside the deadline, reporting whether the gap is speed, independence, or a path that was never there. Use when a mission must guarantee it can vacate a frequency on request. Trigger: ecss, e-st-50c-communications-scope, cease-emission-command, transmitter-inhibit-path, rf-emission-termination, stuck-on-transmitter, emission-cessation-latency, single-failure-cessation."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: space-systems
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
clauses:
  - standard: ECSS-E-ST-50C Rev.2
    clause: 5.3.3
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-communications-scope, e50-cessation-of-emission, cease-emission-command, transmitter-inhibit-path, rf-emission-termination, stuck-on-transmitter, emission-cessation-latency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Cessation of Emission (space-systems/ecss/e50-cessation-of-emission)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.3.3 —
that the space-to-ground emission can be stopped by command — and the
question is whether a particular inhibit architecture actually delivers it.

## Domain quick reference

- The obligation is on the capability, not on a box. It is met by a path
  from a ground request to a carrier that is off, and the path is only as
  good as its weakest link: the receiver that takes the request, the
  decoder that acts on it, and the switch that removes drive from the
  power amplifier.
- The failure the requirement exists for is a transmitter that will not
  stop. An inhibit routed through the emitting chain — through the same
  unit, the same power rail, the same software task that is misbehaving —
  is not a second opinion on that failure. It is the same opinion.
- Safe mode is where cessation is most often wanted and least often
  available. A path that is configured out of existence when the platform
  drops to its survival configuration has no value in the case that
  matters, even though it tests perfectly in nominal mode.
- Reliance on flight software is a real limitation but not a
  disqualification. A software-decoded inhibit still works for the large
  majority of causes; it is recorded as a limitation so a reviewer can
  weigh it, and it is never allowed to be the only path.
- The quantity to hold is a budget, not a box latency. Ground reaction,
  uplink propagation and on-board execution all sit between the decision
  and the carrier going quiet, and only their sum can be compared with a
  regulatory or coordination deadline.
- One path is not a capability. Cessation that a single failure removes
  is cessation that is unavailable in exactly the compound cases that
  drive the requirement, so the time to quote is the time left after the
  fastest path has been taken away.

## Workflow

1. List every emitter the spacecraft can radiate from before looking at
   any path, since the obligation covers all of its transmissions and a
   single transmitter nobody can silence defeats it. Then validate each
   inhibit path as a record: an identifier, an execution latency, and
   whether it runs through the emitting chain, survives safe mode, and
   needs flight software. Reject a malformed record rather than
   assuming a default.
2. Name the impairments on each path, then split them: running through
   the emitting chain or vanishing in safe mode removes the path from the
   credible set; software dependence is recorded as a limitation.
3. Build the end-to-end budget for every credible path — ground reaction
   plus uplink delay plus on-board execution — and sort them.
4. Take the second-fastest credible budget as the time that survives one
   failure. With fewer than two credible paths there is no time to quote,
   and that is itself the finding.
5. Compare both the nominal and the degraded budget with the deadline
   using an explicit tolerance, so a budget that lands exactly on the
   bound reads the same on every host.
6. Return the verdict with the findings that produced it, so a reviewer
   can see whether the gap is speed, independence, or a path that never
   existed. Grade the design met only where each emitter can be brought
   off the air by telecommand at any point in the mission; a
   transmitter that can be silenced in some configurations and not
   others is not one the obligation lets through.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.3.3a | 6 |

## Pitfalls

- Counting an inhibit that is decoded by the transmitter's own controller
  as an independent path. It shares the failure it is meant to answer,
  and an architecture built of two such paths has no cessation capability
  at all.
- Quoting the fastest path's latency as the cessation time. That number
  is only true while nothing has failed, which is not the condition the
  requirement is written for.
- Budgeting the on-board execution alone. Uplink propagation on a distant
  mission can exceed every on-board contribution combined, and a budget
  that omits it will pass on paper and miss in flight.
- Treating safe-mode unavailability as a configuration detail. The
  survival configuration is the one a stuck emission is most likely to
  coincide with, so a path lost there is lost when it is needed.
- Using a bare strict comparison against the deadline. Budgets are sums
  of floats, and a design that lands exactly on its bound must not be
  read as compliant on one host and non-compliant on another.
- Reading software dependence as a pass or a fail. It is neither: it is a
  limitation to record, and the architecture is judged on whether a
  non-software path exists beside it.

## Behavior contract (gate 3)

The path validation, impairment naming, credible-path filtering, end-to-end
budget, single-failure response time, tolerance-based deadline comparison and
final verdict are exercised by the gate 3 contract test:
scripts/test_e50_cessation_of_emission.py against
scripts/e50_cessation_of_emission_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e50_cessation_of_emission.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
