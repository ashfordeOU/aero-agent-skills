---
name: rigid-body-motion-checks
description: "Use when verify that a finite element model passes rigid-body checks
  under ECSS-E-ST-32C clause 5.4: confirm the assembled mass matrix yields a total
  mass matching the reference value within tolerance, confirm that applying each of
  the six rigid-body displacement modes (three translations, three rotations) produces
  near-zero strain energy, and confirm that residual forces arising from rigid-body
  displacements are below the acceptance threshold. Each check produces a pass or
  fail result with a numeric residual; all three must pass for the model to be accepted.
  Trigger: ecss, e-st-32-structures-scope, rigid-body-checks, mass-matrix, strain-energy,
  residual-forces, fem-verification, finite-element."
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
  tags: [ecss, e-st-32-structures-scope, rigid-body-checks, mass-matrix, strain-energy, residual-forces, fem-verification, finite-element]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Rigid-Body Motion Checks (space-systems/ecss/rigid-body-motion-checks)

Use when the task is to verify a finite element model against the rigid-body
check requirements of ECSS-E-ST-32C clause 5.4 — confirming the mass matrix,
stress-free rigid-body strain energy, and residual force balance all meet their
acceptance thresholds before structural analysis proceeds.

## Domain quick reference

- A correctly assembled finite element model must satisfy three independent
  rigid-body checks before structural results are trusted. Each check targets
  a different class of modelling error.
- **Mass matrix check**: the sum of all nodal masses produced by the assembled
  mass matrix must match the reference (design) mass within a stated fraction.
  A discrepancy flags missing mass items, duplicated masses, or mis-scaled
  density properties.
- **Strain energy check (stress-free rigid-body motion)**: when each of the six
  rigid-body displacement fields (three translations TX, TY, TZ and three
  rotations RX, RY, RZ) is applied to the unconstrained model, the resulting
  internal strain energy must be essentially zero. Non-zero strain energy for a
  rigid-body mode indicates spurious stiffness: grounded degrees of freedom,
  incorrectly constrained multi-point constraint equations, or element
  formulation errors that resist rigid translation or rotation.
- **Residual force check**: applying a rigid-body displacement to a free-floating
  model should produce no net internal force vector. A non-zero residual force
  indicates a force-balance error in the stiffness or constraint assembly —
  distinct from a strain energy error and detectable only through this separate
  check. Both the strain energy and residual force checks are run for all six
  rigid-body modes; a failure in either is a separate finding.
- Acceptance thresholds for strain energy and residual force are relative to a
  reference energy or force derived from the applied displacement amplitude and
  the model's overall stiffness level; the analyst sets these thresholds before
  the check and documents the basis.

## Workflow

1. Assemble the full finite element model including all mass items (structural
   mass, non-structural mass, lumped point masses, fluid mass, etc.). Sum the
   diagonal of the assembled mass matrix to obtain the computed total mass.
   Compare against the reference mass: if the relative error exceeds the stated
   tolerance, flag a mass matrix finding and do not proceed until resolved.
2. For each of the six rigid-body modes (TX, TY, TZ, RX, RY, RZ), apply a
   unit rigid-body displacement field to the free-free (unconstrained) model and
   compute the resulting internal strain energy. Compare each mode's strain
   energy against the strain energy threshold; flag any mode whose energy exceeds
   the threshold as a strain energy finding.
3. For each of the same six rigid-body modes, extract the residual force vector
   produced by the rigid-body displacement and compute its magnitude. Compare
   each magnitude against the residual force threshold; flag any mode whose
   residual exceeds the threshold as a residual force finding.
4. Collect all findings from steps 1–3. The model passes rigid-body checks only
   when the mass finding list, the strain energy finding list, and the residual
   force finding list are all empty. Record the numeric residuals for each check
   in the model verification report regardless of pass or fail.
5. If any finding is raised, investigate the root cause before re-running:
   mass errors point to property or density table mismatches; strain energy
   errors point to spurious grounding or constraint conflicts; residual force
   errors point to force-balance assembly faults. Do not relax thresholds as a
   remedy — correct the model.

## Pitfalls

- Running the strain energy check on a constrained (boundary-condition applied)
  model rather than the free-free model: boundary reactions absorb the rigid-body
  displacement and the check always passes, masking real grounding errors.
- Treating a near-zero strain energy result as confirmation that residual forces
  are also acceptable — the two quantities are independent; a model can have
  negligible strain energy for a given mode yet exhibit a significant residual
  force if the force-balance assembly is inconsistent with the stiffness assembly.
- Using an overly loose strain energy threshold (e.g. set relative to model
  peak strain energy rather than a small absolute fraction) so that genuine
  spurious stiffness passes undetected.
- Checking only the three translational modes and skipping the three rotational
  modes — rotational spurious stiffness from shell normal-rotation coupling or
  beam offset errors is only detectable through the RX, RY, RZ displacement
  fields.
- Reporting a mass check pass without documenting which mass items were included
  in the reference mass, making future mass growth assessments ambiguous.

## Behavior contract (gate 3)

The mass matrix, strain energy, and residual force check logic is exercised by
the gate 3 contract test: scripts/test_rigid_body_motion_checks.py against
scripts/rigid_body_motion_checks_logic.py (stdlib unittest, offline). Run:

```
python3 scripts/test_rigid_body_motion_checks.py
```

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
