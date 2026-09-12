---
name: critical-crack-size-calculation
description: "Use when determine the critical crack size at limit-load and assess residual-strength margin for a structural component per ECSS E-ST-32C clause 7.3: apply linear elastic fracture mechanics to compute the critical crack half-length from material fracture toughness, a stress-intensity geometry factor, and the applied limit stress; derive the part residual-strength at the assumed crack size; compute the margin-of-safety against limit-load failure; and flag any crack at or beyond the critical size as requiring disposition. Supports fracture control programmes that must demonstrate adequate residual-strength under limit loading. Trigger: ecss, e-st-32-structures-scope, fracture-control, critical-crack-size, residual-strength, fracture-toughness, limit-load, margin-of-safety, linear-elastic-fracture-mechanics."
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
  tags: [ecss, e-st-32-structures-scope, fracture-control, critical-crack-size, residual-strength, fracture-toughness, limit-load, margin-of-safety, linear-elastic-fracture-mechanics]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Critical Crack Size at Limit Load (space-systems/ecss/critical-crack-size-calculation)

Use when the task is to determine the critical crack half-length at limit
load and verify that an assumed crack leaves adequate residual strength,
per ECSS E-ST-32C clause 7.3. The assessment links material fracture
toughness (K_IC), part geometry (stress-intensity factor Y), and the
applied limit stress to compute whether the part can sustain the limit
load with the assumed crack present.

## Domain quick reference

- Linear elastic fracture mechanics (LEFM) underpins this calculation.
  The stress-intensity factor K_I = Y · σ · √(π · a) characterises the
  crack-tip field, where Y is a dimensionless geometry correction factor,
  σ is the applied stress, and a is the crack half-length.
- Fracture instability occurs when K_I reaches the material plane-strain
  fracture toughness K_IC. Setting K_I = K_IC and solving for a gives
  the critical crack half-length: a_c = (K_IC / (Y · σ))² / π. A crack
  smaller than a_c will not propagate unstably under the applied load.
- Residual strength is the maximum stress the part can sustain with an
  assumed crack of size a: σ_res = K_IC / (Y · √(π · a)). When a = a_c,
  residual strength exactly equals the applied limit stress (margin = 0).
- Margin of safety MS = σ_res / σ_limit − 1. MS ≥ 0 means the part
  retains sufficient load-carrying capacity (pass); MS < 0 means the
  assumed crack exceeds the critical size and unstable fracture can occur
  at limit load (fail).
- The geometry factor Y must match the crack geometry and loading mode
  (central through-crack, edge crack, surface crack, etc.). Using a wrong
  Y value is the most common source of non-conservative error.

## Workflow

1. Gather material and load data: obtain the material plane-strain
   fracture toughness K_IC (MPa·√m) from a qualified database or test
   report, confirm the limit stress σ_limit (MPa) from the design loads
   document, and select the stress-intensity geometry factor Y appropriate
   to the crack shape, location, and loading direction.
2. Compute the critical crack half-length a_c from the LEFM relation
   a_c = (K_IC / (Y · σ_limit))² / π. Record a_c as the maximum
   allowable crack half-length for the part at limit load.
3. Identify the assumed crack size a_assumed from the fracture control
   plan — this is typically the non-destructive-inspection detection
   threshold or the largest crack that survives the inspection process.
4. Compute the residual strength σ_res = K_IC / (Y · √(π · a_assumed))
   for the assumed crack.
5. Compute the margin of safety MS = σ_res / σ_limit − 1.
6. Evaluate the result: if MS ≥ 0, the part passes the residual strength
   check at limit load; if MS < 0, the assumed crack exceeds the critical
   size and the design requires disposition (redesign, reduce load, use
   tougher material, or tighten the inspection threshold).
7. Record a_c, σ_res, MS, and the basis for each input (material source,
   load document, Y reference) in the fracture control analysis report
   per ECSS E-ST-32C clause 7.3.

## Pitfalls

- Applying a through-crack Y factor (Y = 1.0) to a surface or corner
  crack without correction — surface cracks carry a different effective Y
  under the same loading; using Y = 1.0 unconditionally gives a
  non-conservative critical size for some geometries.
- Using the ultimate stress instead of the limit stress when computing
  a_c — clause 7.3 requires the residual strength check at limit load,
  not ultimate load; substituting ultimate stress produces a smaller a_c
  and a smaller residual strength margin than the requirement demands.
- Treating K_IC as equivalent to K_Ic from a plane-stress specimen or
  from a specimen thickness smaller than 2.5 (K_IC / σ_yield)² — if the
  specimen does not meet the plane-strain size criterion, the measured
  value is not a valid K_IC and will overestimate residual strength.
- Ignoring the interaction between adjacent cracks or between a crack and
  a nearby free edge — these elevate K_I above the single-crack solution
  and reduce a_c; the single-crack formula is valid only when the crack
  is isolated from other stress concentrators.

## Behavior contract (gate 3)

The critical crack size, residual strength, margin of safety, and
error-validation logic are exercised by the gate 3 contract test:
scripts/test_critical_crack_size_calculation.py against
scripts/critical_crack_size_calculation_logic.py (stdlib unittest, offline).
Run: python3 scripts/test_critical_crack_size_calculation.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
- Anchor clause: ECSS E-ST-32C §7.3 (critical crack size at limit load;
  residual strength margin).
