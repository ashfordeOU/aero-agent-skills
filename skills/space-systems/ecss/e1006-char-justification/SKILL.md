---
name: e1006-char-justification
description: "Use when verify that every system requirement in the requirements
  database carries a recorded justification explaining why the requirement exists,
  per ECSS-E-ST-10C §8.2.2. For each requirement, determine whether the
  justification field is populated and whether the justification cites a traceable
  source — such as a stakeholder need, mission objective, standard clause, derived
  rationale, or safety argument. Flag any requirement whose justification text is
  absent or empty, and any requirement whose justification source reference is not
  recorded or belongs to an unrecognised source category. Produce a per-requirement
  verdict and a summary count of non-compliant items across the set.
  Trigger: ecss, e-st-10-system-scope, requirement-justification, rationale,
  char-justification, traceability, requirements-management, §8.2.2."
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
  tags: [ecss, e-st-10-system-scope, requirement-justification, rationale, char-justification, traceability, requirements-management]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirement Characteristic — Justification (space-systems/ecss/e1006-char-justification)

Use when the task is verifying that each system requirement carries a recorded
justification (rationale) per ECSS-E-ST-10C §8.2.2: confirm the justification
field is populated, confirm it references a traceable source, and flag any
requirement where either record is missing.

## Domain quick reference

- §8.2.2 of ECSS-E-ST-10C stipulates that each requirement shall have its
  rationale documented — stating the reason the requirement exists. The
  justification is not the requirement itself; it is the answer to "why does
  this requirement exist at all?"
- A valid justification must be traceable to one of the recognised source
  categories: a stakeholder need, a mission objective, a parent standard
  clause, a derived engineering rationale, a safety argument, an interface
  requirement, or an operational concept. A justification that exists but
  cites an unrecognised category is still a finding.
- A requirement may be technically correct and internally consistent yet still
  be non-compliant if no one has recorded the reason it was imposed. Both the
  justification text and its source reference must be on record.
- Duplicate requirement IDs in the assessment set are themselves a finding
  because they prevent unambiguous traceability of justification records.

## Workflow

1. Collect the full list of requirements to be assessed. Reject the assessment
   if the list is empty — an empty set produces no meaningful verdict.
2. For each requirement, check the requirement ID field first. An absent or
   whitespace-only ID is non-compliant immediately; record it with the
   placeholder `<missing-id>` and continue to the next requirement.
3. Check the justification text field. If it is absent or contains only
   whitespace, record a non-compliant finding for that requirement with the
   reason "justification field is absent or empty".
4. Check the justification source reference field. If it is absent or
   whitespace-only, record "justification source reference is absent or empty".
   If the field is populated but the source category does not match any
   recognised source kind (stakeholder_need, mission_objective, standard_clause,
   derived, safety_argument, interface_requirement, operational_concept), record
   the unrecognised category name in the finding.
5. If duplicate requirement IDs are encountered, record the second and
   subsequent occurrences as non-compliant with the reason "duplicate
   requirement id" and skip their detailed justification check — a duplicated
   ID makes the justification record ambiguous.
6. Aggregate per-requirement findings into a report. Count compliant and
   non-compliant items. The set is fully compliant only when no non-compliant
   findings remain.

## Pitfalls

- Treating a justification field that contains the requirement text itself as
  a valid justification — the rationale must explain *why*, not repeat *what*.
  The logic module checks presence and source traceability, not semantic
  adequacy; a separate review step is needed to catch self-referential entries.
- Accepting a populated justification_source field without checking that the
  source category is one of the recognised kinds — an ad-hoc or invented
  category does not satisfy the traceability requirement.
- Skipping the duplicate-ID check and allowing two requirements with the same
  ID to each carry a different justification — the traceability of which
  justification belongs to which instance becomes undefined.
- Reading "no non-compliant count" as "fully compliant" on an empty input —
  the assess function raises on empty input precisely to prevent a vacuous pass.

## Behavior contract (gate 3)

The requirement-ID check, justification-text check, source-reference check,
source-category check, duplicate-ID check, and set-level compliance logic are
exercised by the gate 3 contract test:
scripts/test_e1006_char_justification.py against
scripts/e1006_char_justification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_justification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
