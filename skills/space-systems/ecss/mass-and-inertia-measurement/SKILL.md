---
name: mass-and-inertia-measurement
description: "Use when determine mass properties, center-of-gravity position, and moments of inertia for a spacecraft or structural assembly per ECSS-E-ST-32C §4.6.3.18: measure total mass against a precision reference, locate the CG on all three principal axes, derive moments of inertia from torsion-pendulum swing periods corrected for fixture contribution, validate the torsion constant against a calibration reference object, and compare every measured property against the analysis prediction within its tolerance. Flag each property that falls outside its tolerance band, and flag any measurement without a corresponding prediction on record. Trigger: ecss, e-st-32c, e-st-32-structures-scope, mass-properties, moment-of-inertia, center-of-gravity, torsion-pendulum, mass-measurement, inertia-tensor."
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
  tags: [ecss, e-st-32c, e-st-32-structures-scope, mass-properties, moment-of-inertia, center-of-gravity, torsion-pendulum, mass-measurement, inertia-tensor]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mass and Inertia Property Measurement (space-systems/ecss/mass-and-inertia-measurement)

Use when the task is to measure and verify the mass properties of a spacecraft
structural assembly per ECSS-E-ST-32C §4.6.3.18 — determining total mass,
center-of-gravity (CG) location, and the full inertia tensor (principal moments
plus products of inertia), then comparing every measured value against the
structural analysis prediction within the specified tolerance.

## Domain quick reference

- The mass-properties measurement campaign covers three deliverables: total
  mass, CG position (three coordinates relative to a defined reference frame),
  and the six independent elements of the inertia tensor (Ixx, Iyy, Izz, Ixy,
  Ixz, Iyz) referenced to the same frame.
- Mass is measured on a precision balance calibrated against a traceable
  reference; the reading is accepted when it falls within the allowable
  deviation from the structural mass budget prediction.
- CG is located by the moment-balance method or a multi-point suspension:
  the assembly is supported at known reaction points, the suspension forces
  are measured, and the CG coordinates are computed from equilibrium. Each
  axis result is compared against the prediction with a per-axis tolerance.
- Moments of inertia are measured using a torsion pendulum (swing table):
  the period T of free torsional oscillation is recorded with and without
  the test item, the fixture inertia is subtracted, and the item inertia
  I = k(T_total² − T_fixture²) / (4π²) is derived. The torsion constant k
  is established by a calibration run with a reference object of certified
  inertia before the test article is mounted.
- The inertia tensor must be symmetric (Iij = Iji); any asymmetry beyond
  measurement uncertainty indicates an error in axis assignment or data
  reduction and must be resolved before the result is accepted.
- Tolerance bands for each property are defined in the structural mass
  properties requirement; a finding is raised for every property that
  falls outside its band or for which no prediction exists on record.

## Workflow

1. Confirm the measurement coordinate frame, the reference point (typically
   the launch vehicle interface or structural reference point), and the
   tolerance bands for mass, CG per axis, and each inertia component.
   Reject the test setup if any of these inputs is missing.
2. Calibrate the torsion pendulum before mounting the test article: measure
   the empty-table period T_base, mount the reference object, measure T_ref,
   and compute the torsion constant k = I_ref · 4π² / (T_ref² − T_base²).
   Record k and its calibration uncertainty.
3. Measure total mass on the calibrated balance. Compute the deviation from
   the structural prediction as (measured − predicted) / predicted and compare
   against the tolerance fraction. Issue a finding if exceeded.
4. Measure CG on each of the three axes (one per suspension configuration or
   tilting run). Compute the signed deviation from the prediction per axis.
   Issue a finding for each axis that falls outside its tolerance.
5. Measure the torsion period with the item mounted (T_total) for each
   measurement axis, subtract the fixture contribution, and compute I per
   axis using k from step 2. For product-of-inertia axes, rotate the table
   45° and apply the standard tensor-rotation formula to recover the
   off-diagonal terms. Compare each derived element against its prediction
   within the inertia tolerance. Issue a finding for each element outside
   tolerance.
6. Assemble the inertia tensor from the six elements, verify symmetry within
   measurement uncertainty, and confirm positive definiteness (all principal
   minors positive). Reject asymmetric tensors and investigate before
   acceptance.
7. Compile a mass-properties report listing all measured values, predictions,
   deviations, tolerance bands, and findings. The assembly is accepted only
   when every property passes and the tensor passes symmetry and definiteness
   checks.

## Pitfalls

- Omitting the fixture-inertia subtraction and reporting I_total as the item
  inertia — the fixture can contribute 20–50 % of the total oscillation
  period; not subtracting it inflates the result significantly.
- Using a stale torsion constant from a prior test day without a fresh
  calibration check — temperature-dependent stiffness changes in the torsion
  wire shift k and bias all inertia results on that day.
- Computing CG deviation only in absolute distance and not per axis — an
  assembly whose Euclidean CG error is within tolerance may still violate
  a tighter per-axis requirement; both checks are required.
- Accepting the tensor without a symmetry check — a data-entry error or
  axis-label swap produces an asymmetric tensor that gives physically
  impossible results in downstream dynamics analyses.
- Treating a missing prediction as a free pass — a measured property with
  no on-record prediction cannot be accepted as compliant; the absence of a
  reference value is itself a finding.

## Behavior contract (gate 3)

The mass-measurement, CG-validation, torsion-pendulum derivation,
fixture-correction, torsion-constant calibration, inertia comparison, and
tensor-symmetry logic are exercised by the gate 3 contract test:
scripts/test_mass_and_inertia_measurement.py against
scripts/mass_and_inertia_measurement_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_mass_and_inertia_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
