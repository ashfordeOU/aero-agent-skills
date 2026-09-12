---
name: metallic-pressure-vessel
description: "Use when evaluate the development approach and verify the structural integrity of a metallic pressure vessel (MPV) per ECSS-E-ST-32C clause 4.3.2: determine whether the vessel qualifies under the safe-life approach (no crack reaches critical size over mission life) or the leak-before-burst approach (any crack grows through the wall and leaks before causing fast fracture), compute qualification and acceptance test pressures from the MEOP, check burst and proof factors against minimum requirements, and verify the safe-life fatigue margin against the required scatter factor. Trigger: ecss, e-st-32-structures-scope, metallic-pressure-vessel, safe-life, leak-before-burst, fracture-mechanics, proof-pressure, burst-pressure, qualification-test, acceptance-test."
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
  tags: [ecss, e-st-32-structures-scope, metallic-pressure-vessel, safe-life, leak-before-burst, fracture-mechanics, proof-pressure, burst-pressure]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Metallic Pressure Vessel (space-systems/ecss/metallic-pressure-vessel)

Use when the task is to evaluate the development approach for a metallic
pressure vessel (MPV) under ECSS-E-ST-32C clause 4.3.2 — selecting between
safe-life and leak-before-burst (LBB) strategies, computing and checking
qualification and acceptance test pressures, and verifying burst, proof, and
fatigue margins against the minimum required factors.

## Domain quick reference

- ECSS-E-ST-32C §4.3.2 recognises two MPV development approaches: **safe-life**
  and **leak-before-burst (LBB)**. The approach is chosen on the basis of the
  material fracture toughness, wall thickness, and the operating hoop stress.
- **Safe-life**: The vessel is shown, by fracture-mechanics analysis, that no
  initial crack (of the inspection-detectable size) will grow to the critical
  size that triggers fast fracture within the design service life, including a
  minimum scatter factor of 4 on cycles to failure.
- **LBB**: Applicable when the critical crack size (size at which fast fracture
  initiates) exceeds the wall thickness — meaning any crack will penetrate the
  wall and produce a detectable leak before it can cause a burst. The LBB
  condition is: a_c = (K_Ic / (Y · σ))² / π > t, where K_Ic is the
  plane-strain fracture toughness, Y is the geometry correction factor,
  σ is the hoop stress at MEOP, and t is the wall thickness.
- **Test pressures** are multiples of the Maximum Expected Operating Pressure
  (MEOP): acceptance proof = 1.1 × MEOP; qualification proof = 1.5 × MEOP;
  qualification burst = 2.0 × MEOP. The burst test is destructive and is
  performed on a qualification article only.
- The minimum burst factor (2.0) must be demonstrated by test on the
  qualification article. Proof tests on flight articles use the acceptance
  proof factor (1.1 × MEOP) and must show no permanent deformation.
- The thin-wall hoop stress approximation σ = p · R / t is valid only for
  R/t ≥ 10; below that, use the Lamé thick-wall equations instead.

## Workflow

1. **Gather inputs**: MEOP, mean vessel radius, wall thickness, material yield
   strength, fracture toughness K_Ic, design-life load cycles, and (if LBB is
   being assessed) the geometry correction factor Y for the assumed crack shape.
2. **Compute hoop stress**: σ = p · R / t at MEOP, after verifying R/t ≥ 10
   for the thin-wall approximation to apply.
3. **Check yield at MEOP**: σ / σ_y ≤ 1.0; flag if the vessel yields under
   operating pressure.
4. **Select development approach**: compute the critical crack half-length
   a_c = (K_Ic / (Y · σ))² / π. If a_c > t the LBB condition is met and the
   LBB approach is applicable; otherwise use safe-life.
5. **Safe-life path**: verify cycles_to_failure / applied_cycles ≥ 4 (scatter
   factor). If the margin is negative, the design service life must be reduced
   or the vessel redesigned.
6. **Compute test pressures**: for the acceptance test, proof = 1.1 × MEOP;
   for the qualification test, proof = 1.5 × MEOP and burst = 2.0 × MEOP.
7. **Check burst and proof margins**: confirm the vessel's predicted or tested
   burst pressure ≥ 2.0 × MEOP (qualification) and proof pressure ≥ required
   factor × MEOP for the relevant test type.
8. **Aggregate compliance**: a vessel is MPV-compliant when the approach is
   valid, the yield check passes, the fatigue or LBB margin is satisfied, and
   all test pressures meet their minimum factors.

## Pitfalls

- Applying the LBB approach when the vessel material has low fracture toughness
  relative to its operating stress — a low K_Ic gives a small a_c that may be
  less than the wall thickness, making LBB invalid; check explicitly.
- Using the thin-wall hoop stress formula when R/t < 10 — the thin-wall
  approximation underestimates peak stress in thick-walled vessels; use Lamé
  equations in that regime.
- Confusing the scatter factor with a factor of safety on stress — the safe-life
  scatter factor of 4 applies to cycles (life), not to load; halving the applied
  stress does not halve the scatter factor requirement.
- Setting acceptance and qualification proof pressures to the same value —
  acceptance proof = 1.1 × MEOP while qualification proof = 1.5 × MEOP; using
  the lower value for qualification leaves the qualification burst margin untested.
- Omitting the yield check at MEOP — a vessel that yields at operating pressure
  violates the no-permanent-deformation requirement regardless of burst margin.

## Behavior contract (gate 3)

The hoop-stress, LBB applicability, development-approach selection, test-pressure
calculation, burst/proof margin, and safe-life margin logic is exercised by the
gate 3 contract test:
scripts/test_metallic_pressure_vessel.py against
scripts/metallic_pressure_vessel_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_metallic_pressure_vessel.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
