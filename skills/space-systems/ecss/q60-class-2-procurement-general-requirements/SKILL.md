---
name: q60-class-2-procurement-general-requirements
description: "Evaluate whether the Class 2 EEE parts actually purchased meet the technical baseline agreed for the project. Use when an order is placed or its procurement file is reviewed: match every ordered part type to a baseline entry in both directions, compare the offered procurement grade against the grade the baseline demands, confirm the part temperature range contains the mission range with the margin required at each end, admit a broker route only against traceability and counterfeit-avoidance evidence, accept a departure only against a deviation still valid on the order date, and report the compliant fraction. Trigger: ecss, ecss-q-st-60c-clause-5-3-1, class-2-procurement-general-requirements, class-2-technical-baseline-conformance, class-2-procurement-grade-ladder, class-2-supply-route-traceability, class-2-parts-temperature-margin, class-2-procurement-deviation-validity."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-2-procurement-general-requirements, ecss-q-st-60c-clause-5-3-1, class-2-procurement-general-requirements, class-2-technical-baseline-conformance, class-2-procurement-grade-ladder, class-2-supply-route-traceability, class-2-parts-temperature-margin, class-2-procurement-deviation-validity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts — Procurement General Requirements (space-systems/ecss/q60-class-2-procurement-general-requirements)

Use when the task is the general procurement duty of ECSS-Q-ST-60C clause
5.3.1 — the obligation to ensure that the Class 2 parts a project actually
buys meet the technical baseline that was agreed for them.

## Domain quick reference

- The baseline is the contract, not the catalogue. A part type bought with no
  baseline entry was bought against nobody's requirement, and the first place
  that surfaces is the board it fails on.
- Two entries for one part type is worse than none. Whichever one the buyer
  read, the other is the requirement that went unmet, so a baseline carrying
  a repeated part type is refused before any line is judged.
- Procurement grade is a ladder, not a label. A part offered above the grade
  demanded satisfies the demand; a part offered below it never does, however
  close the two names sound.
- Temperature is judged at both ends independently. A part with generous cold
  margin and none at the hot end passes any single-number check and fails the
  mission, so the cold and hot margins are computed and compared separately.
- A margin that lands exactly on its requirement is met. Limits are decimal
  values parsed from a file and differenced in binary, so the comparison
  carries a representation-sized tolerance and the verdict does not change
  between machines.
- The route carries the traceability or the paperwork does. The manufacturer
  and its franchised distributors bring their own chain; a broker or open
  market route is admitted only where a traceability chain and a
  counterfeit-avoidance test report travel with the lot.
- A deviation has a date. A reference and an approving authority without a
  validity that still covers the order date records that somebody once agreed
  to something, not that this order was covered.
- Reconciliation runs both ways. An ordered type outside the baseline is the
  obvious gap; a baseline type nobody ordered is the one found at integration.

## Workflow

1. Index the agreed baseline by part type, rejecting a repeated type and a
   mission range that does not rise.
2. Match each purchased line to its baseline entry, reporting an ordered type
   that has no entry.
3. Compare the offered procurement grade with the demanded grade on the
   ladder.
4. Compute the cold and hot margins the offered part holds over the mission
   range and compare each with the required margin, within a
   representation-sized tolerance.
5. Judge the supply route, requiring the full evidence set from an
   evidence-bearing route.
6. Where a line departs from the baseline, require a deviation carrying a
   reference, an approval authority and a validity covering the order date.
7. Reconcile ordered types against baseline entries in both directions.
8. Report the per-type records, the compliant fraction and a verdict carrying
   every finding.

## Pitfalls

- Treating the manufacturer datasheet grade as the baseline. The datasheet
  says what the part is; the baseline says what the project agreed to buy.
- Checking the temperature range as a single span. A range wide enough
  overall can still sit shifted, leaving the hot end uncovered.
- Failing a margin that landed on its requirement. The shortfall is in the
  last bit of a decimal parsed into binary, not in the part.
- Accepting a broker lot on a certificate of conformity alone. The
  certificate is the seller's own statement; the chain and the
  counterfeit-avoidance evidence are what make it checkable.
- Reading an approved deviation as permanent. Approval covered a window, and
  an order placed after it closed is uncovered.
- Reconciling one way only. The types on the order all match and the baseline
  entry nobody bought is still missing at board build.
- Stopping at the first finding. The procurement owner closes the file once,
  and needs the whole list to do it.

## Behavior contract (gate 3)

The baseline indexing and its duplicate refusal, the procurement-grade
ladder, the cold and hot margin arithmetic with its representation-sized
tolerance, the supply-route evidence set, the deviation validity window, the
two-way reconciliation, the compliant fraction and the overall verdict are
exercised by the gate 3 contract test:
scripts/test_q60_class_2_procurement_general_requirements.py against
scripts/q60_class_2_procurement_general_requirements_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_q60_class_2_procurement_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
