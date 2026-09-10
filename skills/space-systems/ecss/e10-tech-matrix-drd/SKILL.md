---
name: e10-tech-matrix-drd
description: "Use when generating or validating the Technology Matrix deliverable per ECSS-E-ST-10C Annex F: check the document carries the required DRD sections, each listed technology carries the required matrix fields (name, current TRL, target TRL, mission applicability), TRL values are valid (integer 1-9) and non-regressing (target TRL at or above current TRL), and mission applicability is resolved rather than left blank or TBD. Trigger: ecss, e-st-10c, technology matrix, trl, technology readiness level, annex f, mission applicability, technology plan."
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
  tags: [ecss, e-st-10c, technology-matrix, trl, annex-f, drd]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Technology Matrix DRD (space-systems/ecss/e10-tech-matrix-drd)

Use when the task is generating or validating the Technology Matrix
deliverable under ECSS-E-ST-10C Annex F: a document-and-record
combination that lists every technology relevant to the project
against its technology readiness level (TRL) and its applicability
to the mission.

## Domain quick reference

- The Technology Matrix is a normative DRD deliverable (Annex F): a
  document holding the required front-matter sections plus a matrix
  with one row per technology item.
- Each matrix row must carry, at minimum: the technology name,
  its current TRL, the target TRL required for the mission, and a
  mission-applicability status.
- TRL is reported on the 1-9 integer scale (per E-AS-11 / ISO 16290);
  a value outside that range or non-integer is not a valid TRL entry.
- A technology's target TRL is the maturity level it must reach
  before use; a target TRL below the already-demonstrated current
  TRL is a data error (maturity does not need to regress).
- Mission applicability records whether the technology is actually
  used by the project ("applicable") or was assessed and ruled out
  ("not applicable"); leaving it blank or "TBD" means the assessment
  is not yet closed.
- This leaf checks the Technology Matrix document and its rows; it
  does not run the technology plan and risk-management activity
  that produces the matrix's inputs (see e10-technology) or check
  the separate Technology Plan document structure (see e10-tp-drd).

## Workflow

1. Collect the Technology Matrix document's front-matter sections
   present, and the technology matrix rows: technology name mapped
   to its recorded fields (current TRL, target TRL, mission
   applicability, and any others).
2. Check DRD section presence against the minimum section set; list
   any missing sections.
3. Check each row for missing required fields (name is implicit via
   the mapping key; current TRL, target TRL, and mission
   applicability must each be present).
4. Check TRL validity: current TRL and target TRL must each be an
   integer from 1 to 9; list any row with an invalid value.
5. Check TRL progression: target TRL must be greater than or equal
   to current TRL for every row; list any regression.
6. Check mission-applicability resolution: the value must be
   "applicable" or "not applicable"; list any row left blank, "TBD",
   or any other unresolved value.
7. The matrix is ready only when there are no missing sections, no
   rows with missing fields, no invalid TRLs, no TRL regressions,
   and no unresolved applicability entries; otherwise report the
   specific issues found for correction.

## Pitfalls

- Publishing a matrix row with a target TRL below the current TRL
  (a silent regression, usually a copy-paste or transcription error).
- Leaving mission applicability blank or "TBD" and treating the row
  as closed because the TRL fields are filled in.
- Recording a TRL as a non-integer or out-of-range value (e.g. "TRL
  6-7" or "10") instead of a single value on the 1-9 scale.
- Confusing this leaf's document/row-level checks with the broader
  technology planning and risk-management activity (e10-technology)
  or the Technology Plan DRD content (e10-tp-drd).

## Behavior contract (gate 3)

The section-check, field-check, TRL-validity, TRL-progression, and
applicability-resolution logic is exercised by the gate 3 contract
test: scripts/test_e10_tech_matrix_drd.py against
scripts/e10_tech_matrix_drd_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e10_tech_matrix_drd.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
