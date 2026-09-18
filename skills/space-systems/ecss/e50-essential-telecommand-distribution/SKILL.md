---
name: e50-essential-telecommand-distribution
description: "Audit how essential telecommands reach the units they act on under ECSS-E-ST-50C clause 5.4.4, which carries four separate obligations and four separate ways to fail: the route is decoded in hardware rather than by flight software, it shares no failure point with the nominal command path, it exists in every mission configuration the command is needed in, and it delivers inside the latency it was specified against. Use when judging whether a high-priority command survives a dead processor or a safe mode. Trigger: ecss, e-st-50c-communications-scope, essential-telecommand-distribution, high-priority-command-route, hardware-decoded-command, command-path-segregation, safe-mode-command-availability, essential-command-latency."
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
  tags: [ecss, e-st-50c-communications-scope, e50-essential-telecommand-distribution, high-priority-command-route, hardware-decoded-command, command-path-segregation, safe-mode-command-availability, essential-command-latency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Essential Telecommand Distribution (space-systems/ecss/e50-essential-telecommand-distribution)

Use when the task is ECSS-E-ST-50C clause 5.4.4 — the four obligations on how
an essential telecommand is distributed to its destination — and the question
is whether a given high-priority command route actually meets all four rather
than most of them.

## Domain quick reference

- Four obligations, four different failures, four different fixes. Being
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

1. Validate each essential command as a route record: an identifier, how
   it is decoded, the items it shares with the nominal path, the modes it
   exists in, and its delivery and specified latencies.
2. Validate the set of mission configurations the command has to be
   available in before any command is graded, so a missing mode is a
   finding rather than an omission nobody noticed.
3. Apply the four obligations separately and keep the four results
   separate. A command is distributed only when all four hold.
4. Compare latency with an explicit tolerance, so a route budgeted
   exactly on its bound is not graded differently on two hosts.
5. Name each failure with the detail that makes it actionable: the shared
   item, the absent modes, the two latencies.
6. Summarize the architecture twice — the fraction of essential commands
   that hold all four, and the commands that failed grouped by which
   obligation they failed.

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
obligation checks, the named missing modes, the tolerance-based latency
comparison, the per-command verdict and the architecture summary grouped by
obligation are exercised by the gate 3 contract test:
scripts/test_e50_essential_telecommand_distribution.py against
scripts/e50_essential_telecommand_distribution_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_essential_telecommand_distribution.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
