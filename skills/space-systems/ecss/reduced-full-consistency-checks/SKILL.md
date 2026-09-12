---
name: reduced-full-consistency-checks
description: "Use when verify consistency between a reduced structural model and its
  parent full finite element model per ECSS-E-ST-32C clause 5.8: compare total mass,
  centre of gravity, and moments of inertia within the specified tolerance, compute
  Modal Assurance Criterion values for retained interface modes and confirm natural
  frequency agreement, check static stiffness at boundary degrees of freedom, and
  confirm interface load vectors agree within the permitted threshold. Apply at every
  stage where a reduced model replaces the full FEM for coupled loads analysis.
  Trigger: ecss, e-st-32-structures-scope, reduced-model, craig-bampton, mac,
  modal-correlation, fem-consistency, interface-loads, coupled-loads-analysis."
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
  tags: [ecss, e-st-32-structures-scope, reduced-model, craig-bampton, mac, modal-correlation, fem-consistency, interface-loads, coupled-loads-analysis]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Reduced vs Full Model Consistency Checks (space-systems/ecss/reduced-full-consistency-checks)

Use when the task is to verify that a reduced structural model — produced by a fixed-interface normal-mode reduction (Craig-Bampton) or Guyan static condensation — is sufficiently consistent with its parent full finite element model before the reduced model is submitted for a coupled loads analysis cycle.

ECSS-E-ST-32C clause 5.8 requires the supplier to demonstrate this consistency through a defined set of checks prior to delivery of the superelement or reduced boundary condition model to the integrating authority.

## Domain quick reference

- A **full FEM** is the detailed finite element model of a structural item, retaining all internal degrees of freedom (DOF). It is the reference and must be validated independently before reduction.
- A **reduced model** (superelement, Craig-Bampton component mode synthesis model, or Guyan-reduced stiffness/mass) retains only the boundary/interface DOFs and a set of fixed-interface normal modes. All internal DOFs are eliminated by transformation.
- **Consistency** means the reduced model accurately reproduces the dynamic and static behaviour of the full FEM at the interface. Four properties are compared: mass properties, natural frequencies, mode-shape correlation (MAC), and static stiffness at the interface.
- **MAC (Modal Assurance Criterion)**: a scalar in [0, 1] computed from the dot products of paired mode-shape vectors. A value of 1.0 indicates identical shapes; values below the project threshold (commonly 0.9) indicate a poorly paired or missing mode.
- **Tolerances** are project-defined, but ECSS-E-ST-32C clause 5.8 sets default guidance: ≤2% on total mass, ≤3% on natural frequencies for primary modes, MAC ≥ 0.9 for each retained mode, ≤5% on diagonal static stiffness terms. Projects with tighter dynamic environments (e.g. low-frequency primary structure) may impose stricter limits.
- A reduced model that passes all four checks is deemed consistent and may be used in place of the full FEM for the coupled loads analysis cycle. A reduced model that fails any check must be revised before delivery.

## Workflow

1. **Confirm the full FEM baseline is frozen.** The full FEM must carry a released configuration identifier. Do not run consistency checks against a model under active revision; if the full FEM changes, repeat all checks after re-baselining.

2. **Extract and compare mass properties.** From both the full FEM and the reduced model, obtain: total mass, centre of gravity (CG) coordinates (x, y, z), and the six independent inertia tensor components (Ixx, Iyy, Izz, Ixy, Ixz, Iyz) about the reference point. Compute the percentage difference for total mass and each inertia component, and the Euclidean distance between the two CG vectors. Flag any quantity that exceeds the project tolerance. A mass discrepancy above tolerance typically signals missing or duplicated mass in the reduction transformation.

3. **Compare retained natural frequencies.** For each interface mode retained in the reduced model, identify the corresponding mode in the full FEM by frequency proximity. Compute the percentage frequency deviation. Flag pairs whose deviation exceeds the project tolerance. Modes that cannot be paired (no full-FEM mode within a wide search band) must be reported as unmatched.

4. **Compute the MAC matrix for interface modes.** For each pair of (full FEM mode, reduced mode), compute the MAC value using the interface-DOF components of the mode-shape vectors. Construct the full MAC matrix. Flag any diagonal entry below the project MAC threshold. Flag any off-diagonal MAC entry that exceeds the threshold (indicating mode swap or coupling). A diagonal MAC matrix with all entries above threshold demonstrates shape-level consistency.

5. **Compare static stiffness at the interface.** Apply a unit load at each interface DOF in turn and record the resulting displacement. The ratio of applied load to displacement gives the static stiffness for that DOF. Compute the percentage deviation between full FEM and reduced model for each diagonal stiffness term. Flag deviations above the project tolerance. Off-diagonal coupling terms should also be compared where they are non-negligible.

6. **Consolidate findings and issue a consistency statement.** Gather all flags from steps 2–5. A reduced model is consistent only when every check yields no flags. Where flags exist, record the quantity, full-FEM value, reduced-model value, deviation, and applicable tolerance. The consistency statement must identify the model configuration identifiers, check date, and the pass/fail status of each of the four check categories. Deliver the consistency statement alongside the reduced model file.

## Pitfalls

- **Checking frequency only, skipping MAC.** Two modes at nearly identical frequencies may have swapped or hybridised shapes in the reduced model. Frequency agreement without shape verification (MAC) does not confirm consistency; both checks are mandatory.
- **Using loosely-matched full-model modes for MAC.** The MAC must be computed with the same interface-DOF set that the reduction uses. Using all-DOF mode shapes from the full FEM (including internal DOFs not present in the reduced model) produces incorrect MAC values.
- **Ignoring off-diagonal inertia terms.** Products of inertia (Ixy, Ixz, Iyz) are routinely non-zero for asymmetric structures. Omitting them from the comparison can mask a rotation of the inertia ellipsoid in the reduced model.
- **Re-using a previous consistency check after model edits.** If the full FEM or reduction parameters change — even a single property card update — all four checks must be repeated. Outdated consistency statements must not be re-used.
- **Accepting a near-miss with engineering judgement alone.** Deviations above tolerance require a formal deviation record or a revised model, not an informal note. The integrating authority uses the consistency statement as a contractual input to the coupled loads cycle; undocumented deviations invalidate the cycle.

## Behavior contract (gate 3)

The mass-property comparison, MAC computation, frequency comparison, and static-stiffness comparison logic is exercised by the gate 3 contract test:
`scripts/test_reduced_full_consistency_checks.py` against
`scripts/reduced_full_consistency_checks_logic.py` (stdlib unittest, offline). Run:
`python3 scripts/test_reduced_full_consistency_checks.py`

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS-E-ST-32C § 5.8 (Reduced models).
