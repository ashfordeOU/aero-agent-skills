---
name: q6005-approved-line-acceptance-schemes
description: "Determine which acceptance testing options a hybrid maker running an approved production line may operate under ECSS-Q-ST-60-05C clause 12.2: check the approved-line entry condition that gates the whole clause, test the per-lot option and the monitored-line option against their own conditions independently, count the technical review board quorum and the roles it holds, compute the annual sampling burden the per-lot option carries, and recommend one option with its reason and every gap named. Use when choosing or auditing a hybrid acceptance route. Trigger: ecss, q-st-60-05c, approved-hybrid-line-acceptance, hybrid-acceptance-scheme-choice, hybrid-technical-review-board-quorum, hybrid-line-process-monitoring, hybrid-annual-sample-burden."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-approved-line-acceptance-schemes, approved-hybrid-line-acceptance, hybrid-acceptance-scheme-choice, hybrid-technical-review-board-quorum, hybrid-line-process-monitoring, hybrid-annual-sample-burden]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Approved-Line Acceptance Schemes (space-systems/ecss/q6005-approved-line-acceptance-schemes)

Use when the task is deciding which acceptance testing route a hybrid
manufacturer with an approved production line may take under
ECSS-Q-ST-60-05C clause 12.2 — which options are open to that supplier,
what each one demands before it opens, and which of them the line should
actually operate.

## Domain quick reference

- The approved line is the entry condition for the entire clause, not a
  preference. A maker without it does not pick a weaker option here; it
  leaves this clause altogether for the project-validated route, which
  is a different set of obligations.
- The two options are alternatives, not stages. One tests a sample out
  of every production batch. The other lets a statistically monitored
  line and a technical review board stand in for that sampling. A
  supplier does not work up from the first to the second by doing the
  first for long enough — the second has its own entry conditions.
- The monitoring option's conditions are all about whether the evidence
  exists to replace the sample: a run of consecutive monitored lots long
  enough for a chart to mean something, a capability index at or above
  the floor, a quorate board, and a written criterion for dropping back.
  Without the last one there is no defined way to notice the substitute
  has stopped working.
- Board composition is not the same condition as board quorum. A board
  can hold enough members to decide and still be missing the customer's
  product assurance voice, which is the member the substitution is being
  made in front of. Both are checked.
- The per-lot option's conditions are physical: a batch that yields
  enough units to draw the sample from, a sample size actually set, and
  somewhere to run the tests. A line can meet every monitoring condition
  and still fail these.
- Where both are open the choice is economic and statistical at once. A
  line in continuous production accumulates the history that makes a
  chart trustworthy and carries a heavy annual sampling burden; an
  occasional line accumulates neither and should test each lot.

## Workflow

1. Validate the supplier profile, letting absent evidence normalise to
   its empty value: a supplier with no board recorded has no board, and
   that is a gap to report rather than an input error.
2. Apply the approved-line entry condition first, and require a citable
   approval reference with it — an approval nobody can point at cannot
   be relied on at a review.
3. Evaluate each option against its own conditions independently, and
   keep both gap lists. A supplier two conditions short of monitoring
   needs to know which two, even after the per-lot option is chosen.
4. For the monitoring option, count the required roles the board holds,
   test the quorum, and test separately for the customer product
   assurance member.
5. Compare the capability index against the floor with a tolerance, so a
   line landing exactly on it is not refused by rounding.
6. Compute the annual sampling burden as the per-lot sample times the
   lot rate, and use it with the lot rate to recommend between two open
   options.
7. Return the open options, the per-option gaps, the board finding, the
   burden, the recommendation and its reason.

## Pitfalls

- Reading the monitoring option as a reward for a clean per-lot record.
  It is a different scheme with different entry conditions, and a long
  run of accepted lots satisfies none of them on its own.
- Checking quorum and calling the board compliant. Quorum is a count;
  the customer product assurance member is a named role, and a board
  that is quorate without it is deciding in front of nobody.
- Dropping the reversion criterion because the line is stable today.
  The criterion is what turns a future instability into a defined
  return to per-lot testing instead of an argument.
- Refusing a line whose capability index prints as the floor. Indices
  are quotients of measured spreads and land on the bound exactly in
  worked cases; compare with a tolerance or reject good lines by
  rounding.
- Assuming an approved line automatically has the per-lot option. It
  fails if the batch cannot yield the sample, and small-batch hybrid
  builds routinely cannot.
- Recommending monitoring for an occasional line because the arithmetic
  is cheaper. A chart over a handful of lots a year has no history
  between builds, and the saving is bought with evidence that is not
  there.

## Behavior contract (gate 3)

The profile validation, approved-line entry condition, per-option entry
conditions, board role and quorum check, annual sample burden and the
recommendation are exercised by the gate 3 contract test:
scripts/test_q6005_approved_line_acceptance_schemes.py against
scripts/q6005_approved_line_acceptance_schemes_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q6005_approved_line_acceptance_schemes.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
