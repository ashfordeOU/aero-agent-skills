---
name: q60-class-2-precap-source-inspection
description: "Audit the witnessed pre-cap source inspection covering the Class 2 production lots of an order. Use when a lot is about to be sealed or its inspection record is reviewed: decide from the package whether a witness point exists at all, place that point ahead of the seal in the manufacturing flow, report a cavity-affecting operation running between the two, accept a delegated inspection agency only on a customer delegation reference, admit an unwitnessed lot only against an accepted in-line monitoring programme still valid on the lot date, and report the witnessed coverage per part type. Trigger: ecss, ecss-q-st-60c-clause-5-3-4, class-2-precap-source-inspection, class-2-precap-package-applicability, class-2-precap-witness-delegation, class-2-inline-monitoring-programme, class-2-precap-coverage-per-part-type."
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
  tags: [ecss, q-st-60c-eee-parts-scope, q60-class-2-precap-source-inspection, ecss-q-st-60c-clause-5-3-4, class-2-precap-source-inspection, class-2-precap-package-applicability, class-2-precap-witness-delegation, class-2-inline-monitoring-programme, class-2-precap-coverage-per-part-type]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Class 2 EEE Parts — Pre-cap Source Inspection (space-systems/ecss/q60-class-2-precap-source-inspection)

Use when the task is the pre-cap source inspection of ECSS-Q-ST-60C clause
5.3.4 — the inspection witnessed at the manufacturer's premises before the
package is sealed, applied across the Class 2 production lots an order
carries.

## Domain quick reference

- The package decides whether the question exists. A witness point only
  exists where a cavity is about to be closed; a moulded or encapsulated lot
  has no seal operation, so its record reads not applicable rather than
  counting as an inspection somebody skipped.
- A sealless lot must not be scored as an uncovered one. Mixing the two sinks
  the coverage figure and buries the cavity lots that really were missed.
- Being ahead of the seal is necessary and not sufficient. A wire bond, a die
  replacement or a lid rework between the witness and the seal puts something
  in the cavity that nobody saw, whatever the flow calls the step.
- Class 2 allows the witness to be delegated; it does not allow it to be
  returned to the manufacturer. An approved inspection agency may hold it on
  a customer delegation reference, and no delegation reference makes the
  manufacturer's own quality department independent.
- An unwitnessed lot is recoverable through an accepted in-line programme,
  not through a filed one. The approval reference, the customer's acceptance
  and a validity that still covers the lot date are three separate conditions.
- Coverage is owned by the part type, not by the order. An order with many
  witnessed lots of one type and none of another reads as well covered until
  the figure is computed per type.
- A coverage landing on its minimum has met it. The ratio is compared against
  a fraction written another way, so a representation-sized tolerance keeps
  the verdict the same on every machine.
- A witnessed lot with a finding is not a covered lot. It counts towards the
  coverage only once its own findings are empty.

## Workflow

1. Validate the order and its lots, rejecting a lot reported twice.
2. For each lot, decide from the package family whether a pre-cap witness
   point exists; record a sealless lot as not applicable.
3. For a witnessed cavity lot, locate the witness step and the seal step in
   the flow and confirm the witness comes first.
4. Report any cavity-affecting operation running between the witness and the
   seal.
5. Validate the witness role, requiring a customer delegation reference where
   an inspection agency holds it and rejecting a manufacturer role outright.
6. For an unwitnessed cavity lot, require an in-line monitoring programme
   carrying an approval reference, the customer's acceptance and a validity
   covering the lot date.
7. Group the cavity lots by part type, compute the witnessed coverage each
   type achieved and compare it with the minimum required, within a
   representation-sized tolerance.
8. Report the per-lot records, the per-part-type coverage, the witnessed
   fraction and a verdict carrying every finding.

## Pitfalls

- Demanding a pre-cap witness on a moulded part. There is no cavity and no
  seal, and the finding raised against it costs the attention the real gaps
  needed.
- Scoring sealless lots as uncovered. The coverage figure collapses, the
  report reads as a crisis, and the two cavity lots that were genuinely
  missed are lost in it.
- Reading the flow by date rather than by step order. The dates move; the
  step order is what makes the inspection possible at all.
- Accepting a lid rework after the witness signed. The signature covered the
  package as it stood, and the rework is exactly what nobody saw.
- Accepting an inspection agency on its own letterhead. The delegation comes
  from the customer, and without that reference the agency is a visitor.
- Treating an in-line monitoring programme as permanent. Acceptance covered a
  window, and a lot built after it closed is uncovered.
- Averaging coverage across the whole order. One heavily witnessed part type
  hides another with no witnessed lot at all.
- Counting a witnessed lot that carries a finding towards coverage. The
  witness attended; the coverage was not achieved.

## Behavior contract (gate 3)

The package applicability decision, the witness placement against the seal,
the cavity-affecting operations between the two, the witness role and its
delegation reference, the in-line monitoring programme conditions, the
per-part-type coverage arithmetic with its representation-sized tolerance,
the witnessed fraction and the overall verdict are exercised by the gate 3
contract test: scripts/test_q60_class_2_precap_source_inspection.py against
scripts/q60_class_2_precap_source_inspection_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q60_class_2_precap_source_inspection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
