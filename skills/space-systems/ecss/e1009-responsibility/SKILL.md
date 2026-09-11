---
name: e1009-responsibility
description: "Use when verify responsibility assignments for each coordinate system definition and transformation entry in a Coordinate System Document, ensuring every entry carries exactly one identified owner before the document is baselined. The procedure checks no CSD entry is unassigned (orphaned) and no entry carries ambiguous dual ownership, producing a compliant responsibility matrix per ECSS-E-ST-10C §5.2.1. Trigger: ecss, e-st-10-system-scope, coordinate-system, transformation, responsibility, ownership, csd, single-owner, assignment."
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
  tags: [ecss, e-st-10-system-scope, coordinate-system, transformation, responsibility, ownership, csd, single-owner]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Systems Engineering — CSD Responsibility Assignment (space-systems/ecss/e1009-responsibility)

Use when the task is to verify that every coordinate system definition and
transformation entry in a Coordinate System Document (CSD) has a single,
named responsible owner, per ECSS-E-ST-10C §5.2.1. Each CSD entry must be
traceable to exactly one owner; unassigned or ambiguously owned entries block
document baselining.

## Domain quick reference

- ECSS-E-ST-10C §5.2.1 requires that the Coordinate System Document record,
  for each coordinate system and each transformation defined therein, the
  identity of the responsible party — an individual, role, or organizational
  unit that owns the definition and is accountable for its correctness.
- A CSD entry belongs to one of two types: a coordinate system definition
  (origin, axes, reference frame) or a transformation (the mapping between two
  defined coordinate systems). Both types must carry a single owner; neither
  may be left unassigned in a baselined document.
- "Single owner" means exactly one owner string per entry. An entry with an
  empty, missing, or whitespace-only owner field is considered unassigned. An
  entry whose name appears more than once in the document is a structural
  conflict; duplicate names must be resolved before ownership can be verified.
- Ownership is a documentary check, not a numerical one. The compliance
  verdict is binary: every entry assigned (compliant) or one or more entries
  unassigned or duplicated (non-compliant).

## Workflow

1. Collect all CSD entries — each entry carries a unique name, a type
   (coordinate system or transformation), and an owner field. Reject any entry
   missing a required field before it enters the check.
2. Scan the full entry list for duplicate names. A name appearing more than
   once signals a structural conflict; flag each duplicate and stop that
   entry's ownership check until the conflict is resolved.
3. For each structurally valid entry, inspect the owner field: flag the entry
   as unassigned if the owner is absent, empty, or contains only whitespace.
4. Aggregate all findings (unassigned entries and duplicate-name conflicts)
   into an issues list. An empty issues list means every entry has a single,
   identified owner and the CSD is ownership-compliant.
5. Produce a responsibility report: total entry count, assigned count,
   unassigned count, per-owner entry lists, and the compliant flag. Deliver
   this report as the output artifact for review gate sign-off.
6. If any findings exist, return the issues list to the CSD owner for
   remediation before the document is baselined. Do not mark the document
   compliant until a re-check on the corrected version returns an empty issues
   list.

## Pitfalls

- Treating a whitespace-only owner field as assigned — a field containing
  only spaces or tabs carries no owner identity and must be treated the same
  as an empty or absent field.
- Skipping the duplicate-name check and proceeding directly to ownership
  verification — a duplicated name may appear once with an owner and once
  without, causing a false "assigned" result for the unowned copy.
- Conflating "no issues found" with "fully reviewed" — the checker verifies
  ownership completeness only; the technical correctness of each coordinate
  system definition is a separate engineering review step.
- Applying the check to a partial CSD snapshot instead of the complete
  document — a subset-only check may miss unassigned entries that are present
  in sections not included in the snapshot.

## Behavior contract (gate 3)

The entry-validation, duplicate-name detection, ownership-completeness, and
report-generation logic is exercised by the gate 3 contract test:
scripts/test_e1009_responsibility.py against
scripts/e1009_responsibility_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_responsibility.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
