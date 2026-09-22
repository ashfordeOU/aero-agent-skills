---
name: e50-essential-telecommand-distribution
description: "Audit how essential telecommands reach the units they act on under ECSS-E-ST-50C clause 5.4.4, whose four requirements are about the commands, not a route: they are decoded and their control signals delivered while every other unit on board, the command and data management unit included, is dead; the set, with encoding and effect, is agreed at the preliminary design review; they switch power to key equipment on and off and force a changeover to the redundant side; and where an operation is critical, nothing in their execution leans on a software function. The four properties graded here — hardware decoding, segregation, mode availability, latency — are this leaf's, not the clause's. Use when judging whether a high-priority command survives a dead processor or a safe mode. Trigger: ecss, e-st-50c-communications-scope, essential-telecommand-distribution, high-priority-command-route, hardware-decoded-command, command-path-segregation, safe-mode-command-availability, essential-command-latency."
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
    clause: 5.4.4
    items: [a, b, c, d]
    relation: verifies
metadata:
  domain: space-systems
  subdomain: ecss
  tags: [ecss, e-st-50c-communications-scope, e50-essential-telecommand-distribution, high-priority-command-route, hardware-decoded-command, command-path-segregation, safe-mode-command-availability, essential-command-latency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Essential Telecommand Distribution (space-systems/ecss/e50-essential-telecommand-distribution)

Use when the task is ECSS-E-ST-50C clause 5.4.4 — what an essential
telecommand has to be able to do, and how its route reaches the unit it acts
on — and the question is whether a given high-priority command route actually
meets every part of it rather than most of them.

## Domain quick reference

- Four route properties, four different failures, four different fixes. Being
  hardware decoded, being segregated, being present in every needed mode
  and being fast enough are independent properties of a route; an
  architecture can hold three of them and still lose the command.
- Hardware decoding is the point of the whole clause. An essential
  command exists for the case where the processor that would normally
  decode it is the thing that has failed, so a route that runs through
  flight software answers a question nobody asked.
- Segregation is about shared items, not about the count of paths. Two
  routes through one decoder, one power rail or one connector are one
  route with extra cabling, and the shared item is what has to be named
  in the finding.
- Mode availability is where designs quietly fail. A route that is
  configured out of existence in survival mode is missing exactly when a
  high-priority command is most likely to be sent, and nominal-mode
  testing will never show it.
- Latency is specified per command, not per bus. A command that has to
  stop a thruster firing has a different bound from one that reconfigures
  a receiver, and comparing both against one architectural number hides
  the one that matters.
- The useful summary is per obligation, not per command. Knowing that
  three commands failed is not actionable; knowing that all three failed
  segregation on the same shared decoder points straight at the fix.

## Workflow

1. Start from the essential telecommands the preliminary design review
   agreed, carrying the encoding of each one and what
   each one does. Where no such list has been agreed, report that first:
   an audit against a list nobody has settled grades a moving target.
2. Validate each essential command as a route record: an identifier, how
   it is decoded, the items it shares with the nominal path, the modes it
   exists in, and its delivery and specified latencies.
3. Validate the set of mission configurations the command has to be
   available in before any command is graded, so a missing mode is a
   finding rather than an omission nobody noticed.
4. Check what the list can actually do: switch key system components'
   power on and off, and force a switch-over to the redundant
   system. A set that cannot do those two things is short of the clause
   however sound its routes are.
5. Apply the four route properties separately and keep the four results
   separate, with every other on-board system — the command and data
   management unit included — taken as non-operational. Under exactly
   that condition the route still has to decode the command and drive its
   control signal to the unit. A command is distributed only when all
   four hold.
6. For the commands used in critical operations — switching a transmitter
   on or off is the clause's own example — confirm that nothing in the
   execution path relies on a software function.
7. Compare latency with an explicit tolerance, so a route budgeted
   exactly on its bound is not graded differently on two hosts.
8. Name each failure with the detail that makes it actionable: the shared
   item, the absent modes, the two latencies.
9. Summarize the architecture twice — the fraction of essential commands
   that hold all four, and the commands that failed grouped by which
   property they failed.

## Obligations

| Item | Step |
|---|---|
| ECSS-E-ST-50C Rev.2 5.4.4a | 5 |
| ECSS-E-ST-50C Rev.2 5.4.4b | 1 |
| ECSS-E-ST-50C Rev.2 5.4.4c | 4 |
| ECSS-E-ST-50C Rev.2 5.4.4d | 6 |

## Pitfalls

- Counting a redundant software-decoded path as satisfying the clause.
  Duplicating a processor-dependent route does not remove the dependence
  on the processor; it multiplies it.
- Calling two routes segregated because they are physically separate
  cables. Segregation is broken by anything common — a decoder, a rail, a
  connector, a single command pulse driver — and the cable is rarely it.
- Testing essential command distribution only in nominal mode. The route
  is for the abnormal case, so the only meaningful test configuration is
  the abnormal one.
- Applying one architectural latency to every essential command. The
  bound belongs to the command's purpose, and the tightest one is the one
  that decides whether the architecture works.
- Reporting a pass count. An architecture where every failure is the same
  shared unit and one where four unrelated things went wrong have the
  same count and entirely different fixes.
- Treating an extra available mode as a defect. A route present in more
  configurations than required is fine; only an absent required mode is a
  finding.

## Behavior contract (gate 3)

The route record validation, required-mode validation, the four separate
route-property checks, the named missing modes, the tolerance-based latency
comparison, the per-command verdict and the architecture summary grouped by
property are exercised by the gate 3 contract test:
scripts/test_e50_essential_telecommand_distribution.py against
scripts/e50_essential_telecommand_distribution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_essential_telecommand_distribution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
