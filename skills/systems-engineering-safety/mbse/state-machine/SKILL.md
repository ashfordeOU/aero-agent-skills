---
name: state-machine
description: "Use when you must model or verify SysML state machine behavior in an aerospace systems engineering model: build state machines with states, transitions, events, guards, and actions, simulate an event sequence to produce the firing trace, compute the reachable state set from the initial state, and detect unreachable states and transition conflicts where two guards enable the same event. Produces the firing trace, the reachable set, and the conflict list that gate the behavioral model review. Trigger: state machine, statechart, transitions, guards, events, reachability, SysML behavior."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: arp4754a
    reference-only: true
gated: false
domain: systems-engineering-safety
pack: systems-engineering-safety
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: systems-engineering-safety
  subdomain: mbse
  tags: [state-machine, state-transitions, event-guards, orthogonal-regions, reachability-analysis, transition-conflict]
  version: 0.1.0
  author: AeroSkills
---

# SysML State Machine Modeling (systems-engineering-safety/mbse/state-machine)

Use when the task is behavioral modeling with SysML state machines:
states, transitions, events, guards, actions, and the reachability or
conflict review of the resulting model.

## Domain quick reference

- A state machine models behavior as states connected by transitions.
- A transition fires on an event when its guard condition is true;
  firing may run actions and moves the machine to a target state.
- The initial state is the entry point; a state is reachable when a
  chain of transitions leads to it from the initial state.
- A transition conflict exists when one event enables more than one
  transition from the same state and no priority resolves the choice.
- Review checks that every state is reachable and no event is
  ambiguous, per the behavioral model review in the ARP4754A
  development process.

## Workflow

1. Collect the states, initial state, and the transition list with
   events, guards, and actions.
2. Validate the machine so every transition endpoint exists.
3. Simulate the event sequence and record the firing trace.
4. Compute the reachable state set from the initial state.
5. List the unreachable states and any transition conflicts, then gate
   the behavioral model review.

## Pitfalls

- Firing a transition without checking its guard; a false guard must
  leave the machine in its current state.
- Two enabled transitions on one event with no priority; the model is
  ambiguous and the conflict must be resolved.
- A guard missing from the evaluation context; treat an absent guard
  as blocking, not as enabled.
- Declaring a state that no transition chain can reach; the review
  must list it as unreachable.

## Behavior contract (gate 3)

The firing, trace, and reachability logic is exercised by the gate 3
contract test: scripts/test_state_machine.py against
scripts/state_machine_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_state_machine.py

## Compliance

- Standards referenced, not reproduced: ARP4754A text is proprietary
  (SAE); summary-only per standards-map.yaml. SysML state machine
  semantics are common modeling methodology.
- compliance: STANDARDS-REF, gated: false.
