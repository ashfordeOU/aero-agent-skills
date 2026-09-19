---
name: q6005-hybrid-lot-rejection
description: "Determine whether a hybrid microcircuit production lot has to be declared unacceptable after screening or lot acceptance results under ECSS-Q-ST-60-05C clause 10.4: order the recorded stage verdicts against the mandatory worked sequence, measure how much of the evidence chain actually ran, find the earliest failing stage, decide whether the rejection falls on the whole lot or one segregated sublot, and return accepted, rejected or indeterminate with the quarantine, failure-analysis and notification obligations that status carries. Use when a screening or acceptance failure has to become a formal lot decision. Trigger: ecss, q-st-60-05c, hybrid-lot-rejection-declaration, screening-stage-verdict-chain, lot-rejection-evidence-completeness, rejection-scope-whole-lot-or-sublot, lot-quarantine-obligations."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-hybrid-lot-rejection, hybrid-lot-rejection-declaration, screening-stage-verdict-chain, lot-rejection-evidence-completeness, rejection-scope-whole-lot-or-sublot, lot-quarantine-obligations]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Declaring a Lot Unacceptable (space-systems/ecss/q6005-hybrid-lot-rejection)

Use when the task is turning screening or lot acceptance results into a formal
statement that a hybrid microcircuit production lot is unacceptable under
ECSS-Q-ST-60-05C clause 10.4 — what evidence a rejection rests on, which stage
it is anchored to, how far it reaches, and what the declaration obliges
everyone to do next.

## Domain quick reference

- A lot rejection is a declaration, not an observation. The observation is a
  failure at one stage; the declaration is the statement that the batch as a
  whole is unacceptable, and it carries obligations — quarantine, failure
  analysis, customer notification — that the observation alone does not.
- The screening and lot acceptance stages are worked in a fixed order, and
  that order is load-bearing. The earliest failing stage is what the decision
  is anchored to, because everything downstream was performed on a population
  already known to contain the defect, and any re-screen restarts there.
- A stage that never ran is not a stage that passed. An absent verdict carries
  no information about the lot, so a batch with no recorded failure but an
  incomplete chain is indeterminate, not acceptable. Collapsing the middle
  status into acceptance releases a lot on evidence nobody gathered.
- Admissibility is separate from the verdict. A rejection whose chain has a
  hole *before* the failing stage cannot be reproduced: the defect might have
  been detectable earlier, and the population entering the failing stage is
  not the one the record describes. A hole after the failing stage is
  harmless, because the decision was already taken.
- Scope defaults to the whole lot. Narrowing it to one sublot needs three
  conditions at once — the failures confined to that sublot, the sublot
  physically segregated, and its traceability intact — because any one of them
  missing means the unaffected material cannot be told apart from the rest.
- The declaring authority is part of the record. An unattributed rejection
  cannot be challenged, reversed or escalated, and the disposition route that
  follows depends on who owns the decision.

## Workflow

1. Validate the recorded stage verdicts against the mandatory sequence,
   refusing an unknown stage, an unknown verdict, or a stage carrying two
   verdicts — two verdicts for one stage means the lot record is in doubt, not
   that one of them should be preferred.
2. Sort the records into worked order and list the mandatory stages with no
   run verdict, treating an absent record and a not-run verdict identically.
3. Measure evidence completeness as the fraction of the mandatory sequence
   that ran, absorbing representation error at the boundary with a named
   tolerance rather than by loosening the condition.
4. Find the earliest failing stage. If there is one, the status is rejected;
   otherwise an incomplete chain is indeterminate and a complete clean chain
   is accepted.
5. For a rejection, settle the scope from the three sublot conditions and test
   admissibility by looking for unrun stages earlier than the failing one.
6. Attach the obligations the status carries and return the declaration with
   the failing stage, the missing stages, the completeness, the scope, the
   declaring authority and every finding named.

## Pitfalls

- Reading an empty result field as a pass. The most common way a lot gets
  released is a stage nobody ran and nobody noticed; unknown is not zero, and
  the three-way status exists precisely so that case has somewhere to go.
- Anchoring the rejection to the last failure instead of the first. A late
  failure in a lot that already failed early describes a population that
  should not have reached that stage, and re-screening from the late stage
  repeats none of the work that matters.
- Declaring a sublot-scoped rejection on segregation alone. Segregated but
  untraceable material cannot be shown to be the unaffected part, so the
  narrowing is unsupported and the whole lot stands rejected.
- Treating admissibility as a formality to be fixed after the fact. The gap in
  the chain cannot be closed retrospectively — the units have moved on — so an
  inadmissible declaration is a finding about the process, not a typo.
- Dispositioning before notifying the customer. The notification is what makes
  the rejection visible to the party whose hardware it is, and a rework or
  scrap decision taken first removes their options.
- Recording the rejection without the declaring authority. An anonymous
  rejection has no owner, and the escalation route back to the manufacturer or
  forward to the customer depends on knowing who declared it.

## Behavior contract (gate 3)

The stage-verdict validation, evidence-chain measurement, earliest-failing-
stage rule, rejection scope, admissibility check and three-way status are
exercised by the gate 3 contract test:
scripts/test_q6005_hybrid_lot_rejection.py against
scripts/q6005_hybrid_lot_rejection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q6005_hybrid_lot_rejection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
