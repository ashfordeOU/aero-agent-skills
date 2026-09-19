---
name: q2010-process
description: "Scope the off-the-shelf item utilisation process of ECSS-Q-ST-20-10C clause 4 against the project product tree: decide the stage each candidate has actually reached across market investigation, characterization and selection, and procurement and qualification, refusing to count a later stage while an earlier one is still open, add the delta qualification plan an item not already qualified for this application owes, and reconcile candidates with the tree so a candidate on a make node, a candidate on a node the tree lacks, and an off-the-shelf node with no candidate all surface. Use when an item reuse strategy is being scoped or audited. Trigger: ecss, q-st-20-10c, ots-item-selection-process, ots-market-investigation, ots-characterization-and-selection, ots-delta-qualification-plan, ots-product-tree-integration."
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
  tags: [ecss, q-st-20-10-ots-item-scope, q2010-process, ots-item-selection-process, ots-market-investigation-stage, ots-characterization-and-selection, ots-delta-qualification-plan, ots-product-tree-integration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Off-The-Shelf Items -- Selection Process (space-systems/ecss/q2010-process)

Use when the task is scoping the off-the-shelf utilisation process of
ECSS-Q-ST-20-10C clause 4: candidates are being considered for nodes of a
product tree and the question is how far each one has really got and
whether the candidate set and the make-or-buy decisions agree.

## Domain quick reference

- The process is three stages and they are ordered: investigate the
  market, characterize and select, then procure and qualify. Evidence
  belonging to a later stage does not promote a candidate whose earlier
  stage is still open, because the later work was done against an
  unsettled requirement baseline and may have to be redone.
- Out-of-sequence evidence is worth reporting rather than discarding. A
  procurement specification written before the trade-off is a real
  document and usually a real schedule pressure; it is raised as an
  advisory so the reader sees the order the work actually happened in.
- The last stage carries a conditional artefact. An item already
  qualified for this application is complete on its procurement
  specification and qualification statement; an item qualified only for
  some other application, or not qualified at all, also owes a delta
  qualification plan, and that is the difference between reuse and hope.
- The process only means something against the product tree. A candidate
  attached to a node the project decided to make is a contradiction, and
  a node decided as an off-the-shelf buy with nothing against it is the
  gap that gets discovered at procurement.
- A custom buy with an off-the-shelf candidate is not wrong. It is often
  a fallback under evaluation, so it is advisory and stays visible
  instead of blocking a process that is working as intended.

## Workflow

1. Normalise the product tree, refusing a node listed twice and a
   make-or-buy decision outside the recognised set.
2. Normalise the candidates: node, qualification state, and the evidence
   artefacts held. Refuse a candidate listed twice, an unrecognised
   qualification state and an artefact outside the known set.
3. Compute the artefacts each stage owes this candidate, adding the delta
   qualification plan when the state calls for it.
4. Walk the stages in order and stop at the first incomplete one; that is
   the stage the candidate has reached.
5. Report evidence completed for a stage beyond an open one.
6. Reconcile candidates and tree in both directions.
7. Return the per-candidate stage, the maturity across the candidate set
   and the decision: complete, incomplete, or not integrated.

## Pitfalls

- Counting artefacts instead of stages. A candidate holding nine of
  eleven artefacts can still be at stage one if the two it is missing
  are both in the market investigation.
- Letting a qualification claim close the last stage on its own.
  Qualified for another application is a different statement from
  qualified for this one, and the delta plan is what bridges them.
- Reading an empty candidate set as nothing to do. A product tree with
  off-the-shelf buy decisions and no candidates is the least mature
  state the process has, not a clean one.
- Treating a dangling node reference as a typo to be quietly matched. It
  means the product tree and the candidate list are maintained apart,
  which is the failure the clause exists to prevent.
- Blocking on a custom buy that carries a candidate. Evaluating an
  off-the-shelf fallback against a custom procurement is ordinary
  engineering, and blocking it trains people to leave it off the list.

## Behavior contract (gate 3)

The product tree and candidate normalisation, the conditional delta
qualification artefact, the ordered stage-reached rule, the
out-of-sequence evidence report, the two-way product tree reconciliation
and the maturity fraction driving the decision are exercised by the gate
3 contract test: scripts/test_q2010_process.py against
scripts/q2010_process_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_q2010_process.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
