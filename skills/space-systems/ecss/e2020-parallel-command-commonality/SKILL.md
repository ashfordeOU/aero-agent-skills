---
name: e2020-parallel-command-commonality
description: "Verify that every latching current limiter in a parallel group takes its on command and its off command from one shared line, per clause 5.2.12.4.1 of ECSS-E-ST-20-20C. Use when a paralleled group has to switch as one device rather than as neighbours: resolve the on-command and off-command source each member is bound to, refuse a member left naming no source at all, grade the two lines apart so a shared turn-on with a split turn-off is caught, and measure the spread of arrival delays across the group against a skew budget. Trigger: ecss, e-st-20-20c-clause-5-2-12-4-1, paralleled-limiter-command-commonality, shared-on-off-command-line, limiter-group-command-skew, split-limiter-command-path, unbound-limiter-command-source."
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
  tags: [ecss, e-st-20-20-power-distribution-scope, e-st-20-20c-clause-5-2-12-4-1, e2020-parallel-command-commonality, paralleled-limiter-command-commonality, shared-on-off-command-line, limiter-group-command-skew, split-limiter-command-path, unbound-limiter-command-source]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Power Distribution -- Paralleled Limiter Command Commonality (space-systems/ecss/e2020-parallel-command-commonality)

Use when the task is clause 5.2.12.4.1 of ECSS-E-ST-20-20C: latching
current limiters placed in parallel are commanded on, and commanded off,
through one shared line each. Paralleling exists so the group behaves as
a single larger limiter, and that only survives while every member moves
on the same command, so this leaf grades the group one command line at a
time instead of one limiter at a time.

## Domain quick reference

- A parallel group has two command lines, not one, and they fail
  independently. A group can share its on command and split its off
  command; that asymmetry is the damaging one, because the group powers
  up together and then strands a member conducting after the others have
  opened.
- Commonality is decided on the source each member resolves to, not on
  how the schematic is drawn. Two members naming two different command
  sources are two limiters that happen to sit next to each other; the
  parallel connection on the output side does not make them one device.
- A member naming no source at all outranks a split. A split is an
  argument that was made and came out wrong; an unbound member is the
  part of the design where nobody said what commands it, and the two
  need different work.
- A shared line still reaches each member through its own driver, opto
  and harness. The spread between the earliest and the latest arrival is
  the skew, and during that window one member carries current the group
  was sized to share. The skew that matters is the spread, never the
  largest delay on its own -- a group uniformly late is still a group.
- Group width is bounded by what one line can drive. A group wider than
  the declared fan-out is not a marginal case to be graded; the shared
  line it assumes does not exist, so the input is refused.

## Workflow

1. Validate the policy: a parallel group needs at least two members, the
   line fan-out must be able to reach that many, and the skew budget must
   be a positive time.
2. Read each member into its two command sources and its propagation
   delay; refuse a member with no identifier, a duplicate identifier or a
   negative delay, and keep a missing source as unbound rather than
   silently defaulting it.
3. Refuse a set that is not a group: one limiter on its own, or more
   members than the shared line can drive.
4. For each of the two command lines, collect the distinct sources across
   the group and the members naming none, then read the line as shared,
   split or unbound.
5. Compute the skew as the spread between the earliest and the latest
   member, and compare it with the budget, absorbing floating-point
   representation error at the boundary with a named tolerance rather
   than by relaxing the budget.
6. Rank the group at its worst standing: an unbound member first, then a
   split line, then an excessive skew, then commonality held.
7. Report both line bindings, the skew and every finding, naming the
   members and the sources involved so the finding can be worked.

## Pitfalls

- Grading the on command and calling the group common. The off command
  is a separate line with its own drivers and its own routing, and it is
  the one that leaves a member conducting when it splits.
- Reading the parallel connection on the output as evidence of command
  commonality. The outputs being tied together is what makes the group
  need one command line, not what provides it.
- Treating a member with no declared command source as a member that
  passes. Nothing was argued about it, so it cannot have passed; it
  outranks the members that were argued about and found wrong.
- Reporting the largest propagation delay as the skew. A group whose
  members are all uniformly late still closes together; only the spread
  between them puts the group current into one member.
- Widening the skew budget to absorb an exact-equality case. An equality
  at the limit is a representation question, handled by the tolerance
  inside the comparison; the budget stays as specified.
- Grading a group wider than one line can drive as merely a large group.
  The shared line the clause asks for cannot exist at that width, so the
  answer is an input refusal, not a marginal pass.

## Behavior contract (gate 3)

The policy validation, the member and group normalization, the per-line
binding that separates shared from split from unbound, the skew built
from the spread of arrival delays, the boundary handling at the budget
and the worst-standing group verdict are exercised by the gate 3
contract test:
scripts/test_e2020_parallel_command_commonality.py against
scripts/e2020_parallel_command_commonality_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e2020_parallel_command_commonality.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
