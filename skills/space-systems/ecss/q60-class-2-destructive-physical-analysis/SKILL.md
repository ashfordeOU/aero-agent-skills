---
name: q60-class-2-destructive-physical-analysis
description: "Evaluate the teardown a delivered Class 2 EEE lot owes under ECSS-Q-ST-60C clause 5.3.9: partition the shipment into date-code groups, size the sample each group owes against the spare units left after the build demand, credit a group whose previous teardown still sits inside its validity window down to a confirmation sample, categorize construction observations against a project register, judge die-attach voiding as a fraction of die area and every bond pull as a margin on the diameter minimum, then close with one lot disposition. Use when a Class 2 teardown record has to become an accept, second-sample, board-referral or reject decision. Trigger: ecss, q-st-60c, class-2-date-code-teardown-sample, class-2-prior-teardown-credit-window, class-2-die-attach-void-fraction, class-2-bond-pull-margin, class-2-teardown-disposition."
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
  tags: [ecss, q-st-60c-eee-components-scope, q-st-60c, q60-class-2-destructive-physical-analysis, class-2-date-code-teardown-sample, class-2-prior-teardown-credit-window, class-2-die-attach-void-fraction, class-2-bond-pull-margin, class-2-teardown-disposition]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS EEE Class 2 — Destructive Physical Analysis (space-systems/ecss/q60-class-2-destructive-physical-analysis)

Use when the task is clause 5.3.9 of ECSS-Q-ST-60C: the sample teardown a
delivered Class 2 lot owes, per lot or per date code, to confirm that what is
inside the package is the construction the part was procured on before the
rest of the lot reaches a build.

## Domain quick reference

- A shipment spanning several date codes is several populations. Each group
  owes its own teardown, because an assembly line and its bond process drift
  between date codes and one sample evidences only the group it came from.
- Class 2 buys a credit Class 1 does not. A group whose construction was torn
  down recently enough is still evidenced by that record, so it owes a single
  confirmation unit rather than a full sample. The credit is a window on the
  age of the prior teardown, and a record past that window buys nothing.
- Teardown units are destroyed. The sample comes out of the spare units, so a
  group that cannot give its sample up and still meet the build demand is
  refused rather than quietly under-sampled and signed off.
- Observations are categorized from a project register, never called at the
  bench. Critical, major and minor are three different dispositions, and a
  code the register never carried cannot be counted as any of them.
- Die-attach voiding is an area fraction, not a photograph. The voided share
  of the die attach area is what the limit is written against, and a void
  recorded in square millimetres says nothing until it is divided by the die.
- A bond pull is carried out as a margin on the minimum its wire diameter
  owes. A bond that held at the minimum and one that held at twice it are
  both compliant and are not the same lot.

## Workflow

1. Partition the delivered units into date-code groups, refusing a repeated
   serial or a unit with no date code.
2. Credit each group whose previous teardown is inside the validity window
   down to a confirmation sample; size the rest proportionally, floored and
   capped, and test every sample against the spare units.
3. Categorize each teardown observation from the project register, refusing an
   unregistered code or a citation of a date code the shipment does not hold.
4. Divide the voided area by the die attach area and test the fraction against
   its limit, counting an exactly-on-limit case as inside by tolerance.
5. Read the minimum pull force off the wire diameter and carry the weakest
   pull out as a margin fraction alongside the mean.
6. Dispose of the lot: a critical finding, a bond under its minimum or voiding
   over its limit rejects it; a major finding buys one second sample where the
   project permits one; minor findings over the allowance reach the parts
   control board; anything less accepts the lot.

## Pitfalls

- Drawing one sample from a mixed shipment. It evidences one date code and
  silently passes every other group in the box.
- Crediting a prior teardown without checking its age. The credit is the point
  of the window, and a record old enough to predate a process change is
  evidence for a construction the lot no longer has.
- Sizing the sample against the whole group when part of it is committed. The
  teardown then eats flight units and the shortfall surfaces at kitting.
- Calling an observation at the bench because the register does not carry it.
  A register gap is a refusal and a register update, not a field judgement.
- Comparing a voided area against a fraction limit. Square millimetres and a
  share of the die are different quantities, and mixing them passes a small
  die that is half void.
- Reading the minor count before the critical one. A lot with a critical
  finding is finished, and reading the minors first invites a second sample to
  be argued for that the lot was never entitled to.

## Behavior contract (gate 3)

The date-code partition, credit window, sample sizing against spare units,
observation categorization, void fraction, bond pull margin and the lot
disposition are exercised by the gate 3 contract test:
scripts/test_q60_class_2_destructive_physical_analysis.py against
scripts/q60_class_2_destructive_physical_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_destructive_physical_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
