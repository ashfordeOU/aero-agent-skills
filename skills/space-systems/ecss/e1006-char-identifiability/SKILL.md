---
name: e1006-char-identifiability
description: "Use when verify every requirement in a system specification carries a stable, unique identifier per ECSS-E-ST-10C §8.2.6: confirm each requirement has an assigned, project-controlled identifier in the agreed format, confirm no two requirements share an identifier, confirm no requirement is without an identifier, and flag identifier patterns suggesting instability such as gaps from renumbering events or placeholder values. Trigger: ecss, e-st-10-system-scope, requirements-management, identifiability, unique-identifier, requirements-traceability, stable-identifier."
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
  tags: [ecss, e-st-10-system-scope, requirements-management, identifiability, unique-identifier, requirements-traceability, stable-identifier]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Requirements Characteristic — Identifiability (space-systems/ecss/e1006-char-identifiability)

Use when the task is verifying that every requirement in a system specification
carries a stable, unique identifier per ECSS-E-ST-10C §8.2.6 — checking that
each requirement is anchored to a project-controlled identifier, that no two
requirements share an identifier, and that no identifier shows signs of
instability such as placeholder values or gaps from prior renumbering events.

## Domain quick reference

- §8.2.6 of ECSS-E-ST-10C defines identifiability as the property that each
  requirement is assigned a unique, project-controlled identifier that remains
  stable across revisions. The identifier is the primary key for traceability:
  every link in the verification matrix, every change notice, and every review
  item references it. An unstable or shared identifier breaks traceability and
  invalidates the downstream verification record.
- A valid identifier has three properties: it is present (non-empty, not a
  placeholder such as TBD/TBC), it conforms to the agreed format (typically a
  prefix indicating document and category, followed by a fixed-width numeric
  suffix, e.g. REQ-SYS-001), and it is unique within the specification. Meeting
  all three is necessary for the identifiability characteristic to be satisfied.
- Gaps in the numeric sequence of a prefix group are not automatically a
  violation — single-number gaps arise from normal requirement deletions — but
  large gaps (more than one missing number in sequence) are a warning indicator
  of a renumbering event, which destabilises the traceability record.
- Identifiability is a gate characteristic: a requirement set that fails it
  cannot be accepted for baseline, regardless of whether the individual
  requirement texts are otherwise well-formed.

## Workflow

1. Collect the full requirement set into a list of records, each carrying at
   minimum an identifier field. Accept no record without that field even if it
   is empty — a missing field is itself a finding.
2. Screen every record for a present, non-placeholder identifier. Any record
   whose identifier field is absent, empty, or contains a reserved placeholder
   (TBD, TBC, N/A) is flagged as missing an identifier. Record the index and
   any available label for each finding.
3. For each non-missing identifier, check it against the agreed format pattern
   (a project-defined regular expression). Identifiers that fail the pattern
   check are flagged as format violations. Record the identifier value and the
   pattern it violated.
4. Build an index of all non-missing identifiers and detect duplicates: any
   identifier that appears more than once is flagged, with the full list of
   occurrence indices recorded.
5. For each prefix group present in the set, extract the numeric suffix
   sequence, sort it, and scan for gaps larger than one. Flag each such gap as
   a stability warning, noting the bounding identifiers and the count of missing
   numbers.
6. Aggregate all findings: missing, format violations, duplicates, and gap
   warnings. The requirement set satisfies identifiability only when the first
   three categories are all empty. Gap warnings are advisory and do not block
   compliance, but must appear in the assessment report for human review.

## Pitfalls

- Treating a placeholder value such as TBD as an interim pass — a placeholder
  is not a stable identifier and the requirement is not identifiable until a
  real identifier is assigned. Carrying placeholders into baseline is a tracing
  gap, not an open action.
- Counting uniqueness only within a single document — identifiers are typically
  required to be unique across the full system requirement set, not just within
  a single file or section. Scope the uniqueness check to the agreed boundary
  (usually the full specification tree).
- Accepting a format-compliant, unique identifier as automatically stable — an
  identifier is unstable if it was derived from content (e.g. a hash of the
  requirement text) or if it was renumbered during drafting. The gap scan
  surfaces the latter; the former requires a project-process check outside this
  tool.
- Stopping at the first violation per requirement — a single requirement can
  simultaneously be missing its identifier and violate the format rule (e.g. a
  partially entered TBD-style string). Report all independent findings per
  record.

## Behavior contract (gate 3)

The presence, format, uniqueness, and gap-detection logic is exercised by the
gate 3 contract test: scripts/test_e1006_char_identifiability.py against
scripts/e1006_char_identifiability_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1006_char_identifiability.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
