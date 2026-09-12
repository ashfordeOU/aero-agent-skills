---
name: drd-fci-lists
description: "Use when build the Annex G fracture-critical item register for a structure assessed under ECSS-E-ST-32C: screen each structural item against fracture-criticality criteria, assign each item to the Primary Fracture Critical Item List (PFCIL), Fracture Critical Item List (FCIL), or Fracture Limited Life Item List (FLLIL), validate entry fields and numeric bounds, compute the fracture life margin of safety, and verify that both the PFCIL and FLLIL are proper subsets of the FCIL. Trigger: ecss, e-st-32-structures-scope, fracture-control, fci-lists, pfcil, fcil, fllil, fracture-criticality, drd."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, fci-lists, pfcil, fcil, fllil, fracture-criticality, drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — DRD Fracture-Critical Item Lists (space-systems/ecss/drd-fci-lists)

Use when the task is building or auditing the Annex G fracture-critical item
register required by ECSS-E-ST-32C -- screening structural items against
fracture-criticality criteria, assigning each item to the PFCIL, FCIL, or
FLLIL, and verifying the consistency of the three lists with one another.

## Domain quick reference

- ECSS-E-ST-32C Annex G establishes three fracture-critical registers.
  The **FCIL** (Fracture Critical Item List) covers every item whose
  fracture would degrade mission performance or cause loss; it is the
  superset. The **PFCIL** (Primary Fracture Critical Item List) is the
  subset whose single fracture causes immediate loss of life, vehicle, or
  mission. The **FLLIL** (Fracture Limited Life Item List) is the subset
  of FCIL items for which the required fracture life is met by analysis or
  test within a finite service interval rather than through a fracture-proof
  design; these carry a life limit and a retest interval. A structural item
  not meeting any fracture-criticality criterion is screened out and does
  not appear on any list.
- Because PFCIL and FLLIL are derived subsets of the FCIL, every item on
  the PFCIL must also appear on the FCIL, and every item on the FLLIL must
  also appear on the FCIL. A cross-reference gap is a register deficiency,
  not an acceptable shortcut.
- Each FCIL entry requires: item identifier, description, material,
  assumed initial flaw size, fracture toughness, applied stress, required
  service life in load cycles, computed fracture life, and disposition
  (fracture-proof, safe-life, leak-before-burst, or retirement). PFCIL
  entries additionally require the failure consequence category
  (loss_of_life, loss_of_vehicle, or loss_of_mission). FLLIL entries
  additionally require the life limit in cycles and the retest interval
  in cycles.
- The fracture life margin of safety is (computed_life / required_life) - 1;
  a negative margin means the item does not satisfy its service-life
  requirement and must be dispositioned before the register is closed.

## Workflow

1. Enumerate every structural item in scope and apply the fracture-criticality
   screening question: would a single through-crack or fracture of this item
   cause loss of life, loss of vehicle, loss of mission, or degrade
   mission performance? Items answering no to all consequent levels are
   screened out and recorded as non-fracture-critical; they do not enter
   any register.
2. For each fracture-critical item, determine its failure consequence level.
   If a single fracture causes immediate loss of life, vehicle, or mission,
   add the item to both the PFCIL and the FCIL. Otherwise add it to the
   FCIL only.
3. For each fracture-critical item, determine whether its required service
   life is met through a fracture-proof design margin or through a
   bounded analysis with a defined life limit. If the item carries a finite
   life limit and a retest interval, add it to the FLLIL as well as the FCIL.
4. Validate each FCIL entry: confirm all required fields are present, flaw
   size and fracture toughness are positive, stress and life values are
   positive, and disposition is one of the four accepted values. Compute the
   fracture life margin of safety for every entry; flag any entry with a
   negative margin.
5. Validate each PFCIL entry against the FCIL rules plus the additional
   check that failure_consequence is present and is one of the three accepted
   consequence categories.
6. Validate each FLLIL entry against the FCIL rules plus the additional
   checks that life_limit_cycles is not less than required_life_cycles
   and that retest_interval_cycles does not exceed life_limit_cycles.
7. Perform cross-reference checks: verify every PFCIL item ID appears in
   the FCIL, and every FLLIL item ID appears in the FCIL. Record any
   discrepancies as register deficiencies.
8. Aggregate findings from all validation and cross-reference checks; the
   register is not complete until all finding lists are empty.

## Pitfalls

- Treating the PFCIL as independent of the FCIL -- the PFCIL is a derived
  subset; an item cannot be on the PFCIL without appearing on the FCIL,
  and any gap between the two is a register deficiency, not an allowed
  simplification.
- Setting a life limit on an FLLIL item below the required service life --
  the life limit must meet or exceed the required_life_cycles; a limit
  shorter than the service requirement means the item was retired before
  the mission ended, which must be captured in the mission design, not
  papered over in the register.
- Leaving the fracture toughness or flaw assumption fields blank and
  treating the absence as conservative -- the mandatory fields exist
  precisely because the computed fracture life depends on them; an entry
  without these values cannot be verified and must not be counted as
  validated.
- Reading a zero or positive margin of safety as proof the design is
  mature -- a margin of exactly zero means the computed life equals the
  required life with no reserve; a margin below the project-level fracture
  control requirement (often MOS >= 0 after scatter factors) must still
  be flagged.

## Behavior contract (gate 3)

The item-categorization, entry-validation, margin-of-safety, and
cross-reference logic is exercised by the gate 3 contract test:
scripts/test_drd_fci_lists.py against scripts/drd_fci_lists_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drd_fci_lists.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Normative anchor: ECSS-E-ST-32C Annex G.
