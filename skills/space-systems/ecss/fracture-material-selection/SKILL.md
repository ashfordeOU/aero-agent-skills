---
name: fracture-material-selection
description: "Use when determine material acceptability for fracture control per ECSS-Q-ST-70-36: screen each candidate against the prohibited materials list, evaluate the stress-corrosion cracking (SCC) susceptibility code (A through D), check the KIscc/KIc ratio against the service environment (dry, moist, propellant, or aqueous), verify that fracture-critical parts meet the minimum plane-strain fracture toughness floor, and derive a verdict of ACCEPT, CONDITIONAL, or REJECT with supporting findings. Trigger: ecss, e-st-32-structures-scope, q-st-70-36, fracture-material-selection, stress-corrosion-cracking, scc-susceptibility, fracture-toughness, kic, kiscc, fracture-critical."
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
  tags: [ecss, e-st-32-structures-scope, q-st-70-36, fracture-material-selection, stress-corrosion-cracking, scc-susceptibility, fracture-toughness, kic, kiscc, fracture-critical]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Fracture Control — Material Selection (space-systems/ecss/fracture-material-selection)

Use when the task is to determine whether a candidate material is acceptable for a
fracture-controlled application under ECSS-Q-ST-70-36 — screening the prohibited list,
assigning and evaluating SCC susceptibility codes, checking the KIscc/KIc ratio against
the service environment, and verifying the fracture toughness floor for fracture-critical
parts.

## Domain quick reference

- ECSS-Q-ST-70-36 establishes material selection requirements for components under
  fracture control. Materials are assigned an SCC susceptibility code — A (not
  susceptible), B (low), C (moderate), or D (high) — based on test data and material
  characterisation. The code drives which service environments permit the material.
- The KIscc/KIc ratio is the primary quantitative marker of SCC severity. KIscc is the
  threshold stress intensity below which a sharp crack does not propagate under sustained
  load in the service environment; KIc is the plane-strain fracture toughness. A ratio
  below 0.10 means the material cannot maintain a safe service stress around a crack and
  is rejected. A ratio between 0.10 and 0.25 triggers conditional acceptance: the design
  stress must remain below the KIscc-derived allowable and sustained-load test data must
  be on record.
- Service environment governs SCC code permissibility. Code D (high susceptibility) is
  not permitted in moist, propellant, or aqueous environments. Code C (moderate) in those
  environments requires stress limitation to 75 % Fty and SCC qualification test data.
  Code B (low) in propellant or aqueous environments requires sustained-stress SCC
  confirmation. Dry environments relax the SCC code constraint, but the KIscc/KIc check
  still applies when ratio data are available.
- Fracture-critical parts require a minimum KIc of 22 MPa√m. Non-fracture-critical parts
  have no KIc floor under this procedure but must still pass the prohibited-list and SCC
  checks.

## Workflow

1. Confirm whether the material appears on the Q-ST-70-36 prohibited materials list
   (Appendix A). If so, reject immediately without further evaluation.
2. Record the material's SCC susceptibility code (A, B, C, or D) from the material
   datasheet or test programme. If the code is absent, flag the gap before proceeding.
3. If a KIscc value is available, compute the KIscc/KIc ratio. Reject if the ratio is
   below 0.10. Flag conditional acceptance if the ratio is between 0.10 and 0.25,
   requiring stress restriction and sustained-load SCC test data.
4. Apply the SCC code rule for the stated service environment: reject code D in any
   corrosive environment; require stress limitation and test data for code C; require SCC
   confirmation testing for code B in propellant or aqueous environments.
5. For fracture-critical parts, verify that KIc meets or exceeds 22 MPa√m. Flag a
   rejection if it does not.
6. In a corrosive environment with an SCC code of B, C, or D, confirm that a KIscc value
   is on record. Flag a rejection if KIscc is missing, because the margin cannot be
   verified.
7. Aggregate all findings. A material is acceptable only when the prohibited-list check,
   ratio check, environment check, and fracture-critical toughness check are all clear.
   Findings involving stress limitation or test evidence produce conditional acceptance.

## Pitfalls

- Relying on the SCC code alone without checking the KIscc/KIc ratio in corrosive
  environments — code B in aqueous service may still fail the ratio check even when the
  code nominally permits conditional use.
- Omitting the prohibited-list check and treating a ratio-passing result as acceptance —
  the prohibited list overrides all other checks unconditionally.
- Applying the 22 MPa√m KIc floor to non-fracture-critical parts — this floor is scoped
  to parts designated fracture-critical in the fracture-control plan only.
- Treating a missing KIscc entry as "no SCC concern" in a corrosive environment — the
  absence of KIscc data for a susceptible-code material in a corrosive service means the
  margin cannot be verified, not that the margin is adequate.
- Accepting a code-D material in a dry environment on the basis that no aqueous concern
  applies — dry service relieves the environment restriction for code D, but the
  KIscc/KIc check still applies if ratio data exist.

## Behavior contract (gate 3)

The prohibited-list, KIscc/KIc ratio, SCC-code environment, and fracture-critical
toughness logic is exercised by the gate 3 contract test:
scripts/test_fracture_material_selection.py against
scripts/fracture_material_selection_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_fracture_material_selection.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase per
  standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
