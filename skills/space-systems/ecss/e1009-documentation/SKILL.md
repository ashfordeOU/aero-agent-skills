---
name: e1009-documentation
description: "Use when maintain the Coordinate Systems Document (CSD) across the
  spacecraft project life cycle under ECSS-E-ST-10C §5.2.2: define each coordinate
  system with a unique identifier, origin, axis triad, and reference frame; validate
  entry completeness; enforce permissible lifecycle state transitions (draft -> review
  -> approved -> superseded); verify that required project phases each carry at least
  one applicable coordinate system; and compute a CSD readiness score to track documentation
  maturity. Trigger: ecss, e-st-10-system-scope, coordinate-systems-document, csd,
  reference-frame, axis-definition, lifecycle, project-phases, documentation-maturity."
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
  tags: [ecss, e-st-10-system-scope, coordinate-systems-document, csd, reference-frame, axis-definition, lifecycle, project-phases]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS System Engineering — Coordinate Systems Document Maintenance (space-systems/ecss/e1009-documentation)

Use when the task is to maintain the Coordinate Systems Document (CSD) across
the spacecraft project life cycle under ECSS-E-ST-10C §5.2.2 — establishing
and updating each coordinate system definition, enforcing documentation
completeness and lifecycle discipline, and verifying phase coverage.

## Domain quick reference

- The CSD is the single controlled reference listing every coordinate system
  used in the spacecraft project. Each entry covers one coordinate system:
  a unique identifier, a descriptive name, an origin description, axis
  definitions for the x/y/z triad, the parent reference frame, the project
  phases in which that system is applicable, and an entry status.
- Entry status follows a fixed path: draft (under preparation) →
  review (under verification) → approved (controlled baseline) →
  superseded (replaced by a later revision). Skipping states or reversing
  to a prior state without a rework step is a documentation non-conformance.
- The CSD document itself has a lifecycle state that mirrors the entry
  maturity: the document may not be declared approved while it still carries
  draft or review-status entries that govern active project phases.
- Phase coverage means that for each project phase (A through E), at least
  one coordinate system entry must list that phase in its applicable_phases
  field. A phase with no applicable coordinate system is a gap that indicates
  either missing entries or incorrect phase attribution.

## Workflow

1. Collect the current list of coordinate systems in use across all subsystems.
   For each system, assign a unique identifier, capture the origin description,
   define each axis of the right-hand triad with a non-empty prose description,
   record the parent reference frame, and list the project phases for which
   the definition is applicable.
2. Validate every entry against the required field set. Reject entries with
   missing fields, empty axis descriptions, unknown status values, or empty
   applicable-phase lists before they enter the controlled document.
3. Check identifier uniqueness across all entries. Duplicate identifiers
   indicate either a split definition that must be merged or a transcription
   error; resolve before issuing the document revision.
4. For each entry whose status is changing, verify the transition is on the
   permitted path: draft -> review, review -> approved, review -> draft
   (rework), or approved -> superseded. Reject any other direction.
5. Check that every project phase listed in the programme's scope is covered
   by at least one approved or review-status entry. Report missing phases as
   documentation gaps.
6. Compute the CSD readiness score to track overall maturity. Score factors
   are document-level field completeness, lifecycle state, and the fraction
   of entries that individually pass validation. A score below 80 signals
   that the CSD is not ready for a controlled-document release.
7. Produce a consolidated findings list: entry-level issues keyed by
   identifier, document-level issues, duplicate identifiers, missing phase
   coverage gaps, and the readiness score. The CSD revision may only be
   issued when all findings are resolved.

## Pitfalls

- Approving the document while individual entries remain in draft state —
  the document lifecycle state must reflect the lowest maturity of its
  active entries; a premature approval is a traceability non-conformance.
- Accepting an empty or whitespace-only axis definition as satisfactory —
  an axis without a prose description cannot be verified against drawings
  or models, making the entry effectively unusable for design checks.
- Treating phase coverage as optional when a phase is not yet active —
  coordinate system definitions must be in place before the phase begins,
  not after; missing coverage at phase entry is a late capture.
- Merging two coordinate system definitions under one identifier to reduce
  the entry count — each coordinate system must have its own unique
  identifier; combined entries create ambiguity in interface documents and
  data packages.

## Behavior contract (gate 3)

The entry validation, identifier uniqueness, lifecycle transition, phase
coverage, and readiness scoring logic is exercised by the gate 3 contract
test: scripts/test_e1009_documentation.py against
scripts/e1009_documentation_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_documentation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
