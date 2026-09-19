---
name: e7041-suspending-and-resuming
description: "Model how a running on-board control procedure is held and released, under ECSS-E-ST-70-41C clause 6.18.4.6. Use when the task is pausing a run without throwing it away: landing a hold on a step boundary rather than half way through a step nobody described as interruptible, reporting a procedure that finished before its hold arrived as terminated rather than held, resuming at the step it paused on instead of the first one, keeping the engine slot a hold never gives back, and grading an open hold against the longest the mission allows. Trigger: ecss, e-st-70-41c, pus-packet-utilisation, obcp-suspend-and-resume, obcp-hold-at-step-boundary, obcp-resume-at-held-step, obcp-late-suspend-termination, obcp-maximum-hold-duration."
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
  tags: [ecss, e-st-70-41-packet-utilisation-scope, e7041-suspending-and-resuming, obcp-suspend-and-resume, obcp-hold-at-step-boundary, obcp-resume-at-held-step, obcp-late-suspend-termination, obcp-maximum-hold-duration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Packet Utilisation — Suspending and Resuming (space-systems/ecss/e7041-suspending-and-resuming)

Use when the task is the hold and release of ECSS-E-ST-70-41C clause
6.18.4.6 -- telling a running on-board control procedure to stop where
it is and keep everything it has, and letting it carry on later from
exactly there.

## Domain quick reference

- A hold is not a stop. Stopping ends the run and the procedure would
  have to begin again at its first step. Holding keeps the step
  pointer, the bound arguments and the engine slot, so a release
  carries on from where it paused. Every rule here protects that
  distinction.
- A hold lands on a step boundary, never inside a step. A step is the
  unit the procedure was written in, and halting half way through one
  leaves the spacecraft in a configuration the author never described:
  a valve driven and not confirmed, a heater commanded and not
  verified.
- So a hold commanded mid-step is pending, not effective. Between the
  command and the boundary the procedure is still running, and a ground
  that reads the acknowledgement as a hold is reasoning about a
  spacecraft that is still moving.
- The late hold. If the step in progress was the last one, the run ends
  before the hold can take effect. There is nothing left to release,
  and the honest report is terminated with the hold too late -- report
  it as held and the ground waits forever to resume something that
  finished.
- Holding is not idempotent. A hold commanded on a procedure that is
  already holding, or that already has one pending, is a refusal, not a
  no-op: the second command means the operator's model of the
  spacecraft is wrong and the refusal is what tells them.
- A hold costs an engine slot the whole time it lasts. It is not cheap
  parking. An unbounded hold is a slot lost quietly, so the longest
  hold the mission tolerates is a real limit and an over-run is a
  decision -- release it or abort it -- not a status.
- Hold time accumulates across holds. One procedure held three times
  for twenty minutes has cost an hour of its slot, and only the running
  total says so.

## Workflow

1. Validate the instance: a known state, a step pointer inside the
   procedure, and a hold time that is present exactly when the state
   says it is holding.
2. Refuse a hold on anything that is not running, and refuse a second
   hold whether the first is landed or still pending. Name which.
3. If a step is in progress, record the hold as pending and leave the
   state running. Report the pending state as pending.
4. If no step is in progress, the hold lands immediately. Record the
   moment and the step it landed on.
5. When a step completes, advance the pointer first, then decide. Past
   the last step the procedure has terminated, and a pending hold is
   reported as having arrived too late.
6. Otherwise land a pending hold at the new boundary and record the
   step, so the release has somewhere to resume to.
7. On release, require a held procedure, add the elapsed hold to the
   running total, count the release, and carry on from the held step.
   Refuse a release whose time predates the hold.
8. Grade an open hold against the mission limit, treating a hold
   exactly at the limit as within it, and report the engine slot it is
   still holding.
9. For an event sequence, refuse one that goes backwards in time, and
   keep each outcome with its moment and the state it produced.

## Pitfalls

- Reading a hold acknowledgement as a landed hold. Mid-step it is
  pending, and the spacecraft is still executing while the ground
  thinks it stopped.
- Halting inside a step to make a hold prompt. The configuration left
  behind is one no procedure step describes, and no release path
  returns from it cleanly.
- Reporting a procedure that ran out as held. The ground then waits to
  resume a run that has already finished, and nothing on the link ever
  corrects it.
- Resuming from the first step. That is a restart wearing the word
  resume, and for anything already partly done it repeats actions that
  were never meant to run twice.
- Treating a repeated hold as harmless. The refusal is the only signal
  that the operator's model of the spacecraft has drifted.
- Assuming a hold releases the engine slot. The concurrency budget then
  reads free while it is not, and the next activation is refused by the
  engine rather than by the plan.
- Measuring only the current hold. The cost of a procedure held
  repeatedly is the accumulated total, not the last interval.

## Behavior contract (gate 3)

The instance validation and its state and hold-time consistency
checks, immediate versus pending holds, the pending hold landing at the
next boundary, the late hold reported as termination, refusal of a
repeated or pending-duplicate hold, refusal of a release on a running
or pending instance, resumption at the held step, accumulated hold
time and release count, engine slot retention while held, the
mission hold limit with exact-limit acceptance, and the time-ordered
event sequence are exercised by the gate 3 contract test:
scripts/test_e7041_suspending_and_resuming.py against
scripts/e7041_suspending_and_resuming_logic.py (stdlib unittest,
offline). Run: python3 scripts/test_e7041_suspending_and_resuming.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
