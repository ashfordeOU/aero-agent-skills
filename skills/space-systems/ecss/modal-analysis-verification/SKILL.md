---
name: modal-analysis-verification
description: "Use when verify that structural natural frequencies and mode shapes satisfy
  the frequency requirements and mass participation criteria per ECSS-E-ST-32C clause
  4.6.2.4: determine the fundamental frequency for each structural axis from the effective
  mass fractions across all computed modes, compute the frequency margin against the
  minimum allowable requirement, confirm that cumulative effective mass participation
  in each axis reaches the required threshold to establish that the model captures the
  dominant dynamic behavior, and identify axes where no mode contributes effective mass.
  Results support the modal survey test (cross-reference 32-11). Trigger: ecss,
  e-st-32-structures-scope, modal-analysis, natural-frequency, frequency-requirement,
  effective-mass, mass-participation, beam-vibration."
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
  tags: [ecss, e-st-32-structures-scope, modal-analysis, natural-frequency, frequency-requirement, effective-mass, mass-participation, beam-vibration]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural — Modal Analysis Verification (space-systems/ecss/modal-analysis-verification)

Use when the task is verifying structural natural frequencies and mode shapes against
the frequency requirements and mass participation criteria of ECSS-E-ST-32C clause
4.6.2.4. Covers determination of the fundamental frequency per structural axis,
frequency margin calculation, and cumulative effective mass participation assessment.
Cross-references the modal survey test (ECSS-E-ST-32C test 32-11).

## Domain quick reference

- Clause 4.6.2.4 requires that natural frequencies computed by the structural dynamic
  model meet or exceed the minimum allowable frequency specified for each structural
  axis (typically lateral-X, lateral-Y, and axial-Z). The minimum frequency requirement
  per axis is derived from the coupled loads analysis interface or the launcher authority
  interface control document; the clause does not set a universal numeric value — the
  applicable requirement is always project-specific.
- The fundamental frequency in a given axis is the lowest natural frequency among all
  modes that carry non-zero effective mass in that axis. A mode with zero effective
  mass fraction in an axis is a locally resonant mode and does not bound the frequency
  requirement for that axis.
- The frequency margin is the fractional excess of the fundamental frequency above the
  minimum requirement: (f_fundamental / f_required) − 1. A negative margin is a
  frequency requirement violation and must be dispositioned before the structural
  verification record can be closed.
- Effective mass participation (also called mass fraction) quantifies what fraction of
  the total structural mass is mobilised by each mode in a given direction. Cumulative
  effective mass participation across all retained modes must reach the project-required
  threshold (commonly 90 %) in each axis to confirm that the model captures the
  dominant dynamic response and that no significant frequency has been omitted from the
  modal extraction.
- A failed mass participation check does not necessarily mean a frequency violation;
  it means the modal basis is incomplete and the fundamental frequency result is
  unreliable until further modes are extracted.

## Workflow

1. Collect the modal analysis output: the list of extracted modes, each with its
   natural frequency and the effective mass fraction it contributes in each structural
   axis. Collect the total structural mass and the minimum frequency requirement for
   each axis from the interface control document or coupled loads analysis.
2. For each structural axis, identify the fundamental frequency: the minimum natural
   frequency among all modes whose effective mass fraction in that axis is greater than
   zero. If no mode contributes effective mass in an axis, record that the fundamental
   frequency is undefined for that axis — this is itself a finding, not a pass.
3. Compute the frequency margin for each axis: (f_fundamental / f_required) − 1. A
   margin equal to or greater than zero satisfies the requirement; a negative margin is
   a violation.
4. For each structural axis, sum the effective mass fractions across all retained modes.
   Compare the cumulative fraction against the project mass participation threshold
   (default 90 %). A cumulative fraction below the threshold means the modal extraction
   is incomplete; the frequency result for that axis should be treated as preliminary
   until further modes are added.
5. Aggregate the frequency margin results and the mass participation results per axis.
   The modal analysis is fully verified only when every axis meets both the frequency
   requirement and the mass participation threshold.
6. Cross-check the verified fundamental frequencies against the modal survey test plan
   (test 32-11) to confirm the measured frequencies bracket the predicted values within
   the acceptable correlation tolerance defined in the test report.

## Pitfalls

- Selecting the lowest overall natural frequency as the fundamental frequency for all
  axes simultaneously — a mode with zero effective mass in a given axis does not bound
  the frequency requirement for that axis; the fundamental frequency must be resolved
  per axis from the modes that actually mobilise mass in that direction.
- Declaring the frequency requirement satisfied when the mass participation check has
  not been met — if the modal extraction is incomplete, the lowest effective-mass mode
  found so far may not be the true fundamental; the mass participation check guards
  against this premature conclusion.
- Using the total structural mass in the effective mass fraction denominator when the
  model is a substructure or component model — the effective mass fractions must be
  normalised to the correct reference mass for the boundary conditions used in the
  analysis; mixing subsystem and system-level mass references will produce incorrect
  cumulative fractions.
- Treating a positive frequency margin as a permanent clearance — the margin is valid
  only for the flight configuration analyzed; any mass or stiffness change to the
  structure requires re-verification.

## Behavior contract (gate 3)

The fundamental frequency extraction, frequency margin computation, mass participation
accumulation, and overall compliance assessment logic is exercised by the gate 3
contract test: scripts/test_modal_analysis_verification.py against
scripts/modal_analysis_verification_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_modal_analysis_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
