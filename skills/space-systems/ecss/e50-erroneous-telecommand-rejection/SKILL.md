---
name: e50-erroneous-telecommand-rejection
description: "Verify that an on-board telecommand chain rejects an erroneous command instead of executing it, per ECSS-E-ST-50C clause 5.4.3: recompute the check symbol rather than trusting the one that arrived, walk integrity, declared length, destination application, service support and parameter range in an order where a broken packet can never be blamed on a later field, and return the first failing check with an execution plan that is empty and a rejection report owed to the ground. Use when deciding what an on-board acceptance chain does with a malformed uplink. Trigger: ecss, e-st-50c-communications-scope, erroneous-telecommand-rejection, telecommand-acceptance-check, telecommand-check-symbol, telecommand-parameter-range, partial-command-execution, telecommand-rejection-report."
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
  tags: [ecss, e-st-50c-communications-scope, e50-erroneous-telecommand-rejection, telecommand-acceptance-check, telecommand-check-symbol, telecommand-parameter-range, partial-command-execution, telecommand-rejection-report]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Communications — Erroneous Telecommand Rejection (space-systems/ecss/e50-erroneous-telecommand-rejection)

Use when the task is the single obligation of ECSS-E-ST-50C clause 5.4.3 —
that a telecommand found to be erroneous is rejected rather than executed —
and the question is what the on-board acceptance chain must actually do with
a command that does not survive its checks.

## Domain quick reference

- Rejection is a decision about the whole command, taken before anything
  happens. A command that has begun to execute cannot be rejected any
  more; it can only be partly done, which is the state the requirement
  exists to prevent.
- The checks have an order and the order is part of the contract. A
  packet that failed integrity has no trustworthy fields left, so
  reporting an unknown destination on such a packet blames a field that
  was probably never sent that way.
- The check symbol has to be recomputed from the octets that arrived.
  Comparing the symbol in the packet against itself, or against a value
  carried alongside it, tests nothing; only the recomputation over the
  received body can detect the corruption.
- Declared length and received length are two statements of one fact and
  they can disagree. That disagreement is a rejection reason in its own
  right, independent of whether the payload would have parsed.
- An unknown destination and an unsupported service are different
  findings. The first says no such application exists on board; the
  second says it exists and does not do this. A chain that merges them
  sends the ground looking in the wrong place.
- A rejection that the ground never sees is indistinguishable from a
  command that vanished on the link. The report is not an optional extra
  on top of the rejection; it is how the rejection becomes useful.

## Workflow

1. Validate the received octets as octets before anything else, so a
   decoding defect is not mistaken for a content error.
2. Split the trailing check symbol from the body, recompute the symbol
   over the body as received, and compare. Stop here if it disagrees.
3. Compare the declared body size with the octets that actually arrived,
   and stop if the packet is not self-consistent.
4. Resolve the destination application, then the service and subservice
   pair inside it, reporting the two separately.
5. Range-check every parameter against its declared bounds, treating a
   parameter with no declared range as an offender rather than as
   unconstrained, and name each offender.
6. Return the first failing check as the reason, an empty execution plan
   whenever the command was rejected, and the fact that a rejection
   report is owed.

## Pitfalls

- Validating the parameters first because that code was easiest to reach.
  On a corrupted packet the parameter values are noise, and the reason
  reported to the ground then points at a field the ground never wrote.
- Trusting the check symbol that arrived. It travelled over the same link
  as the body, and a chain that compares it with itself will accept a
  packet corrupted in transit.
- Beginning execution while the later checks still run. Even a single
  side effect makes the outcome a partial execution, which is worse than
  either accepting or rejecting the whole command.
- Treating a parameter with no declared range as acceptable. Silence in
  the database is not permission, and an out-of-range value in an
  undeclared field is exactly the case nobody tested.
- Reporting an unsupported service as an unknown destination. The two
  send an operator to different places, and merging them costs a pass
  while somebody looks for a unit that was there all along.
- Rejecting quietly. Without a report the ground sees only that nothing
  happened, and will retransmit the same erroneous command.

## Behavior contract (gate 3)

The octet validation, check symbol computation and splitting, integrity,
length, destination, service and parameter-range checks, the ordered
first-failure chain and the accept-or-reject assessment with its empty
execution plan are exercised by the gate 3 contract test:
scripts/test_e50_erroneous_telecommand_rejection.py against
scripts/e50_erroneous_telecommand_rejection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e50_erroneous_telecommand_rejection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
