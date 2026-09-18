---
name: e2020-retrigger-function-enable-control
description: "Evaluate whether a retriggerable limiter really lets its automatic retrigger behaviour be switched off and switched back on, under ECSS-E-ST-20-20C clause 5.2.6.2.1. Use when a power design claims retrigger is commandable and that claim has to become a verdict: refuse a design declaring no control, reject a one-way inhibit that can never be put back, name every required command path that cannot reach the control, require a state read-back, and compute the worst-case settling time between a disable command and the last re-energisation the load can still see, including one racing dead-time cycle. Trigger: ecss, e-st-20-20c-clause-5-2-6-2-1, retriggerable-limiter-retrigger-enable-control, retrigger-function-two-way-commandability, retrigger-control-state-telemetry, retrigger-disable-settling-time, retrigger-control-command-path-reach."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-6-2-1, e2020-retrigger-function-enable-control, retriggerable-limiter-retrigger-enable-control, retrigger-function-two-way-commandability, retrigger-control-state-telemetry, retrigger-disable-settling-time, retrigger-control-command-path-reach]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Limiters -- Retrigger Function Enable Control (space-systems/ecss/e2020-retrigger-function-enable-control)

Use when the task is the clause 5.2.6.2.1 question of ECSS-E-ST-20-20C:
a retriggerable limiter re-closes on its own after a dead time, and the
spacecraft has to be able to turn that automatic behaviour off and turn
it back on.

## Domain quick reference

- The clause is about the control, not about the trip threshold. What
  current opens the limiter, and how many attempts it makes, are
  separate design questions; this one asks only whether the retrigger
  behaviour itself is commandable.
- The control has to work both ways. A limiter whose retrigger can be
  disabled but never restored is a one-shot inhibit: after its first use
  the retrigger behaviour is gone for the rest of the mission, and
  nothing on board can bring it back. That is the single most common
  shape of a control that passes a paper review and fails in flight.
- The control has to be reachable from every command path the project
  declares, not from one of them. A retrigger inhibit that lives only in
  a ground telecommand is absent exactly when an onboard procedure needs
  it during a pass gap; one that lives only onboard cannot be exercised
  from ground when the onboard software is the thing under suspicion.
- The control state has to be observable. An operator with no read-back
  has to infer the present state from the last command they believe
  arrived, and a belief is not a state. Deciding whether it is safe to
  close a limiter onto a suspect load from an inferred state is the
  decision this read-back exists to support.
- The control takes time to bite, and the time is not the command
  latency. A disable landing inside a dead time may arrive after the
  decision point of the attempt already in flight, so the load still
  sees one further re-energisation. The worst case is the latency plus,
  when that race is possible, one whole trip and dead-time cycle.
- A design that claims the race cannot happen has made the settling
  budget much easier and has taken on the burden of showing it. The
  claim is reported as an advisory rather than accepted silently.

## Workflow

1. Validate the control policy first: which command paths the project
   requires, the settling budget, whether a state read-back is required,
   and the advisory band. An empty required-path list, or an advisory
   band above the whole budget, is refused rather than used.
2. Validate the limiter design: a non-blank identifier, both direction
   flags boolean, a non-negative command latency, positive dead time and
   trip response, and at least one command path whenever any control is
   declared at all.
3. Determine which directions are supported. Neither direction closes
   the assessment on control not provided; one direction closes it on
   not commandable, with the one-shot inhibit named.
4. Compare the declared command paths against the required set and name
   every required path that cannot reach the control, not the first one
   found. An extra path beyond the required set is not a finding.
5. Require the retrigger control state in telemetry unless the policy
   explicitly waives it.
6. Compute the worst-case settling time as the command latency plus, if
   a command can race the retrigger in flight, one trip-and-dead-time
   cycle. Compare it against the budget with a named tolerance, a
   settling time landing exactly on the budget being admissible.
7. Close on one verdict: retrigger control not provided, not
   commandable, settling budget exceeded, or commandable both ways --
   and report the settling time, its margin and any advisory beside it.

## Pitfalls

- Accepting a disable-only control. The clause asks for the behaviour to
  be enabled or disabled; a path that only removes the retrigger, with
  no way back, loses a capability permanently on its first use.
- Budgeting the disable against the command latency alone. The command
  that lands mid dead time is the one the fault protection will meet, so
  the budget has to carry the racing cycle unless the race is shown to
  be impossible.
- Proving reach from one command path. Ground-only and onboard-only
  controls each go missing in exactly the situation the other one is
  there for, so the required set is checked in full.
- Treating the control state as known because a command was sent. Sent
  is not applied; without a read-back the state is an inference, and the
  next decision rests on it.
- Widening the settling budget to admit a design that lands just past
  it. An equality at the limit is a representation question, handled by
  the tolerance inside the comparison; the budget stays as declared.

## Behavior contract (gate 3)

The policy validation, design validation, supported-direction
determination, required command-path reach, state read-back
requirement, worst-case settling computation with its racing dead-time
cycle, the budget comparison and the advisories are exercised by the
gate 3 contract test:
scripts/test_e2020_retrigger_function_enable_control.py against
scripts/e2020_retrigger_function_enable_control_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2020_retrigger_function_enable_control.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
