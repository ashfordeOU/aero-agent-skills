---
name: drd-allowables
description: "Use when prepare the material and mechanical-part allowables document required by ECSS-E-ST-32C Annex H (MMPA DRD): identify every structural material and fastener in scope, assign each an allowable basis (A-, B-, S-, or typical), retrieve governing allowable values from MMPDS or CMH-17 for composites, apply environmental and statistical knockdown factors, verify that all required mechanical properties are present for the applicable temperature range, and confirm full source traceability before the allowables package is released for structural analysis use. Trigger: ecss, e-st-32-structures-scope, drd-allowables, mmpsd, cmh17, material-allowables, mechanical-part-allowables, allowable-basis, knockdown-factors, structural-properties."
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
  tags: [ecss, e-st-32-structures-scope, drd-allowables, mmpsd, cmh17, material-allowables, mechanical-part-allowables, allowable-basis, knockdown-factors, structural-properties]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Material and Mechanical-Part Allowables DRD (space-systems/ecss/drd-allowables)

Use when the task is to prepare or verify the Material and Mechanical-Part
Allowables (MMPA) document as required by ECSS-E-ST-32C Annex H — identifying
all in-scope materials and fasteners, assigning each a statistically grounded
allowable basis, pulling values from approved reference sources, applying
environmental knockdown factors, and confirming the package is complete before
it feeds structural analysis.

## Domain quick reference

- ECSS-E-ST-32C Annex H defines the MMPA DRD: a controlled document that
  records the allowable mechanical properties for every material and fastener
  used in the structural design. The allowables package is consumed directly
  by stress analysts; its completeness and traceability are mandatory before
  any sizing analysis is released.
- Allowable basis defines the statistical confidence of a property value.
  Four basis levels are recognised: **A-basis** (99th-percentile lower bound
  at 95% confidence — used for single-load-path structure), **B-basis**
  (90th-percentile lower bound at 95% confidence — used for redundant
  load-path structure), **S-basis** (a published minimum, typically a
  specification limit), and **Typical** (mean value, acceptable only for
  non-critical stiffness estimates). Choosing a basis weaker than the
  criticality of the load path is a nonconformance.
- Primary approved reference sources are MMPDS (Metallic Materials Properties
  Development and Standardisation, successor to MIL-HDBK-5) for metallic
  allowables and CMH-17 (Composite Materials Handbook, successor to
  MIL-HDBK-17) for composite laminates. Programme-specific test data and
  manufacturer data are accepted only with a statistical derivation
  substantiation attached.
- Each material record is categorized into one of four families: **metallic**,
  **composite**, **adhesive**, or **fastener**. The required property set
  differs per family; a metallic entry without Ftu/Fty/Fcy/Fsu/E/density is
  incomplete regardless of source.
- Environmental knockdown factors (temperature, moisture for composites,
  radiation, etc.) are applied multiplicatively to the room-temperature
  reference value. A knockdown factor must be in the range (0, 1].

## Workflow

1. Scope the allowables package: list every structural material, adhesive, and
   fastener used in the design. Assign each a unique material identifier.
   Reject any entry whose material family is not one of the recognised
   categories (metallic, composite, adhesive, fastener) before proceeding.
2. For each entry, assign an allowable basis (A, B, S, or Typical) consistent
   with the load-path criticality from the structural design justification
   document. Flag any entry where the basis selected is weaker than the
   load-path criticality demands.
3. Retrieve the governing allowable values from an approved source (MMPDS,
   CMH-17, programme test data with statistical derivation, or manufacturer
   data with derivation). Record the source reference (document title, revision,
   table/figure number) in the traceability field of each entry.
4. Verify property completeness for each material family: metallic entries
   require Ftu, Fty, Fcy, Fsu, E, and density; composite entries require F1tu,
   F1cu, F2tu, F2cu, F12su, E11, E22, G12, and nu12; adhesive entries require
   shear strength, peel strength, and E; fastener entries require Fstu, Fsbru,
   and diameter. Flag missing properties before sign-off.
5. Check physical plausibility: for metallics, Fty must not exceed Ftu, Fsu
   must not exceed Ftu, and all strength and modulus values must be positive.
   For composites, nu12 must be in (−1, 1) and all strength and stiffness
   values must be positive. Flag any violation.
6. Apply environmental knockdown factors to each property for every relevant
   environmental condition (hot-wet, cold-dry, radiation-aged). Record the
   knockdown factor value, its source, and the condition it covers alongside
   the reduced allowable. A knockdown factor outside (0, 1] is an error.
7. Define the temperature range of applicability for each entry. Confirm that
   the analysis temperature envelope falls within this range; flag gaps.
8. Verify DRD section completeness: the MMPA document must contain scope,
   applicable documents, material identification, allowable basis, property
   tables, source traceability, environmental conditions, statistical derivation
   methodology, and limitations and applicability sections.
9. Aggregate findings per material entry and per DRD section. The allowables
   package is not ready for release until all findings lists are empty.

## Pitfalls

- Using a Typical-basis value in a single-load-path sizing analysis — Typical
  is a mean estimate and provides no statistical lower-bound protection; A-basis
  or B-basis is mandatory for primary structure.
- Pulling composite allowable values from MMPDS or metallic allowables from
  CMH-17 — the two handbooks are family-specific; cross-applying them produces
  undefined results.
- Omitting the environmental knockdown derivation for composite wet-hot
  properties — CMH-17 does not supply pre-reduced wet-hot values for all
  laminates; the programme must derive knockdowns from its own conditioning
  tests when handbook values are absent.
- Recording a source as "manufacturer data" without attaching a statistical
  derivation substantiation — this makes the entry untraceable to an approved
  basis and will be rejected at design review.
- Treating a temperature range as verified because the reference document
  covers a nominally similar range — the analysis temperature envelope must
  be explicitly compared against the tabulated range of the allowable entry,
  not against the general scope of the reference document.

## Behavior contract (gate 3)

The allowable-basis validation, material categorization, property-completeness
check, plausibility check, knockdown-factor application, and DRD-section
completeness logic are exercised by the gate 3 contract test:
scripts/test_drd_allowables.py against scripts/drd_allowables_logic.py
(stdlib unittest, offline). Run:
python3 scripts/test_drd_allowables.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
