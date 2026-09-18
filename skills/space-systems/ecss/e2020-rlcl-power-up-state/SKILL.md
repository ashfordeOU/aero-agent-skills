---
name: e2020-rlcl-power-up-state
description: "Assess whether a retriggerable current limiter comes up conducting on every occasion bus power becomes available, per clause 5.2.7.1.1 of ECSS-E-ST-20-20C. Use when a channel's power-up state has to hold for a cold start, a brown-out recovery, an undervoltage recovery, a bus reset and a commanded power cycle alike: refuse a turn-on that waits on an enable telecommand, catch an occasion nobody declared, time the output against its turn-on budget, and bound the retrigger cycle so a still-faulted line is retried rather than oscillated. Trigger: ecss, e-st-20-20c-clause-5-2-7-1-1, rlcl-power-up-conducting, retriggerable-limiter-default-state, limiter-enable-command-dependency, limiter-turn-on-latency-budget, rlcl-retrigger-cycle-bounds."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-7-1-1, e2020-rlcl-power-up-state, rlcl-power-up-conducting, retriggerable-limiter-default-state, limiter-enable-command-dependency, limiter-turn-on-latency-budget, rlcl-retrigger-cycle-bounds]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Retriggerable Limiter Power-Up State (space-systems/ecss/e2020-rlcl-power-up-state)

Use when the task is clause 5.2.7.1.1 of ECSS-E-ST-20-20C: a
retriggerable current limiter is conducting whenever bus power becomes
available. The clause is one short sentence and a channel either
satisfies it on every occasion power arrives or it has a power-up
lottery, so this leaf grades a declared power-up behaviour occasion by
occasion rather than at the cold start alone.

## Domain quick reference

- "Whenever" is the load-bearing word. Power becomes available at a cold
  start, on recovery from a brown-out, on recovery from a bus
  undervoltage, after a bus-side reset and on a commanded power cycle.
  A channel shown conducting at cold start and never exercised on the
  other four has been shown for one occasion out of five.
- An occasion nobody declared is a different finding from an occasion
  declared wrong. The first means the design has not been evaluated
  there; the second means it has been evaluated and fails. Reporting
  both as "non-compliant" hides which one needs a test and which one
  needs a redesign.
- The state belongs to the arrival of power, so nothing may stand in
  front of it. A limiter that conducts only after an enable telecommand
  is dark exactly in the case the clause exists for -- the one where the
  commanding chain is itself coming back up and cannot issue the
  command it is waiting to be issued.
- Conduction has a deadline as well as a value. The bus-valid dwell the
  channel insists on before it acts, plus its own driver delay, is the
  time the downstream load spends unpowered; past the turn-on budget the
  load starts outside its own window even though the limiter is
  nominally on.
- The retrigger behaviour is part of the same state, because a limiter
  that comes up into a line that is still faulted will limit, drop, wait
  and try again. That cycle needs a rest long enough for the line to
  actually clear, a conducting share small enough that the fault is not
  held near full draw, and a repetition rate that reads as a retry and
  not as an oscillator parked on the distribution.

## Workflow

1. Validate the power-up policy: turn-on budget, admissible bus-valid
   dwell, minimum rest between attempts, duty ceiling, rate ceiling and
   the attempt floor that makes the behaviour retriggerable at all.
2. Name each declared occasion against the known set of ways power
   becomes available; refuse an unrecognised one and refuse the same
   occasion declared twice.
3. Evaluate each occasion in order: an undeclared or indeterminate state
   first, then output off, then a dependency on an enable command, then
   the turn-on latency against its budget.
4. Compute the latency as bus-valid dwell plus driver delay, so the
   number compared against the budget is the time the load is dark and
   not the driver datasheet figure alone.
5. List the occasions never covered at all and keep them separate from
   the ones covered and failed.
6. Assess the retrigger cycle: rest time, conducting share and
   repetition rate against their bounds, and the attempt count against
   the floor.
7. Rank the channel at its worst standing -- unevaluated, command
   dependent, not conducting, late, unbounded retrigger -- and roll up
   every finding with the occasion that produced it.

## Pitfalls

- Demonstrating the power-up state at the cold start and calling the
  clause closed. The cold start is the tidy occasion: rails come up in
  order, nothing is latched and nothing is still faulted. Brown-out
  recovery is where a channel that carries state from before the dip
  comes back dark.
- Reading an enable command in the turn-on sequence as a safety feature.
  It is a dependency, and it is a dependency on the one subsystem least
  likely to be available at the moment power returns.
- Timing the turn-on from the driver alone. A channel that waits on a
  long bus-valid qualification before it even starts is late by the
  amount it waited, and the load feels the whole of it.
- Leaving an occasion out of the declaration and reading the resulting
  silence as a pass. Nothing in a table of four rows says whether the
  fifth occasion works.
- Treating any retrigger as containment. A limiter re-arming every few
  milliseconds into a hard short is a current source with a chopper on
  it, and the distribution sees every attempt.
- Declaring a single attempt and still calling the channel
  retriggerable. One try is a latching limiter with extra words.

## Behavior contract (gate 3)

The power application event vocabulary, the turn-on latency built from
bus-valid dwell and driver delay, the per-occasion evaluation with its
undeclared, off, command-dependent and late categories, the uncovered
occasions kept separate from the covered ones, the retrigger rest, duty,
rate and attempt bounds, and the worst-standing channel verdict are
exercised by the gate 3 contract test:
scripts/test_e2020_rlcl_power_up_state.py against
scripts/e2020_rlcl_power_up_state_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_e2020_rlcl_power_up_state.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
