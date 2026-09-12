---
name: stress-free-thermoelastic-check
description: "Use when verify that a structural finite element model handles a uniform
  temperature change correctly by producing negligible stress under stress-free boundary
  conditions. Apply a uniform ΔT across all elements, confirm temperature uniformity
  of the applied thermal load, compare each element's stress residual against the
  expected E·α·ΔT scale, and confirm that nodal displacements match the free thermal
  expansion. Non-zero stress indicates a modelling error such as mismatched coefficient
  of thermal expansion, an unintended kinematic constraint, or inconsistent material
  property assignment. This check is required to validate the thermoelastic response
  of the FEM before thermal load cases are accepted. Trigger: ecss, e-st-32-structures-scope,
  thermoelastic, fem-verification, stress-free, thermal-expansion, cte, fem-validation,
  temperature-uniformity."
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
  tags: [ecss, e-st-32-structures-scope, thermoelastic, fem-verification, stress-free, thermal-expansion, cte, fem-validation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structural Engineering — Stress-Free Thermoelastic Deformation Check (space-systems/ecss/stress-free-thermoelastic-check)

Use when the task is to verify that the finite element model correctly
represents free thermal expansion under a uniform temperature change, per
ECSS-E-ST-32C §5.6. The check confirms that no spurious stress develops
in an unconstrained body subjected to a uniform ΔT, and that nodal
displacements match the expected free-expansion values.

## Domain quick reference

- A body free from mechanical constraints and subjected to a spatially
  uniform temperature change ΔT should develop only thermal strains
  ε_thermal = α·ΔT in each principal direction; stress must be zero
  everywhere because no constraint prevents free expansion.
- If the FEM produces non-zero stress under this load case, a modelling
  defect is present. Common causes are: a coefficient of thermal expansion
  (CTE) assigned to one element that differs from its neighbours,
  a residual kinematic constraint (e.g. an inadvertently fixed degree of
  freedom), or a material property inconsistency introduced at a
  multi-material interface.
- The stress residual is evaluated against the characteristic
  thermoelastic stress scale S = E·α·|ΔT|. Any element stress that
  exceeds a small fraction of S (typically 10⁻⁶ × S) indicates a
  modelling error.
- Displacement at each node must match the analytical free-expansion
  value d = α·ΔT·L_ref (projected along the relevant axis) within the
  model's numerical precision tolerance.
- Temperature uniformity must also be verified: if the applied thermal
  load itself is not spatially uniform, the check is invalid and the
  load definition must be corrected before proceeding.

## Workflow

1. Define a thermal load case in which every element is assigned the
   same temperature change ΔT. Apply stress-free boundary conditions:
   remove all mechanical constraints except the minimum set needed to
   suppress rigid-body motion (typically three translational and three
   rotational constraints at a single reference node, or equivalent).
2. Verify temperature uniformity: extract the temperature assigned to
   each element and confirm that the spread (max − min) is below the
   accepted uniformity tolerance (default 0.01 °C). A non-uniform
   temperature field invalidates the check and must be corrected.
3. Run the FEM solution and extract element stresses. For each element,
   compute the characteristic thermoelastic stress scale S = E·α·|ΔT|
   and compare the maximum principal stress component against the
   fraction threshold (default fraction = 10⁻⁶). Flag every element
   where max(|σ_xx|, |σ_yy|, |σ_zz|) > fraction × S.
4. Extract nodal displacements and compare each node's computed
   displacement against the analytically expected free-expansion
   displacement. Flag every node where the Euclidean residual exceeds
   the displacement tolerance (default 10⁻⁶ m or fraction of
   characteristic length).
5. Aggregate all element and node findings. The check is passed only
   when: (a) temperature uniformity is satisfied, (b) no element exceeds
   the stress residual threshold, and (c) no node exceeds the
   displacement residual threshold.
6. Document the ΔT applied, the stress fraction used, the number of
   elements and nodes checked, and any failures with their element or
   node IDs. A failed check requires model correction followed by a
   repeat run before the thermal load cases are accepted.

## Pitfalls

- Retaining too many kinematic constraints when setting up the
  stress-free case: even one unnecessarily fixed translational degree of
  freedom will generate reactions that produce non-zero stress and cause
  every element in the constrained region to fail the check
  spuriously. The boundary condition for this test must allow free
  thermal breathing of the entire mesh.
- Using a non-uniform applied temperature and attributing the resulting
  stress to a mesh defect: if the load itself has spatial gradients
  the check is meaningless. Verify temperature uniformity first; do not
  proceed to stress evaluation if the uniformity check fails.
- Setting the stress fraction threshold too loosely (e.g. 0.1): a
  10 % tolerance masks real CTE mismatches at material interfaces.
  The recommended threshold of 10⁻⁶ × E·α·|ΔT| is consistent with
  typical FEM double-precision arithmetic noise floors.
- Comparing absolute displacements without accounting for the reference
  rigid-body suppression point: the expected free-expansion displacement
  is measured relative to the constrained reference node, not to the
  undeformed origin. Mis-referencing inflates the residual at every node.

## Behavior contract (gate 3)

The temperature-uniformity, element-stress, and displacement-residual
logic is exercised by the gate 3 contract test:
scripts/test_stress_free_thermoelastic_check.py against
scripts/stress_free_thermoelastic_check_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_stress_free_thermoelastic_check.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
