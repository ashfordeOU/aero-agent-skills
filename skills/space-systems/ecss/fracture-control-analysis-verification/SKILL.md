---
name: fracture-control-analysis-verification
description: "Use when verify fracture control analysis compliance for a structural part per ECSS-E-ST-32-01 clause 4.6.2.9: screen the part for fracture criticality based on failure consequence, compute the mode-I stress intensity factor and compare it against material fracture toughness (KIC), confirm crack growth life satisfies the required life factor (4x for unpressurized, 2x for pressurized structures), verify the assumed initial flaw size is at or above the NDE detection limit, and check residual strength of the cracked structure against the required limit load. Aggregate all check results into a single pass/fail verdict. Apply to fracture-critical primary and secondary structural elements in spacecraft and launch vehicles. Trigger: ecss, e-st-32-01, fracture-control, fracture-toughness, crack-growth, damage-tolerance, stress-intensity-factor, residual-strength, nde-flaw-size, e-st-32-structures-scope."
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
  tags: [ecss, e-st-32-01, fracture-control, fracture-toughness, crack-growth, damage-tolerance, stress-intensity-factor, residual-strength, nde-flaw-size, e-st-32-structures-scope]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Fracture Control Analysis Verification (space-systems/ecss/fracture-control-analysis-verification)

Use when the task is the fracture control analysis verification of a structural
part per ECSS-E-ST-32-01 clause 4.6.2.9 — screening for fracture criticality,
computing stress intensity, verifying life factors and residual strength, and
confirming that initial flaw assumptions are conservative relative to the NDE
detection capability.

## Domain quick reference

- ECSS-E-ST-32-01 clause 4.6.2.9 requires that every structural part
  carrying a consequence of catastrophic fracture failure shall be
  subjected to a fracture control analysis. Parts are categorized as
  fracture-critical (FC) or non-fracture-critical (NFC) based on whether
  their fracture failure could lead to loss of mission, spacecraft, crew,
  or a pressurized system. NFC parts do not require fracture control analysis.
- For fracture-critical parts, the analysis verifies four linked checks:
  (1) stress intensity factor K must remain below material fracture
  toughness KIC under the applied loads; (2) the crack growth life under
  cyclic loading must equal or exceed the required life factor times the
  design life (4x for unpressurized structures, 2x for pressurized
  structures); (3) the assumed initial flaw size must be at or above the
  NDE detection limit so the assumption is conservative; (4) the residual
  strength of the structure with the limiting crack must meet or exceed
  the required load level.
- The mode-I stress intensity factor is computed as
  K = F × σ × √(π × a), where F is a geometry (beta) factor, σ is the
  nominal applied stress, and a is the crack half-length. The critical
  crack size (crack half-length at which K = KIC) is
  a_crit = (1/π) × (KIC / (F × σ))².
- Crack growth rate per cycle is described by the Paris relation:
  da/dN = C × (ΔK)^m, where C and m are material constants derived from
  coupon data.

## Workflow

1. Identify every structural part under review and record its failure
   consequence (e.g., loss of mission, loss of crew, degraded
   performance). Categorize each part as fracture-critical or
   non-fracture-critical. Non-fracture-critical parts exit the workflow
   at this step; no further fracture control analysis is required for them.
2. For each fracture-critical part, collect: applied nominal stress (σ),
   geometry factor (F), material fracture toughness (KIC), assumed initial
   crack half-length (a_0), NDE detection limit, design life and structure
   type, crack growth material constants (C, m), and residual strength
   from the cracked-section analysis.
3. Compute the mode-I stress intensity factor K = F × σ × √(π × a_0).
   Compare K against KIC. If K ≥ KIC the part fails the toughness check
   immediately; record the exceedance and stop — no further checks are
   meaningful for this load case.
4. Verify the life factor: determine the required life (design_life ×
   life_factor_requirement) from the structure type, and confirm that the
   crack growth analysis demonstrates the crack does not reach the critical
   size within that required life. Flag a fail if the analyzed life is less
   than the required life.
5. Verify the NDE conservatism: confirm that the assumed initial flaw
   size used in the crack growth analysis is at or above the NDE detection
   limit. An assumed flaw size smaller than the detection limit is
   non-conservative because the NDE cannot guarantee the structure is
   free of flaws larger than the detection limit; flag this as a fail.
6. Verify residual strength: confirm that the residual strength of the
   cracked structure (from linear elastic fracture mechanics or test) is
   not less than the required limit load times any applicable safety factor.
7. Aggregate findings: the part is compliant only when all four checks
   (toughness, life factor, NDE conservatism, residual strength) pass.
   Report each check with its margin; a single fail makes the part
   non-compliant with fracture control requirements.

## Pitfalls

- Skipping the fracture criticality categorization step and applying
  fracture control analysis to every part — this wastes effort and
  dilutes attention. Equally, skipping the categorization and assuming
  parts are non-fracture-critical without evidence is a finding, not a
  shortcut.
- Using a geometry factor F = 1.0 for all geometries — the geometry
  factor depends on crack shape, part geometry, and loading mode. Applying
  a flat 1.0 is non-conservative for geometries with stress concentrations
  or surface cracks.
- Treating the life factor requirement as a simple check on total life
  rather than on crack growth life from the initial assumed flaw — the
  requirement is that the structure survives the required number of design
  lives before the crack reaches critical size, not that the structure
  survives the design life under monotonic load.
- Choosing an assumed initial flaw size below the NDE detection limit —
  the analysis must assume the worst flaw that the inspection program
  cannot reliably detect. Using a smaller flaw makes the crack growth
  life appear longer than it conservatively should be.
- Reporting residual strength without specifying which crack size was
  assumed — residual strength degrades as crack length grows; the check
  must be performed at the end-of-life crack size, not the initial flaw.

## Behavior contract (gate 3)

The fracture criticality screening, life factor, stress intensity,
NDE detectability, residual strength, and full compliance aggregation
logic is exercised by the gate 3 contract test:
scripts/test_fracture_control_analysis_verification.py against
scripts/fracture_control_analysis_verification_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_fracture_control_analysis_verification.py

## Compliance

- ECSS standards are freely downloadable (ESA); cited as anchor only,
  paraphrased — no verbatim text reproduced.
- compliance: STANDARDS-REF, gated: false.
