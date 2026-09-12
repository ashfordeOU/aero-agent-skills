---
name: mass-and-inertia-analysis
description: "Use when determine the analytical mass and inertia properties of a spacecraft structure or subsystem under ECSS-E-ST-32C clause 4.6.2.18: inventory all structural components with their individual mass, geometric centroid, and self-inertia tensor; compute the system center of mass from the mass-weighted sum of component centroids; apply the parallel-axis theorem to transfer each component's self-inertia to the system reference point; sum over all components to obtain the system inertia tensor; verify the resulting total mass against the allocated mass budget; and flag any component with a missing or invalid mass, centroid, or self-inertia before it enters the computation. Trigger: ecss, e-st-32-structures-scope, mass-properties, inertia-tensor, center-of-mass, parallel-axis-theorem, mass-budget, structural-mass-analysis."
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
  tags: [ecss, e-st-32-structures-scope, mass-properties, inertia-tensor, center-of-mass, parallel-axis-theorem, mass-budget, structural-mass-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Mass and Inertia Property Computation (space-systems/ecss/mass-and-inertia-analysis)

Use when the task is the analytical determination of mass and inertia properties
for a spacecraft structure or subsystem per ECSS-E-ST-32C clause 4.6.2.18 —
building up the system-level mass, center of mass, and inertia tensor from
component-level inputs and verifying the result against the allocated mass budget.

## Domain quick reference

- The computation takes as input a component inventory: each entry carries a
  name, scalar mass (kg), three-element centroid vector (m), and a 3×3
  self-inertia tensor about that component's own centroid (kg m²).
- The system center of mass is the mass-weighted arithmetic mean of component
  centroids. No component may have zero or negative mass; any such entry is an
  error to be flagged before the computation begins.
- The parallel-axis theorem transfers a component's self-inertia tensor to any
  desired reference point. For a component of mass m whose centroid is displaced
  by vector **d** from the reference point, the corrected tensor is:
  I_ref = I_cm + m × (|**d**|² × δ_ij − d_i × d_j), where δ_ij is the Kronecker
  delta. The system inertia tensor is the sum of these corrected tensors over all
  components. The result is symmetric by construction.
- Mass budget compliance is a scalar check: total system mass must not exceed the
  allocated budget. A positive margin (budget − total) indicates compliance;
  zero margin is still compliant; negative margin is a finding.
- A component with an absent or malformed centroid, inertia tensor, or mass field
  must be rejected before any numerical step — partial inputs silently corrupt
  the tensor.

## Workflow

1. Receive the component inventory. Validate that every entry carries a positive
   scalar mass, a three-element centroid, and a 3×3 inertia-tensor matrix. Reject
   and report any entry that fails validation before proceeding.
2. Sum all component masses to obtain the total system mass.
3. Compute the system center of mass: for each coordinate axis, multiply each
   component's mass by its centroid coordinate along that axis, sum the products,
   then divide by the total mass.
4. For each component, compute the displacement vector **d** from the chosen
   reference point (typically the system center of mass or a nominated body-frame
   origin) to the component centroid. Apply the parallel-axis correction to the
   component's self-inertia tensor. Accumulate the corrected tensor into the
   running system tensor.
5. Verify total system mass against the allocated mass budget. Record the margin.
   A negative margin is a non-compliance finding; an unset budget is a gap that
   must be flagged — it is not a pass.
6. Report: total mass, center-of-mass coordinates, full 3×3 system inertia tensor,
   mass budget margin, and any validation errors. The output is not complete until
   all six items are present.

## Pitfalls

- Applying the parallel-axis correction with the wrong sign on the product-of-inertia
  terms — the off-diagonal correction is −m × d_i × d_j, not +m × d_i × d_j.
  An incorrect sign produces a non-symmetric tensor, which is a reliable indicator
  of a sign error.
- Treating an absent mass budget as compliance — if no budget value has been set,
  the compliance step cannot be executed and must be flagged as a data gap rather
  than silently recorded as passing.
- Summing component inertia tensors without transferring them to a common reference
  first — tensors defined about different origins cannot be added directly; each
  must be shifted to the common reference before accumulation.
- Accepting a component with a centroid of length other than 3 or an inertia matrix
  of shape other than 3×3 — both produce wrong numerical results without an
  obvious runtime error if validation is skipped.

## Behavior contract (gate 3)

The component validation, center-of-mass, parallel-axis, inertia summation, and
mass-budget logic is exercised by the gate 3 contract test:
scripts/test_mass_and_inertia_analysis.py against
scripts/mass_and_inertia_analysis_logic.py (stdlib unittest, offline). Run:

    python3 scripts/test_mass_and_inertia_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
