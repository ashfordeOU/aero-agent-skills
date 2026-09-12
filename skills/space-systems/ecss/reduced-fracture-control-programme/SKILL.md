---
name: reduced-fracture-control-programme
description: "Use when determine whether a structural item qualifies for the reduced fracture control programme defined in ECSS-E-ST-32C and identify which standard requirements may be modified. Evaluate each candidate by consequence of failure (catastrophic items are excluded), operating stress ratio against the allowable threshold, mission type (crewed versus uncrewed), and material fracture toughness. For eligible items, identify which analysis steps—crack growth calculation, fracture mechanics assessment, and NDE inspection scope—may be simplified or waived, and list the minimum required actions that remain mandatory. Reject items that do not meet applicability criteria with an explicit reason before any programme modification is applied. Trigger: ecss, e-st-32c, fracture-control, reduced-programme, fracture-critical, stress-ratio, nde, fracture-toughness, structural-integrity."
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
  tags: [ecss, e-st-32c, fracture-control, reduced-programme, fracture-critical, stress-ratio, nde, fracture-toughness, structural-integrity]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Reduced Fracture Control Programme (space-systems/ecss/reduced-fracture-control-programme)

Use when the task is to determine whether a structural item qualifies for
the reduced fracture control programme under ECSS-E-ST-32C clause 11, and
to identify which requirements of the standard programme may be modified or
waived for eligible items.

## Domain quick reference

- ECSS-E-ST-32C clause 11 permits a reduced fracture control programme for
  structural items that do not carry fracture-critical designation, provided
  they satisfy applicability criteria related to consequence of failure,
  operating stress ratio, and mission type.
- An item is fracture-critical when its single failure would result in a
  catastrophic outcome (loss of mission, loss of crew, or loss of vehicle).
  Fracture-critical items are never eligible for the reduced programme;
  they remain subject to the full programme requirements.
- The operating stress ratio is the ratio of the maximum operating stress to
  the material yield stress. For uncrewed missions the reduced programme
  threshold is ≤ 0.50; for crewed missions the threshold is stricter
  at ≤ 0.40, reflecting the higher consequence of failure involving crew.
- Fracture toughness (K_IC) must exceed the minimum material threshold
  (default 30 MPa√m) for the reduced programme to apply; materials with
  inherently low toughness require the full fracture mechanics treatment.
- When an item is eligible, the following standard programme steps may be
  simplified: crack growth life calculation (waived), detailed fracture
  mechanics stress intensity analysis (waived), and NDE inspection coverage
  (reduced to visual and surface examination only at standard intervals).
  The mandatory actions that remain are: material toughness verification,
  operating stress ratio documentation, and a consequence-of-failure
  confirmation on record.

## Workflow

1. Obtain the item data: fracture category (fracture-critical or
   non-fracture-critical), consequence of failure severity (minor, major,
   critical, or catastrophic), operating stress ratio, mission type (crewed
   or uncrewed), and material fracture toughness K_IC.
   Reject any input with an unrecognized value in any field before
   proceeding; do not assume defaults for safety-relevant attributes.
2. Screen for automatic exclusion: if the fracture category is
   fracture-critical, or if the consequence of failure is catastrophic,
   the item is not eligible for the reduced programme — record the specific
   reason and stop the assessment for that item.
3. Apply the mission-type stress ratio threshold: for crewed missions the
   operating stress ratio must be ≤ 0.40; for uncrewed missions ≤ 0.50.
   If the ratio exceeds the threshold, the item is not eligible — record
   the reason (actual ratio vs. allowable) and stop.
4. Verify fracture toughness: if K_IC is below the minimum acceptable
   toughness (30 MPa√m by default), the item is not eligible — full
   fracture mechanics treatment is required.
5. For items passing all four screens, confirm eligibility and list the
   applicable modifications (crack growth calculation waived, fracture
   mechanics analysis waived, NDE reduced to visual/surface).
6. List the mandatory remaining actions regardless of reduced status:
   document the confirmed operating stress ratio, confirm material K_IC
   on record, and retain the consequence-of-failure justification in the
   fracture control plan.
7. Aggregate results across all items; an item is only considered covered
   by the reduced programme when eligibility is confirmed and all mandatory
   remaining actions are completed.

## Pitfalls

- Applying the reduced programme to an item whose consequence of failure was
  recorded as catastrophic in an earlier review but not re-evaluated — the
  consequence determination must be current and on record at the time of the
  programme assessment.
- Using the uncrewed stress ratio threshold (0.50) for a crewed mission —
  the tighter threshold (0.40) exists because crew safety requires a larger
  margin against unexpected crack propagation.
- Treating a waived crack growth calculation as evidence that no crack can
  grow — the waiver applies because the operating stress is low enough that
  crack propagation to a critical size is not expected within service life,
  not because the item is inherently immune.
- Omitting the mandatory remaining actions on the assumption that "reduced"
  means the programme is optional — the mandatory documentation (stress
  ratio, K_IC, consequence justification) is required even under the reduced
  programme; missing it leaves the item uncovered.
- Confusing non-fracture-critical categorization with safe-life
  demonstration — categorization is a consequence-of-failure screening step,
  not a fatigue or damage tolerance analysis.

## Behavior contract (gate 3)

The eligibility screening, stress ratio threshold, fracture toughness check,
and modification-list logic are exercised by the gate 3 contract test:
scripts/test_reduced_fracture_control_programme.py against
scripts/reduced_fracture_control_programme_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_reduced_fracture_control_programme.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
