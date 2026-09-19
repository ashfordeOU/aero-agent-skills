---
name: q6005-hybrid-delivery-general-requirements
description: "Verify the delivery package that accompanies a shipped batch of hybrids under ECSS-Q-ST-60-05C clause 13.1: validate the batch and its data pack, assemble the documents this delivery owes with the additions a raised nonconformance, an enhanced reliability level and a hermetic package bring, measure data pack coverage at the unit rather than the batch, name records held for units that never shipped, check the electrostatic and moisture packaging provisions, and return release or hold with each finding kept apart. Use when releasing or auditing a hybrid shipment. Trigger: ecss, q-st-60-05c, hybrid-delivery-data-package, hybrid-serial-number-coverage, hybrid-certificate-of-conformity, hybrid-shipment-packaging-provisions, hybrid-orphan-data-record."
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
  tags: [ecss, q-st-60-05-hybrid-procurement, q6005-hybrid-delivery-general-requirements, hybrid-delivery-data-package, hybrid-serial-number-coverage, hybrid-shipment-packaging-provisions, hybrid-orphan-data-record, hybrid-certificate-of-conformity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Hybrids — Delivery General Requirements (space-systems/ecss/q6005-hybrid-delivery-general-requirements)

Use when the task is releasing or auditing a shipped batch of hybrids
under ECSS-Q-ST-60-05C clause 13.1 — what travels with the batch, how
the data pack lines up against the units in the box, and how the units
are packed for the journey.

## Domain quick reference

- The delivery package is a set of records about specific units, not a
  folder of types of document. A certificate of conformity naming the
  lot and a data pack naming serials are answering different questions,
  and only the second can be checked against what is in the box.
- What the batch owes is conditional on how it was built. The base set
  travels with everything; a nonconformance raised anywhere in the build
  adds its report, an enhanced reliability level adds the construction
  analysis, and a hermetic package adds its seal evidence. Reading the
  base set as the whole obligation lets exactly the interesting
  deliveries through thin.
- Coverage is a unit-level measurement. A thick data pack is not a
  complete one: the question is whether every shipped serial has a
  record, and a pack can be larger than the shipment and still miss one.
- A record for a unit that did not ship is its own finding, not a
  harmless surplus. Either the unit exists somewhere outside this
  delivery, or the pack was assembled against a different build — and
  both need answering before the batch is used.
- Packaging obligations depend on the package type. A non-hermetic
  hybrid carries a moisture obligation — desiccant and an indicator —
  that a sealed one does not, and electrostatic protection is owed by
  everything regardless.
- Findings are corrected by different people. A missing certificate is
  the supplier's quality function, an uncovered serial is the test data
  owner, and a packaging gap is the shipping bench; a single
  "incomplete" verdict sends the whole list to whoever opened the box.

## Workflow

1. Validate the delivery: shipped serials with no repeats, the serials
   the data pack holds records for, the documents in the pack, the
   packaging provisions, and the build attributes that change what is
   owed.
2. Let an absent document list normalise to an empty pack rather than
   raising — a batch shipped with no paperwork is a real delivery to be
   graded.
3. Assemble the owed documents from the base set plus the conditional
   additions, and compare against the pack with case and separator
   insensitive matching.
4. Compute serial coverage as covered units over shipped units, and
   absorb representation error at the complete-pack bound rather than
   testing a strict inequality.
5. List the shipped serials with no record and, separately, the records
   for serials that did not ship.
6. Check electrostatic protection on every delivery, unit separation on
   a multi-unit shipment, and the moisture provision on a non-hermetic
   one.
7. Return release only when nothing is outstanding, and keep the missing
   documents, uncovered serials, orphan records and packaging gaps as
   separate lists in the report.

## Pitfalls

- Checking the document types and calling the pack complete. The types
  can all be present while the data inside covers three of the four
  units in the box.
- Reading a data pack larger than the shipment as thorough. Extra
  records mean the pack and the box disagree about what was built, which
  is a traceability question, not a bonus.
- Treating the base document set as the whole obligation. The additions
  are triggered by exactly the conditions that make a delivery worth
  scrutinising — a nonconformance, an enhanced build, a sealed package.
- Shipping non-hermetic units on the hermetic packing standard. The
  moisture provision is the difference, and it is invisible until the
  units are opened much later.
- Dropping unit separation because the units are individually bagged in
  one tray. Separation is about what can touch what in transit, and a
  shared tray is one shock away from being one item.
- Collapsing every finding into a single incomplete verdict. The lists
  are separate because the corrections are owned by different functions
  and take different amounts of time.

## Behavior contract (gate 3)

The delivery validation, the conditional document assembly, the
unit-level serial coverage, the orphan-record finding, the packaging
provisions and the release/hold disposition are exercised by the gate 3
contract test: scripts/test_q6005_hybrid_delivery_general_requirements.py
against scripts/q6005_hybrid_delivery_general_requirements_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_q6005_hybrid_delivery_general_requirements.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
