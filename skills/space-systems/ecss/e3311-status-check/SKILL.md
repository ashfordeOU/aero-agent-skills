---
name: e3311-status-check
description: "Verify the safe/arm status indication of an explosive subsystem against ECSS-E-ST-33-11C clause 4.8.4. Use when the task is proving an operator can tell which state the hardware is actually in: resolving the displayed state from the sensing channels and falling to indeterminate whenever they disagree or one falls silent, checking the channels share neither a sensing principle nor a power source, grading every monitoring current against the no-fire current and rejecting a channel that senses through the initiation circuit, reconciling the displayed state with the reported barrier position, and confirming the indication exists through each arming phase. Trigger: ecss, e-st-33-11-explosive-subsystem-scope, safe-arm-status-indication, safe-arm-barrier-position-sensing, initiation-monitor-current-margin, status-indication-independence, indeterminate-arm-state."
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
  tags: [ecss, e-st-33-11-explosive-subsystem-scope, e3311-status-check, safe-arm-status-indication, safe-arm-barrier-position-sensing, initiation-monitor-current-margin, status-indication-independence, indeterminate-arm-state]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Explosive Subsystems — Safe/Arm Status Check (space-systems/ecss/e3311-status-check)

Use when the task is the status-indication requirement of
ECSS-E-ST-33-11C clause 4.8.4 -- showing that the safe-and-arm state an
operator reads off a panel is the state the hardware is in, not the
state it was commanded to and not the state one sensor believes.

## Domain quick reference

- A safe-and-arm device has two states anyone is allowed to act on,
  and the indication exists so that the decision to approach, to
  power, or to launch is made against the hardware rather than against
  the command history.
- Indeterminate is a state, not a missing answer. When the sensing
  channels disagree, or one of them reports nothing at all, the honest
  output is that the state is unresolved -- and the operating rule
  that follows is to treat the device as armed.
- Independence is what makes two channels worth more than one. Two
  microswitches on the same bus fail together for a dozen reasons, so
  the count of channels is graded alongside the count of distinct
  sensing principles and the count of distinct power sources.
- Reading a status must not arm anything. Every monitoring current
  that flows anywhere near the device is graded against the no-fire
  current the same way a stray current is, and a channel that senses
  through the initiation circuit is a finding regardless of how small
  its current is.
- The indication and the barrier are two independent statements about
  the same thing, so they are reconciled rather than trusted
  separately. Safe implies an interposed barrier, armed implies an
  aligned one, and any other pairing means one of the two is lying.
- Availability is a phase question. An indication that is valid at the
  endpoints but blind during the arming transition leaves the operator
  without a state during precisely the interval in which the state is
  changing.

## Workflow

1. Normalize the sensing channels and reject the set outright on a
   duplicate identifier, an unknown sensing principle or an unknown
   reading, because a channel nobody can categorize cannot be voted
   with the others.
2. Resolve the displayed state. Unanimous channels give their state;
   any disagreement, and any channel reporting no signal, gives
   indeterminate, and the silent channels are named.
3. Grade independence: channel count, distinct sensing principles and
   distinct power sources, each against its own policy floor, so a
   report says which kind of commonality was found.
4. Grade every monitoring current against the declared fraction of the
   no-fire current, report each channel's margin, and raise a separate
   finding for any channel routed through the initiation circuit.
5. Reconcile the resolved state with the reported barrier position,
   and treat an unresolved indication as unable to agree with any
   barrier position at all.
6. Walk the arming phases, name any phase in which the indication is
   unavailable, and close with the overall verdict and the list of
   checks that produced it.

## Pitfalls

- Displaying a state from a single channel because the second one is
  silent. A silent channel is not a concurring channel; treating it as
  one converts a detected fault into a confident wrong answer.
- Counting redundancy by boxes rather than by failure modes. Two
  channels of the same sensing principle on the same bus are one
  channel with a spare connector.
- Taking a small monitoring current as automatically safe. The
  comparison that matters is with the no-fire current of this device,
  and a current that is negligible for one initiator is a fraction of
  the no-fire level for another.
- Sensing arm status through the firing loop. It gives an unambiguous
  reading and it does so by putting current where the safety case
  spent its whole length keeping current out.
- Trusting the indication over the barrier, or the reverse. They
  disagree only when something is wrong, and the safe reading of a
  disagreement is the armed one.
- Grading the indication only at rest. The transition is where a
  barrier can stall between positions, and an indication that goes
  blank there hides the one state that needs to be visible.

## Behavior contract (gate 3)

The channel normalization, state resolution, independence counting,
monitoring-current grading, barrier reconciliation, phase availability
and overall verdict are exercised by the gate 3 contract test:
scripts/test_e3311_status_check.py against
scripts/e3311_status_check_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e3311_status_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
