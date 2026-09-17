---
name: q60-class-3-destructive-physical-analysis
description: "Evaluate the sample teardown a delivered Class 3 EEE lot owes under ECSS-Q-ST-60C clause 6.3.9: partition the shipment into date-code groups, let a manufacturer teardown report for the same date code inside its validity reduce a group to a confirmation piece, compare every torn-down piece attribute by attribute against the declared construction baseline, revoke that delegation for the changed build week and every later one when the comparison finds a change, judge the measured fine leak against its limit, and categorize bench observations from the project register. Use when a Class 3 teardown record has to become an accept, second-sample, board-referral or reject decision. Trigger: ecss, q-st-60c-clause-6-3-9, class-3-date-code-teardown-sample, class-3-delegated-teardown-credit, class-3-construction-baseline-deviation, class-3-fine-leak-limit, class-3-teardown-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q60-class-3-destructive-physical-analysis, class-3-date-code-teardown-sample, class-3-delegated-teardown-credit, class-3-construction-baseline-deviation, class-3-fine-leak-limit, class-3-teardown-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Components — Class 3 Destructive Physical Analysis (space-systems/ecss/q60-class-3-destructive-physical-analysis)

Use when the task is the sample teardown of ECSS-Q-ST-60C clause 6.3.9 —
opening a few pieces per lot or date code to confirm that the construction
inside a Class 3 package is still the construction the part was procured on.

## Domain quick reference

- A shipment spanning several date codes is several populations. A build and a
  bond process drift between date codes, so one teardown evidences only the
  group it was drawn from, and a single sample across a mixed shipment quietly
  passes every group it never opened.
- Class 3 is the class where the **manufacturer's own** teardown report can
  stand in for the project's. It has to name the **same date code** — a
  neighbouring week is a different build — and still be inside its validity. A
  credited group gives up a confirmation piece rather than nothing, so the
  delegation is checked and not simply believed.
- Every torn-down piece is compared **attribute by attribute** against the
  declared construction baseline. An attribute the baseline never declared is
  refused: there is nothing to compare it with, and a bench call is not a
  baseline.
- A construction change is about the **line**, not the piece. It revokes the
  delegation credit for its own build week and for every later one in the
  shipment, because a report raised before the change cannot speak for parts
  built after it. That contagion rule is the whole reason the groups are held
  in build order.
- The seal is judged on its **measured leak rate against the project limit**,
  compared through a relative tolerance. A reading sitting on the limit is a
  representation question, not an engineering one, and the limit itself is
  never widened to absorb it.
- A **critical** observation or a leaking package ends the lot outright. A
  construction change goes to the parts control board, because accepting a
  changed build is a board decision and not a bench one. Only cosmetic counts
  buy a second sample, once.
- Teardown pieces are destroyed. A group whose spares cannot cover its sample is
  reported infeasible rather than under-sampled, so the shortfall surfaces at
  the plan and not at kitting.

## Workflow

1. Partition the shipment into date-code groups in build order, refusing a
   repeated serial or a piece without a date code.
2. Compare the observed construction against the baseline, and fix the build
   week from which any change takes effect.
3. Test each group for delegation credit: a manufacturer report naming the same
   date code and still inside its validity, not revoked by a construction
   change at or before that week.
4. Size each group's sample — a confirmation piece for a credited group, an
   exact rational share floored and capped for every other — and check it
   against the spares left after the committed pieces.
5. Categorize every bench observation from the project register, refusing a code
   the register never listed.
6. Judge the measured fine leak rate against the project limit through the
   relative tolerance.
7. Settle the disposition in precedence: reject on a critical observation or a
   leaking package, refer a construction change to the parts control board,
   reject on a major observation, offer one second sample where only cosmetic
   counts overran, otherwise accept.

## Pitfalls

- Drawing one sample across a mixed shipment. It evidences one date code and
  silently passes the rest.
- Crediting a manufacturer report from a neighbouring week. The week is the
  population; a report for another one is data about other parts.
- Treating a construction change as a finding against one piece. It is a
  statement about the line, and leaving the later date codes delegated keeps
  crediting reports that predate the change.
- Comparing only the attributes that look interesting. The baseline is the list,
  and an attribute left out of the comparison is an attribute nobody checked.
- Widening the leak limit to absorb a reading that sits on it. The
  representation question is already handled inside the comparison; the limit
  stays where the project put it.
- Offering a second sample after a second sample, or in place of a major
  finding. The allowance absorbs cosmetic variation once, and never substitutes
  for a finding that already ended the lot.

## Behavior contract (gate 3)

The date-code partition in build order, the delegated teardown credit and its
validity, the baseline comparison, the revocation of credit from the changed
build week onward, exact rational sample sizing against the spares, the
registered observation categories and the leak comparison at its limit are
exercised by the gate 3 contract test:
scripts/test_q60_class_3_destructive_physical_analysis.py against
scripts/q60_class_3_destructive_physical_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_3_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
