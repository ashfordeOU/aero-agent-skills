---
name: e50-deterministic-performance
description: "Compute the worst-case end-to-end latency and the jitter band a time-critical message meets on an on-board network under ECSS-E-ST-50C clause 5.7.1.2, where performance has to be deterministic rather than merely fast on average. Sum medium-access wait, per-hop store-and-forward time, blocking by a lower-priority frame already in flight and interference from every higher-priority stream through a response-time fixed point, then compare the bound with the deadline. Use when qualifying a network for control-loop traffic or reviewing a latency budget quoted as an average. Trigger: ecss, e-st-50-communications, onboard-network-determinism, worst-case-end-to-end-latency, network-jitter-band, priority-blocking-delay, response-time-fixed-point, control-loop-deadline-margin."
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
    clause: 5.7.1.2
    items: [a]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50-communications, e50-deterministic-performance, onboard-network-determinism, worst-case-end-to-end-latency, network-jitter-band, priority-blocking-delay, response-time-fixed-point, control-loop-deadline-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Deterministic Performance (space-systems/ecss/e50-deterministic-performance)

Use when an on-board network has to carry time-critical traffic under
ECSS-E-ST-50C clause 5.7.1.2 — establishing that the latency of a path is
bounded, and what that bound is, rather than reporting how fast it usually is.

## Domain quick reference

- Determinism is a property of the worst case, not of the mean. A path
  that averages a tenth of its deadline and cannot be shown to have an
  upper bound has not met the clause; a slower path with a proven bound
  inside the deadline has.
- The bound on one link is made of four parts. The message's own
  transmission time; blocking by one lower-priority frame that was
  already on the wire and cannot be pre-empted; interference from every
  higher-priority stream that can win arbitration while the message
  waits; and the fixed medium-access overhead the link charges.
- The interference term is recursive. A longer wait admits more
  higher-priority arrivals, which lengthen the wait again, so the
  response time is the fixed point of R = C + B + sum ceil(R/T_i)*C_i,
  iterated from R = C + B until it stops moving.
- That fixed point exists only while the link load stays below one. At
  or above capacity the queue grows without limit and there is no bound
  to quote — the honest result is "unbounded", not a large number
  obtained by stopping the iteration early.
- End to end, a store-and-forward path pays the per-link bound at every
  hop plus the switching cost at each intermediate node. Jitter is the
  spread between that bound and the same path with an empty network,
  and it is often the number a control loop actually cares about.

## Workflow

1. State the path: message size, its own repetition period, link rate,
   hop count, per-hop switching cost and the fixed medium-access
   overhead. A zero rate, a zero period or a zero-hop path is an input
   error, not a degenerate case to be clamped.
2. Declare the blocking frame — the largest lower-priority frame the
   link can already be sending — and every higher-priority stream as a
   size and a period. An empty rival set is allowed but is reported as
   an idle-path assumption, not as a worst case.
3. Compute the link load. At or above one, stop and report the path as
   unbounded; the remaining numbers would be arithmetic without meaning.
4. Iterate the response-time fixed point on one link, snapping a
   ceiling that lands on an integer so an arrival pattern dividing the
   response time exactly is counted identically on every build host.
5. Extend to the full path: the per-link bound at each hop, plus the
   switching cost at each intermediate node.
6. Compute the idle-path latency the same way with no blocking and no
   rivals, and take the jitter as the spread between the two.
7. Work steps 2 to 6 again for every load the network is specified to
   carry, restating the blocking frame and the higher-priority streams
   at step 2 for each one, up to the heaviest offered traffic it is
   permitted to see. Re-running the arithmetic on the same declared
   rivals only reproduces the operating point it came from, so the
   second case has to be declared, not recomputed. The clause is a
   claim about all of the loads, so one bounded operating point settles
   nothing, and a single load case with no bound settles the clause on
   its own.
8. Compare the bound with the deadline and the spread with the jitter
   budget, absorbing representation error at each boundary with a named
   tolerance rather than by relaxing the requirement. Report the
   verdict, the margin and every finding, load case by load case.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.7.1.2a | 7 |

## Pitfalls

- Quoting an average or a measured maximum as the bound. Neither is a
  bound; a measurement only says the worst case was not reached during
  the run, which is the weakest possible evidence for determinism.
- Counting each higher-priority stream once. One activation is correct
  only when the response time stays inside that stream's period; past
  it the stream arrives again, and a single-activation sum
  systematically understates a busy path.
- Returning the iterate reached at the iteration limit on a saturated
  link. That converts "no bound exists" into a plausible number, which
  is the worst possible failure mode for this clause.
- Forgetting blocking because the message is the highest priority. The
  top-priority message still waits for whatever non-pre-emptable frame
  is already on the wire, and on a long-frame link that term dominates.
- Charging switching cost per hop instead of per intermediate node. A
  two-hop path crosses one switch, and the off-by-one inflates every
  multi-hop budget in the same direction.
- Deciding the deadline comparison with a bare inequality. A path sized
  to exactly meet its deadline then passes on one build host and fails
  on another, which makes the verdict a property of the machine.

## Behavior contract (gate 3)

Input validation, the transmission and load models, the idle-path
latency, the response-time fixed point including its second activation
and its non-existence on a saturated link, the jitter spread, and the
deadline and jitter verdicts at and past their bounds are exercised by
the gate 3 contract test:
scripts/test_e50_deterministic_performance.py against
scripts/e50_deterministic_performance_logic.py (stdlib unittest,
offline).
Run:
python3 scripts/test_e50_deterministic_performance.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
