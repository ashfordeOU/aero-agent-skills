---
name: q2010-equipment-spec
description: "Define the equipment specification an off-the-shelf candidate has to be matched against under ECSS-Q-ST-20-10C clause 5.1.2. Use when a shortlisted unit must be held against the functional, performance and interface requirements of the application before any evaluation effort is spent on it. Builds the requirement set, refuses a specification that populates no interface requirement, grades each candidate datum as met, not met or undeclared, keeps an undeclared datum out of the compliance ratio instead of scoring it zero, and blocks acceptance on an unmet mandatory requirement while carrying a desirable shortfall as a gap. Trigger: ecss, q-st-20-10, ots-equipment-specification, ots-candidate-matching, functional-performance-interface-requirements, undeclared-characteristic-handling, mandatory-requirement-shortfall, ots-candidate-gap-list."
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
  tags: [ecss, q-st-20-10-ots-utilisation-scope, q2010-equipment-spec, ots-equipment-specification, ots-candidate-matching, functional-performance-interface-requirements, undeclared-characteristic-handling, mandatory-requirement-shortfall]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS OTS Utilisation — Equipment Specification (space-systems/ecss/q2010-equipment-spec)

Use when the task is the specification step of ECSS-Q-ST-20-10C clause
5.1.2 — writing down what the application actually demands of an
off-the-shelf unit, so that every candidate is measured against one
fixed yardstick instead of against whichever of its data-sheet figures
happens to look impressive.

## Domain quick reference

- The specification is written before the candidates are looked at, not
  distilled from them. A requirement set assembled after a favourite
  unit is in view reproduces that unit's strengths and quietly omits the
  properties it lacks, and the comparison it then supports is decided
  before it is run.
- Three families have to be populated. The functional family says what
  the unit must do, the performance family says how well, and the
  interface family says how it joins the rest of the system. An
  off-the-shelf unit is bought on its interfaces at least as much as on
  its function, so a specification with no interface requirement cannot
  decide anything, however detailed the rest of it is.
- Obligation is a separate axis from category. A mandatory requirement
  that goes unmet ends the candidate; a desirable one that goes unmet is
  a gap the programme may choose to live with, and collapsing the two
  into a single pass/fail either rejects usable units or accepts
  unusable ones.
- A characteristic the supplier never declared is not a zero. Scoring it
  as a failure buries a data-pack hole under an arithmetic result, and
  scoring it as a pass invents evidence. It is an unknown: reported as
  such, kept out of the compliance ratio, and blocking while the
  requirement behind it is mandatory.
- A criterion has to be matchable. A floor, a ceiling, a band, a target
  with a tolerance and a plain capability each compare differently, and
  a requirement written as prose with no criterion cannot be matched
  against a declared figure at all.

## Workflow

1. Validate every requirement: an identifier, one of the three
   categories, an obligation, and a criterion of a kind that can be
   compared with a declared datum. Refuse a duplicate identifier and an
   inverted band.
2. Report which of the three categories the specification never
   populated, and treat a specification with no interface requirement as
   unusable rather than as merely thin.
3. For each candidate, refuse declared data citing a requirement that is
   not in the specification — that is a sign the yardstick moved between
   candidates.
4. Grade each declared datum against its criterion, absorbing
   floating-point representation error at a bound with a named tolerance
   rather than by relaxing the bound.
5. Mark a requirement with no declared datum as undeclared, and keep it
   out of the compliance ratio so the ratio describes what was actually
   assessed.
6. Assign the verdict in precedence order: rejected on any unmet
   mandatory requirement, not assessable while a mandatory requirement
   is undeclared, acceptable with gaps when only desirable requirements
   fall short, compliant otherwise.
7. Rank the surviving candidates by their assessed compliance, breaking
   a tie on name so the shortlist is reproducible, and carry the gap
   list of each into the evaluation dossier.

## Pitfalls

- Writing the specification from the preferred unit's data sheet. The
  resulting requirement set is a description, and every later comparison
  is a formality.
- Leaving the interfaces to the integration phase. Connector type,
  protocol, mounting and thermal path are where an otherwise excellent
  unit becomes a redesign, and they are cheapest to discover here.
- Scoring an undeclared characteristic as a zero. It makes a data-pack
  hole look like a performance result, and the candidate is then dropped
  for something nobody ever measured.
- Treating every requirement as mandatory. A specification with no
  desirable requirements has no room to trade, so the first imperfect
  candidate ends the search.
- Widening a limit so a value sitting on it passes. Equality at the
  bound is a representation question, handled by the tolerance inside
  the comparison; the limit itself stays as specified.

## Behavior contract (gate 3)

The requirement validation, category-coverage check, criterion grading
with tolerance, undeclared-datum handling, compliance ratio, verdict
precedence and candidate ranking are exercised by the gate 3 contract
test: scripts/test_q2010_equipment_spec.py against
scripts/q2010_equipment_spec_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_q2010_equipment_spec.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
