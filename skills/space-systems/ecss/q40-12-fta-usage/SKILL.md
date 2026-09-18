---
name: q40-12-fta-usage
description: "Scope fault tree analysis inside an ECSS project under the ECSS-Q-ST-40-12C adoption of IEC 61025: categorize the need as top-down consequence reasoning or bottom-up failure-mode enumeration, decide whether a tree, an FMECA or both carry the work, name the analyses the tree feeds — hazard analysis under ECSS-Q-ST-40-02 or the dependability analyses of ECSS-Q-ST-30C — set the depth as qualitative or quantitative, and compute how far the basic events trace back to declared failure modes. Use when a project has to justify that a fault tree is the right technique, or to divide work between a tree and an FMECA. Trigger: ecss, q-st-40-12c, fta-usage-scoping, fta-versus-fmeca-division, iec-61025-adoption, fault-tree-basic-event-traceability, fta-analysis-depth-selection."
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
  tags: [ecss, q-st-40-12c-fault-tree-analysis, q-st-40-12c, q40-12-fta-usage, fta-usage-scoping, fta-versus-fmeca-division, iec-61025-adoption, fault-tree-basic-event-traceability, fta-analysis-depth-selection]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Fault Tree Analysis — Usage Scoping (space-systems/ecss/q40-12-fta-usage)

Use when the task is the scoping clause of ECSS-Q-ST-40-12C — the adoption of
the IEC 61025 method into an ECSS project — applied before any tree is drawn:
whether a fault tree is the technique the stated need actually asks for, which
receiving analysis the tree would feed, and where the boundary with the FMECA
runs.

## Domain quick reference

- ECSS-Q-ST-40-12C does not restate the method. It adopts IEC 61025 and says
  where that method applies inside an ECSS programme, so the scoping question
  is always two-part: is the adopted method applicable to this need at all,
  and which of its procedure elements does the need switch on.
- A tree reasons downwards from one undesired consequence to the combinations
  of lower events that produce it. An FMECA reasons upwards from every single
  failure mode of every item to its effect. Direction is the first
  discriminator, and a need stated in both directions owes both analyses.
- Four things pull work onto a tree regardless of direction: combinations of
  events have to be represented, a common cause is suspected, the consequence
  crosses more than one function, or software and human contributors are in
  play. None of those fit on an item worksheet.
- One thing pulls work onto an FMECA regardless of direction: a duty to
  enumerate every failure mode. A tree only ever carries the events someone
  chose to develop, so it is never the evidence that the enumeration is
  complete.
- A tree is built for a customer. A catastrophic or critical top event feeds
  the hazard analysis of ECSS-Q-ST-40-02 and the critical items list; a
  declared numeric target feeds the dependability analyses of ECSS-Q-ST-30C. A
  tree with no receiving analysis has no acceptance criterion either.
- Depth follows the customer, not preference. Cut sets alone are enough until
  a probability target is declared or the top event is catastrophic; then
  quantification, importance and sensitivity switch on as well.
- The two analyses meet at the basic events. Every basic event should resolve
  to a failure mode the item analysis already declared, and the fraction that
  does is a measurable property of the pair, not an opinion.

## Workflow

1. Write the top event as one consequence, and declare the direction the need
   is stated in, the severity category, and the four flags that pull work onto
   a tree. Reject an undeclared value rather than defaulting it.
2. Select the technique from those declarations and keep the rationale: the
   selection has to survive a review that asks why a tree was drawn at all.
3. Name the receiving analyses. If none is identified, stop and settle that
   first — the depth and the acceptance criterion both come from the customer.
4. Set the depth, then switch on the IEC 61025 procedure elements the depth
   and the common-cause declaration imply, and write down the ones deliberately
   left out.
5. Draw the boundary with the FMECA artefact by artefact, so neither analysis
   is asked for the other's product in review.
6. Where a basic event list and a failure mode list both exist, compute the
   traceability fraction, grade it against the project threshold, and name
   every event that does not resolve.

## Pitfalls

- Drawing a tree because the project plan lists one. The clause runs the other
  way: the need names a direction and a set of duties, and those select the
  technique. A tree built for a need that enumerates failure modes duplicates
  the worksheet and proves nothing extra.
- Treating a tree as evidence of completeness. It develops the events someone
  chose to develop, so an undeveloped branch is invisible in the result. Only
  the item analysis carries the enumeration duty.
- Quantifying because the tool offers a number. Below a declared target and
  below a catastrophic severity the cut sets are the product, and a
  probability quoted with no receiving analysis has no criterion to be graded
  against.
- Leaving software and human contributors out because they have no item
  worksheet. They enter as basic events, and a tree that silently drops them
  reports a top event probability for a different system.
- Letting basic events float free of the failure modes. An event that resolves
  to nothing in the item analysis carries no data basis, and a traceability
  fraction is a ratio of counts, so a set that is exactly complete can land a
  few units in the last place below one; the comparison absorbs that
  representation error while the threshold stays untouched.

## Behavior contract (gate 3)

The need validation, technique selection, receiving-analysis identification,
depth and procedure-element switching, FMECA division of labour and basic
event traceability are exercised by the gate 3 contract test:
scripts/test_q40_12_fta_usage.py against scripts/q40_12_fta_usage_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q40_12_fta_usage.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
