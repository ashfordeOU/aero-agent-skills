---
name: drd-modal-dynamic-response
description: "Use when prepare the modal and dynamic response analysis report
  (MDRA) for a space structure per ECSS-E-ST-32C Annex J: identify natural
  frequencies and mode shapes from the structural math model, compute effective
  mass fractions per axis to verify modal completeness above the 90% threshold,
  check the fundamental frequency against the minimum stiffness requirement,
  evaluate frequency separation margins between structural modes and excitation
  sources, validate damping ratios, and assess dynamic response under sine,
  random, and shock loading. Flag missing effective mass budgets or insufficient
  frequency margins before the report is finalised. Trigger: ecss,
  e-st-32-structures-scope, modal-analysis, dynamic-response, natural-frequency,
  effective-mass, mode-shape, modal-truncation, frequency-margin."
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
  tags: [ecss, e-st-32-structures-scope, modal-analysis, dynamic-response, natural-frequency, effective-mass, mode-shape, modal-truncation, frequency-margin]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Modal and Dynamic Response Analysis (space-systems/ecss/drd-modal-dynamic-response)

Use when the task is preparing the modal and dynamic response analysis
(MDRA) report for a space structure under ECSS-E-ST-32C Annex J:
extracting eigenvalues, verifying effective mass completeness, checking
frequency margins, and assessing dynamic response to the specified load
environments.

## Domain quick reference

- Annex J of ECSS-E-ST-32C defines the mandatory content of the MDRA
  report. The report must document the structural math model, boundary
  conditions, eigensolution results (natural frequencies, mode shapes,
  effective masses per axis), damping assumptions, and the dynamic
  response results for each load environment (sine, random, shock).
- Modal completeness is verified by summing the effective masses per
  translational axis and checking that the sum reaches at least 90 % of
  the total structural mass. A modal basis that does not meet this
  threshold is considered truncated and must be extended with additional
  modes before response calculations proceed.
- The fundamental frequency of a structural assembly must meet the
  minimum stiffness target imposed by the system-level load document.
  Exceeding the target is acceptable; falling below it requires a design
  change or a formal waiver before the analysis result is used to derive
  interface loads.
- Frequency separation between a structural mode and a recurring
  excitation source (e.g., AOCS thruster firing frequency, rotating
  machinery) must be at least 10 % of the excitation frequency to avoid
  near-resonant amplification. Where the margin cannot be achieved, the
  dynamic amplification factor at the actual frequency ratio must be
  computed and applied to the interface loads.
- Damping ratios for space structures are typically in the range
  0.01–0.05 (1–5 % of critical damping). Values above 0.05 require
  justification by test correlation; the modal model must not use assumed
  damping without a stated justification on record.

## Workflow

1. Review the structural math model summary: confirm boundary conditions,
   mass properties, and the frequency range covered by the eigensolution.
   Reject a model whose documented frequency range does not cover the
   load environment's frequency band.
2. Extract the eigensolution table: list each mode by index, natural
   frequency (Hz), and effective mass per translational axis (X, Y, Z).
   Assign each mode to one of three bands — rigid-body (< 0.1 Hz),
   flexible (0.1 Hz to 200 Hz), or high-frequency (≥ 200 Hz) — using the
   mode's natural frequency.
3. Sum the effective masses per axis and divide by the total structural
   mass. Flag any axis whose effective mass fraction falls below 0.90;
   request additional modes from the analyst until the threshold is met.
4. Check the lowest flexible-band natural frequency against the
   system-level minimum stiffness requirement. Record the margin in Hz;
   a negative margin is a non-conformance.
5. For each structural mode in the flexible band, compare its natural
   frequency to each known excitation frequency. Compute the separation
   ratio |f_mode – f_excit| / f_excit; flag every mode–excitation pair
   whose separation ratio falls below 0.10.
6. For every flagged mode–excitation pair, compute the steady-state
   dynamic amplification factor at the actual frequency ratio and the
   structure's damping ratio. Apply this factor to the quasi-static load
   level when deriving the combined interface load.
7. Validate the reported damping ratio for each mode: confirm it is
   positive, strictly below 1.0 (underdamped), and does not exceed 0.05
   without a justification reference in the report.
8. Check that the MDRA report contains every mandatory section listed in
   Annex J. Record any missing section as a report non-conformance; do
   not accept a report with missing sections.

## Pitfalls

- Proceeding with a truncated modal basis (effective mass fraction below
  0.90) underestimates response because the omitted high-frequency modes
  can carry significant mass participation at their resonant frequencies.
- Treating a near-resonant condition (separation ratio < 0.10) as
  acceptable without computing the actual dynamic amplification factor
  underestimates peak loads and produces non-conservative margin of
  safety calculations.
- Using an assumed damping ratio without a test-correlation basis
  introduces conservatism (if the ratio is too low) or non-conservative
  results (if too high) that are undetectable without an audit trail.
- Accepting a MDRA report that omits the effective mass table: without
  this table the modal completeness check cannot be performed and the
  analysis is not auditable per Annex J.

## Behavior contract (gate 3)

The fundamental-frequency check, effective-mass fraction computation,
modal completeness check, mode band assignment, frequency separation,
dynamic amplification, modal participation factor, and report-field
completeness logic are exercised by the gate 3 contract test:
scripts/test_drd_modal_dynamic_response.py against
scripts/drd_modal_dynamic_response_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_drd_modal_dynamic_response.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
