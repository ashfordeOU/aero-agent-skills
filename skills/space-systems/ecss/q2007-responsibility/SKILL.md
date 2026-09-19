---
name: q2007-responsibility
description: "Allocate responsibility and authority for quality and safety items as ECSS-Q-ST-20-07 clause 5.3.3 asks, and say whether the matrix in place holds. Use when a test centre's duties, delegations or reporting lines are being set or audited: refuse a matrix never assigned, separate an item with nobody against it from an item carrying two holders, compare each holder's authority level with what the item's criticality demands, catch a delegation granting more authority than the delegator holds or coming from somebody holding none, and walk every reporting line to the centre head to find one that stops short or loops. Trigger: ecss, q-st-20-07-clause-5-3-3, test-centre-responsibility-assignment, test-centre-authority-level-demand, test-centre-authority-delegation, test-centre-quality-and-safety-reporting-line."
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
  tags: [ecss, q-st-20-07-test-centre-quality-and-safety-scope, q2007-responsibility, q-st-20-07-clause-5-3-3, test-centre-responsibility-assignment, test-centre-authority-level-demand, test-centre-authority-delegation, test-centre-quality-and-safety-reporting-line, test-centre-duty-ambiguity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Test-Centre Quality and Safety — Responsibility and Authority (space-systems/ecss/q2007-responsibility)

Use when the task is clause 5.3.3 of ECSS-Q-ST-20-07: the test centre
says who is responsible for each quality and safety item, with what
authority, under what delegation, and reporting to whom.

## Domain quick reference

- An item with nobody against it and an item with two holders are
  different defects. The first needs somebody appointed; the second
  needs one of two appointments withdrawn. A matrix counted by rows
  instead of grouped by item reports neither, because the row count
  looks healthy in both cases.
- Authority is an ordered scale and that order is the whole point. An
  item demanding a manager is not discharged by an operator however
  carefully the duty is worded, so the held level is compared against
  the level the item's criticality demands rather than against the job
  title.
- The demand itself is a centre policy and is validated before it is
  used. A demand placing a safety-critical item under a routine one is
  refused rather than applied, because it would licence exactly the
  arrangement the clause exists to prevent.
- Delegation cannot manufacture authority. A delegator passes down what
  they hold and no more, so a delegate carrying a level above their
  delegator is invalid even when both people exist and both levels are
  recognised. A delegation from somebody holding nothing at all is the
  same defect seen from the other end, and is reported as such rather
  than skipped.
- A reporting line has to terminate at the centre head. A holder
  reporting to somebody the matrix does not list breaks the line, and a
  loop never arrives; either way an escalation on a safety item has
  nowhere to go.
- The centre head is the one person who holds top authority by position
  rather than by assignment, which is what lets a delegation from the
  head be valid without the head appearing as a holder anywhere.

## Workflow

1. Validate the authority demand first: every recognised criticality
   covered, every level recognised, and a safety-critical item never
   demanding less than a routine one.
2. Validate the matrix: recognised criticalities and authority levels,
   nobody delegating to or reporting to themselves, no item registered
   twice, no person assigned to one item twice, and no assignment
   naming an item the matrix does not hold.
3. Group the assignments by item and take the unassigned items, then
   the items carrying more than one holder.
4. Compare each holder's authority with the level their item's
   criticality demands and name the shortfalls with both levels.
5. Resolve each delegator's own highest authority — treating the centre
   head as top by position — and name the delegations that exceed it or
   that come from somebody holding nothing.
6. Walk each holder's reporting line to the centre head, and name the
   lines that stop short, contradict themselves or loop.
7. Close on one verdict in order: matrix absent, items unassigned, duty
   ambiguous, authority insufficient, delegation invalid, reporting line
   broken, or responsibilities and authorities assigned.

## Pitfalls

- Counting assignment rows instead of grouping by item. Three rows
  across three items and three rows across two items give the same
  total, and only one of them is a complete matrix.
- Reading a job title as an authority level. The title is not the scale;
  a "safety manager" row carrying supervisor authority still fails a
  safety-critical item and only the declared level shows it.
- Accepting a delegation because both parties exist. Existence is not
  authority, and a delegation from somebody holding nothing is the
  easiest way to write an unlimited duty into a matrix.
- Checking only the first link of a reporting line. A holder reporting
  to a supervisor who reports to nobody is as broken as one reporting to
  nobody directly, and only the walk to the centre head finds it.
- Applying a raised authority demand without validating it. A demand
  that inverts the criticality order will pass every safety item it was
  written to catch.

## Behavior contract (gate 3)

The authority-demand validation, item and assignment validation, the
unassigned and ambiguous items, the assignment coverage, the authority
shortfalls against a demand, the delegation defects including a
delegator holding nothing, the reporting-line walk with its stop-short
and loop cases, and the ordered verdict are exercised by the gate 3
contract test: scripts/test_q2007_responsibility.py against
scripts/q2007_responsibility_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2007_responsibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
