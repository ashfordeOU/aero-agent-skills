---
name: e50-telecommand-receipt-confirmation
description: "Monitor a window of outstanding telecommands against the receipt confirmation obligation of ECSS-E-ST-50C clause 5.6.14.8, which asks that receipt be confirmed to the sender. Derive the shortest deadline the round trip, onboard processing and margin can actually meet, then grade each command as confirmed, confirmed after its deadline had already expired, pending or timed out, and attach the retransmit-or-escalate action each state earns. Separate a confirmation that is repeated or names a command nobody sent. Use when setting a confirmation timeout or triaging unacknowledged uplinks. Trigger: ecss, e-st-50-communications, telecommand-receipt-confirmation, telecommand-confirmation-timeout, telecommand-retransmission-limit, late-telecommand-confirmation, unsolicited-telecommand-confirmation."
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
  tags: [ecss, e-st-50-communications, e50-telecommand-receipt-confirmation, telecommand-confirmation-timeout, telecommand-retransmission-limit, late-telecommand-confirmation, unsolicited-telecommand-confirmation, telecommand-confirmation-deadline]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Telecommand Receipt Confirmation (space-systems/ecss/e50-telecommand-receipt-confirmation)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.6.14.8 —
that receipt of a telecommand is confirmed to the sender — and the question is
what the ground should conclude when a confirmation has not arrived yet.

## Domain quick reference

- A confirmation only means something against a deadline, and the
  deadline is not a free parameter. It is bounded below by the round
  trip, the onboard processing and whatever margin the operator wants,
  and anything shorter declares timeouts nobody can avoid.
- A deadline set too short does not merely produce noise. The ground
  retransmits commands that were received perfectly well, which is a
  cheap outcome for a status request and an expensive one for anything
  that moves.
- A late confirmation is a third state, not a success. By the time it
  lands the retransmission has already gone, so the spacecraft may act
  on the command twice unless the command is idempotent — and knowing
  which it is belongs in the assessment.
- Timed out and lost are different claims. A timed-out command is one
  the ground has stopped waiting for; whether it was received is exactly
  the thing the missing confirmation does not say.
- The retransmission limit is where the fault changes owner. Past it the
  command is not the problem, the link is, and the report should go to
  whoever can act on that rather than back around the same loop.
- Confirmations arriving are evidence too. One naming a command nobody
  sent, or a command already confirmed, points at a duplicated uplink or
  a counter that has slipped, and discarding it silently loses that.

## Workflow

1. Compute the minimum deadline from the geometry — round-trip light
   time plus onboard processing plus margin — before looking at any
   configured value.
2. Compare the configured deadline against that minimum, and stop there
   if it is shorter: every other finding in the window is an artefact of
   the configuration rather than a fact about the link.
3. Validate the window: unique command identifiers, no confirmation
   dated before its dispatch, at least one attempt recorded per command.
4. Grade each command against the deadline into confirmed, confirmed
   late, pending, or timed out, comparing at the bound with a relative
   tolerance so a confirmation landing exactly on time is on time.
5. Attach the action each state earns: nothing for confirmed and
   pending, retransmit for a timeout inside the attempt budget, escalate
   for one past it.
6. Grade arriving confirmations against what was sent and what is
   already confirmed, and report duplicates and unsolicited ones rather
   than dropping them.
7. Report the worst observed latency alongside the deadline — it is the
   number that says whether the deadline has any margin left in practice.

## Pitfalls

- Setting the confirmation timeout from the one-way light time. It is a
  round trip plus processing, and halving it turns every distant pass
  into a retransmission storm.
- Treating a late confirmation as a plain success. The retransmission
  has already been sent, and for a non-idempotent command that is a
  second execution nobody has accounted for.
- Reading a timeout as proof the command was not received. It is proof
  that no confirmation arrived, which is also what a lost downlink looks
  like.
- Retransmitting without a limit. The same command cycles for the rest
  of the pass while the actual fault — the link — goes unreported.
- Discarding a confirmation that matches nothing. It is the clearest
  evidence available of a duplicated uplink or a slipped counter, and it
  only exists once.
- Comparing latency against the deadline with a bare inequality. A
  confirmation landing exactly on the deadline then counts as late on
  some hosts and on time on others.

## Behavior contract (gate 3)

Window validation with unique identifiers and causally ordered confirmations,
the geometry-derived minimum deadline and the achievability test at its exact
bound, the four command states including the exact-deadline cases, the
retransmit-and-escalate action ladder, duplicate and unsolicited confirmation
grading, the verdict ordering that puts an unachievable deadline above every
command state, and the worst-latency report are exercised by the gate 3
contract test:
scripts/test_e50_telecommand_receipt_confirmation.py against
scripts/e50_telecommand_receipt_confirmation_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_e50_telecommand_receipt_confirmation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
