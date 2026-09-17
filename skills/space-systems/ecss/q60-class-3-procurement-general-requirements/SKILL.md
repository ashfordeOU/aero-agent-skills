---
name: q60-class-3-procurement-general-requirements
description: "Evaluate whether the Class 3 EEE parts a project actually buys meet the technical baseline agreed for them. Use when a Class 3 order is placed or its procurement file is reviewed: reconcile ordered part types against the baseline in both directions, rank the offered quality level against the minimum the baseline demands on a ladder that reaches down into commercial grades, confirm the rated temperature envelope contains the mission envelope and demand an uprating justification record wherever it does not, admit an open-market or broker route only against authenticity evidence, refuse a lot whose date code is older than the agreed limit, and report the conforming fraction. Trigger: ecss, ecss-q-st-60c-clause-6-3-1, class-3-procurement-general-requirements, class-3-technical-baseline-conformance, class-3-quality-level-ladder, class-3-temperature-uprating-justification, class-3-open-market-authenticity-evidence, class-3-lot-date-code-age."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-3-procurement-general-requirements, ecss-q-st-60c-clause-6-3-1, class-3-procurement-general-requirements, class-3-technical-baseline-conformance, class-3-quality-level-ladder, class-3-temperature-uprating-justification, class-3-open-market-authenticity-evidence, class-3-lot-date-code-age]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 3 EEE Parts — Procurement General Requirements (space-systems/ecss/q60-class-3-procurement-general-requirements)

Use when the task is the general procurement duty of ECSS-Q-ST-60C clause
6.3.1 — the obligation to ensure that the Class 3 parts a project actually
buys meet the technical baseline that was agreed for them.

## Domain quick reference

- The baseline and the order are reconciled in both directions. A part type
  bought against no baseline entry and a baseline entry nobody ever bought are
  different defects with different repairs, and a check that walks the order
  only will never see the second one.
- Quality level is a ladder, and the Class 3 ladder reaches down into
  commercial grades. That is the point of the category, so the question is
  never whether the rung is a commercial one but whether it sits at or above
  the rung the baseline demands for that part type.
- The rated temperature envelope has to contain the mission envelope at both
  ends. The two ends fail independently and both are named.
- Where the mission runs outside the rated envelope the part is being uprated,
  whether or not anybody used the word. Uprating is admissible only against a
  justification record naming a recognised method and the evidence behind it.
  Buying a commercial part and assuming it will hold is the defect this
  catches, and it is the commonest one at this assurance category.
- An envelope that matches the mission exactly still contains it. Zero margin
  is a thin design, not a nonconformance, and the edge case is absorbed with a
  named tolerance rather than by moving the bound.
- A manufacturer or franchised route carries its own traceability. An
  open-market or broker route carries none, so it is admitted only against the
  authenticity evidence set, item by item.
- A lot older than the agreed date-code limit is refused on age alone,
  whatever else about it conforms.
- The order-level verdict is not the part-level verdict. A conforming fraction
  says how much of the order stands; one departure still stops the order.

## Workflow

1. Index the agreed baseline by part type, refusing a library in which two
   entries claim the same type.
2. Confirm the order is declared at the assurance category this check covers.
3. For each purchased part type, find its baseline entry. No entry is a
   finding in its own right, not a reason to skip the part.
4. Rank the offered quality level against the baseline minimum on the ladder.
5. Compute the cold and hot margins of the rated envelope over the mission
   envelope and decide whether the envelope contains the mission.
6. Where it does not, require an uprating justification record, and validate
   the method it names against the recognised set.
7. Read the supply route; require the authenticity evidence set from an
   evidence-bearing route and name each absent item separately.
8. Compare the lot date-code age with the agreed limit.
9. Walk the baseline for entries nobody bought, then report the per-type
   records, the conforming fraction and one order-level verdict.

## Pitfalls

- Walking the order only. A baseline entry nobody bought is invisible to a
  one-directional check and is exactly how a part quietly leaves the design.
- Treating a commercial rung as a nonconformance by itself. The ladder reaches
  down here on purpose; only the comparison with the baseline minimum decides.
- Reading a part outside its rated envelope as a margin problem. It is an
  uprating, and it needs a record naming a method, not a note in the file.
- Accepting an uprating record that names no evidence. The record is the
  justification; without evidence behind it, it is an assertion.
- Failing an envelope that matches the mission exactly because the comparison
  was written as a strict inequality. Zero margin contains the mission.
- Reporting one temperature end. The cold end and the hot end fall short
  independently and each is a separate repair.
- Admitting a broker lot because some authenticity evidence arrived. The set
  is the admission criterion and each absent item is named.
- Keeping an over-age lot because its paperwork is otherwise complete.
- Reporting a conforming fraction as though it were the order verdict. One
  departing part type stops the order however high the fraction reads.

## Behavior contract (gate 3)

The two-directional baseline reconciliation, quality ladder comparison,
temperature margins and envelope containment, uprating record validation,
supply route authenticity evidence, date-code age limit, conforming fraction
and order-level verdict are exercised by the gate 3 contract test:
scripts/test_q60_class_3_procurement_general_requirements.py against
scripts/q60_class_3_procurement_general_requirements_logic.py (stdlib
unittest, offline).
Run: python3 scripts/test_q60_class_3_procurement_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
