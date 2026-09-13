---
name: e2001-measurement-procedure-documentation
description: "Use when audit an emission-yield measurement-procedure document against ECSS-E-ST-20-01C clause 9.5.1: confirm the written procedure records every mandatory item -- normative-references, measurement-facility description, electron-gun beam parameters, sample-description carrying material identity, batch identifier, thickness and surface-finish, sample-preparation and grounding, the bias-and-collector measurement-method, data-reduction from measured currents, uncertainty-budget, run environmental-conditions and record identification -- categorize each declared entry as mandatory, optional or uncategorized, flag present-but-thin entries too sparse to be repeatable elsewhere, score procedure-completeness against the mandatory set, and refuse a sample-description missing material identity, batch identifier, thickness or surface-finish. Trigger: ecss, e-st-20-01c, emission-yield-measurement, measurement-procedure-documentation, procedure-completeness-audit, sample-description-record, uncertainty-budget-item."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-measurement-procedure-documentation, emission-yield-measurement, measurement-procedure-documentation, sample-description-record, procedure-completeness-audit, uncertainty-budget-item]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipaction — Emission-Yield Measurement-Procedure Documentation (space-systems/ecss/e2001-measurement-procedure-documentation)

Use when the task is the clause 9.5.1 audit of an ECSS-E-ST-20-01C
secondary-electron-emission yield measurement-procedure document --
deciding whether the written procedure carries the minimum set of
recorded items, from the normative-references at the front to the
sample-description that identifies exactly which specimen was placed in
the chamber.

## Domain quick reference

- Clause 9.5.1 fixes a floor on what the emission-yield
  measurement-procedure must state in writing. The floor exists so a
  second laboratory can repeat the run and land on the same yield
  curve; a procedure that omits an item is not merely untidy, the
  measurement it produced is unverifiable and cannot be cited as
  representative data.
- The mandatory set covers ten recorded items: normative-references
  (which standards and applicable documents govern the run),
  measurement-facility description (chamber, pumping arrangement,
  achievable base-pressure), electron-gun parameters (energy span,
  beam current, spot geometry, incidence angle), sample-description
  (material identity, batch identifier, thickness, surface-finish),
  sample-preparation (cleaning, handling, mounting, grounding path),
  measurement-method (bias scheme, collector arrangement, pulse
  duration), data-reduction (how the yield is derived from the
  measured currents), uncertainty-budget (contributions and how they
  combine), environmental-conditions during the run (temperature,
  pressure) and record-identification (operator, date, document
  reference).
- A handful of further items are recognized but optional -- a
  surface-analysis record, a beam-alignment record, a witness-specimen
  record. They are categorized separately so their absence never
  suppresses completeness, and an entry matching neither list is
  uncategorized: it is reported, it is not counted, and it never
  substitutes for a mandatory item.
- Presence alone is not the check. Each item carries a minimum depth,
  expressed here as a per-item word floor on the recorded text. An
  entry that is present but below its floor is flagged
  present-but-thin: the heading exists, the repeatable content does
  not.
- The sample-description is validated structurally rather than by
  depth: material identity and batch identifier must be non-empty
  strings, thickness must be a positive length, and surface-finish
  must be stated. A missing or non-positive field is rejected, because
  the emission yield of a metal is a property of the surface actually
  presented to the beam, not of the generic material name.

## Workflow

1. Normalize every declared procedure item key (case, spacing,
   underscores) and categorize it as mandatory, optional or
   uncategorized. Reject a key that is not a string or that normalizes
   to nothing.
2. For each present item, measure the recorded detail against that
   item's word floor and mark it sufficient or present-but-thin. An
   uncategorized key has no floor and is never depth-checked.
3. Validate the normative-reference list: every entry needs an
   identifier and an issue or date, and a repeated identifier is a
   finding rather than a duplicate to be silently collapsed.
4. Validate the sample-description structurally -- material identity,
   batch identifier, positive thickness, stated surface-finish --
   raising on any field that is absent, blank or non-positive.
5. Score procedure-completeness as the fraction of mandatory items
   both present and sufficient. Compare it against the required floor
   with a representation tolerance so an exactly-complete record is
   never rejected by floating-point residue.
6. Aggregate the findings: missing mandatory items, present-but-thin
   items, reference-list defects, sample-description defects and
   uncategorized entries. The procedure is compliant only when the
   first four lists are empty.

## Pitfalls

- Counting a heading as an item. A section titled uncertainty-budget
  with one sentence under it satisfies no one; the depth floor exists
  precisely to separate a populated item from a placeholder.
- Letting optional items inflate the score. A procedure carrying three
  optional records and eight of ten mandatory items is not eighty
  percent complete plus extra credit -- it is missing two mandatory
  items and therefore non-compliant.
- Treating an uncategorized entry as a mandatory item under a local
  name. Site vocabulary drifts; the fix is to map the local name onto
  the standard key before the audit, not to let an unrecognized key
  quietly discharge a mandatory obligation.
- Accepting a sample-description that names only the material. Two
  aluminium coupons from different batches with different
  surface-finish states yield materially different emission curves,
  so the batch identifier and finish are part of the identity, not
  metadata.
- Comparing the completeness fraction with a bare equality or a
  hand-widened threshold. The fraction is a ratio of small integers
  and can land a few units in the last place away from unity; absorb
  that in the comparison tolerance, never by lowering the floor.

## Behavior contract (gate 3)

The item categorization, depth assessment, reference-list validation,
sample-description validation and completeness scoring are exercised
by the gate 3 contract test:
`scripts/test_e2001_measurement_procedure_documentation.py` against
`scripts/e2001_measurement_procedure_documentation_logic.py`
(stdlib unittest, offline). Run:
python3 scripts/test_e2001_measurement_procedure_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
