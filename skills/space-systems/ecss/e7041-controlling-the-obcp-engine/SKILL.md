---
name: e7041-controlling-the-obcp-engine
description: "Model the engine-level control of an on-board control procedure engine, under ECSS-E-ST-70-41C clause 6.18.5.1. Use when an engine restart left procedures that the ground expected to resume, or when a resume restarted one somebody had deliberately stopped: separating a stop, which terminates the live procedures for good, from a hold, which suspends them reversibly, releasing on resume only the procedures the engine itself held, refusing an activation into an engine that is stopped or held, and refusing one past the engine's simultaneous-procedure limit rather than queueing it. Trigger: ecss, e-st-70-41c, obcp-engine-control, obcp-engine-stop-terminates-procedures, obcp-engine-hold-and-resume, obcp-individually-held-procedure, obcp-engine-procedure-limit, obcp-activation-refused-engine-state."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-controlling-the-obcp-engine, obcp-engine-control, obcp-engine-stop-terminates-procedures, obcp-engine-hold-and-resume, obcp-individually-held-procedure, obcp-engine-procedure-limit]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Controlling the OBCP Engine (space-systems/ecss/e7041-controlling-the-obcp-engine)

Use when the task is the engine control of ECSS-E-ST-70-41C clause
6.18.5.1 -- the eleven requirements that start, stop, hold and resume
the OBCP engine itself, and fix what each of those does to every
procedure the engine is hosting at the time.

## Domain quick reference

- The engine has its own state, separate from the state of any
  procedure. Stopped, running, held: the procedures follow it, and
  they do not all follow it the same way.
- Stopping is destructive and one-directional. An engine that stops
  terminates the procedures it was running; they do not wait, and
  starting the engine again does not bring them back. A stop is
  therefore a decision about the procedures, not only about the
  engine.
- Holding is reversible and narrow. An engine hold suspends the
  procedures that were running at that moment. An engine resume
  releases exactly those and nothing else.
- A procedure held by its own command was not held by the engine, so
  the engine's resume leaves it held. Releasing it as well is the
  defect this clause exists to prevent: a procedure somebody stopped
  on purpose restarts because an unrelated engine hold happened to
  cover it.
- Activation follows the engine. An engine that is stopped or held
  does not accept an activation, and the refusal is immediate rather
  than a queue that empties when the engine comes back -- a queued
  activation would fire in conditions nobody re-checked.
- The engine hosts a bounded number of simultaneous procedures, and a
  held procedure still occupies one of those slots. It is suspended,
  not unloaded, so the limit is reached exactly as fast whether the
  procedures are stepping or waiting.
- Loading is not activating. A loaded procedure is present and idle;
  it consumes no slot and can be loaded while the engine is stopped.
- An engine command that the current state does not permit is refused
  and leaves the state alone. Starting a running engine and resuming a
  running engine are both refusals, not silent successes.

## Workflow

1. Build the engine with its simultaneous-procedure limit and its
   initial state, and refuse a limit below one procedure.
2. Normalise each command: an engine command carries no procedure
   identifier, a procedure command must carry one.
3. Look the command up in the engine transition table; if the current
   state does not permit it, raise the refusal finding and leave the
   engine untouched.
4. On a stop, terminate every live procedure and name them in the
   finding -- the termination is the part the ground has to know
   about, not the state change.
5. On a hold, suspend the procedures that were running and mark each
   as held by the engine, so the hold's own scope is recorded.
6. On a resume, release only the procedures marked as held by the
   engine and report by name those left held by their own command.
7. On an activation, check the engine state, then that the procedure
   is loaded, then that it is not already live, then the limit; refuse
   at the first failure rather than partially activating.
8. Report the engine state, each procedure's state, the spare
   capacity, and the findings indexed by the command that raised them.

## Pitfalls

- Using a stop where a hold was meant. Both quiet the procedures; only
  one of them lets you carry on afterwards.
- Expecting terminated procedures to resume with the engine. The
  engine comes back and the procedures do not, which reads in
  telemetry as a failed restart rather than a completed stop.
- Releasing every held procedure on an engine resume. The individually
  held one restarts, and it restarts into conditions that were the
  reason it was held.
- Queueing an activation that arrived while the engine was stopped. It
  fires later, against a spacecraft state nobody re-evaluated.
- Counting only stepping procedures against the engine limit. A held
  procedure still occupies its slot, so the limit arrives earlier than
  the count suggests.
- Reading a refused engine command as a no-op worth ignoring. It means
  the ground's model of the engine state is wrong, which is a finding
  about the ground, not about the engine.

## Behavior contract (gate 3)

The engine transition table, refusal of impermissible engine commands,
destructive stop with named terminations, reversible hold, resume
scoped to engine-held procedures, retention of individually held
procedures, refusal of activation while stopped or held, unknown and
already-live procedure refusals, the simultaneous-procedure limit with
held procedures counted, and the indexed finding report are exercised
by the gate 3 contract test:
scripts/test_e7041_controlling_the_obcp_engine.py against
scripts/e7041_controlling_the_obcp_engine_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e7041_controlling_the_obcp_engine.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
