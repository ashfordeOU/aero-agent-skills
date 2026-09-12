---
name: copc-metallic-liner
description: "Use when verify a composite overwrapped pressure container (COPC) with metallic liner per ECSS-E-ST-32 clause 4.5.2: confirm the liner remains elastic at proof pressure, compute the margin-of-safety on liner hoop stress at maximum expected operating pressure, validate proof and burst pressure factors against required minimums, demonstrate leak-before-burst by confirming the fracture-mechanics critical flaw depth exceeds the liner wall thickness, and check the fatigue-cycle budget against a cycle-life scatter factor of at least four before pressurised qualification is declared. Trigger: ecss, e-st-32-structures-scope, copc, metallic-liner, pressure-vessel, leak-before-burst, fatigue-cycle-budget, fracture-mechanics, proof-pressure, burst-factor."
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
  tags: [ecss, e-st-32-structures-scope, copc, metallic-liner, pressure-vessel, leak-before-burst, pressure-cycle-fatigue]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — COPC with Metallic Liner (space-systems/ecss/copc-metallic-liner)

Use when the task is the structural verification of a Composite Overwrapped
Pressure Container (COPC) with a metallic liner under ECSS-E-ST-32 clause
4.5.2 — confirming that the liner material is recognized, the proof and burst
pressure factors meet the required minimums, the liner remains elastic at
proof pressure, the fatigue cycle budget is covered by a scatter factor of at
least four, and leak-before-burst is demonstrated by fracture mechanics before
pressurised qualification is declared.

## Domain quick reference

- A COPC consists of a metallic liner that provides the gas-tight barrier and
  a composite overwrap that carries the primary structural load. The liner and
  overwrap interact through hoop load-sharing; for verification purposes the
  liner hoop stress is computed via the thin-wall formula (σ = P × r / t) using
  the liner's own geometry, valid only when t/r < 0.1.
- The metallic liner must remain elastic — hoop stress strictly below yield
  stress — at proof pressure. Proof pressure = MEOP × proof factor (minimum
  1.1 per clause 4.5.2). A liner that yields at proof is no longer a reliable
  leak-tight barrier and the vessel fails this gate before any further check is
  applied.
- Burst pressure = MEOP × burst factor (minimum 1.5). The complete vessel
  (liner and overwrap combined) must withstand the required burst pressure
  without rupture. Demonstrated burst capacity is compared against the required
  value and a finding is raised on any shortfall.
- Leak-before-burst (LBB) is verified via fracture mechanics: for a
  semi-elliptical surface crack on the liner inner wall, the critical flaw
  half-depth a_c = (K_Ic / (Y × σ_MEOP))² / π. LBB is demonstrated when
  a_c exceeds the liner wall thickness, meaning a crack propagates through-wall
  and produces a detectable leak before reaching fracture-critical size.
- Fatigue cycle life is verified by checking that the demonstrated or analyzed
  allowable cycle count, divided by a scatter factor of at least four (per
  ECSS-E-ST-32 clause 4.5.2), covers the mission design cycle count.
- Recognized metallic liner materials include aluminium alloys (2014, 2219,
  6061), titanium alloys (Ti-6Al-4V, CP-4), stainless steels (316L, 321), and
  nickel superalloys (Inconel 718). Unrecognized materials require separate
  material qualification before entry into this assessment.

## Workflow

1. Confirm the liner material is in the recognized set. Reject any
   unrecognized material with a clear finding; do not proceed with fabricated
   material properties.
2. Verify the proof pressure factor (proof pressure / MEOP) meets the
   minimum of 1.1. Record the shortfall if it does not.
3. Verify the burst pressure factor (required burst pressure / MEOP) meets
   the minimum of 1.5. Record the shortfall if it does not.
4. Compute the liner hoop stress at proof pressure using the thin-wall
   formula (σ = P × r / t). First check that t/r < 0.1; if not, flag the
   thin-wall assumption as violated and require thick-wall analysis before
   continuing.
5. Compare the liner hoop stress at proof pressure against the liner yield
   stress. The liner must be strictly elastic (stress < yield). A yield margin
   at or below zero is a blocking finding that must be resolved before the
   vessel enters qualification.
6. Compute the liner hoop stress at MEOP and check the margin of safety
   (yield / hoop − 1) is positive. A negative margin at MEOP is a finding
   even when the liner remains elastic at proof, because MEOP represents the
   sustained operating condition.
7. Demonstrate leak-before-burst: compute a_c using the liner's fracture
   toughness K_Ic and hoop stress at MEOP. Confirm a_c exceeds the liner wall
   thickness. If not, flag LBB as undemonstrated; the vessel requires either a
   liner material change or geometry modification before qualification.
8. Check the fatigue cycle budget: divide the demonstrated or analyzed
   allowable cycle count by the scatter factor (minimum 4.0) and confirm the
   result is at or above the mission design cycle count. Flag any deficit.
9. Confirm the vessel's demonstrated or computed burst pressure meets or
   exceeds the required burst pressure (MEOP × burst factor).
10. Aggregate all findings. The COPC metallic liner verification is closed
    only when the findings list is empty across all nine checks above.

## Pitfalls

- Applying the thin-wall formula without checking the t/r ratio first. When
  t/r ≥ 0.1, the thin-wall stress is unconservative and must be replaced by a
  thick-wall or finite-element result before any elasticity check is valid.
- Confusing proof-pressure elasticity with MEOP margin. ECSS-E-ST-32 clause
  4.5.2 requires the liner to remain elastic at proof pressure; a separate
  margin of safety check at MEOP is also required because MEOP represents the
  sustained operating condition.
- Reversing the LBB condition. LBB is satisfied when a_c is larger than the
  wall thickness, not smaller. A larger critical flaw depth means the crack
  must grow further before becoming unstable — and since it goes through-wall
  first, it leaks rather than bursting.
- Using a fatigue scatter factor below four. ECSS-E-ST-32 clause 4.5.2 sets a
  minimum scatter factor of four for metallic liner fatigue life; a scatter
  factor of two or three is not compliant even if derived from test data.
- Treating burst capability as demonstrated by analysis alone when a physical
  burst test is required by the project acceptance plan. Confirm whether the
  acceptance plan requires a physical burst test or accepts a certified burst
  analysis before closing this finding.

## Behavior contract (gate 3)

All eight individual checks and the top-level assessment are exercised by the
gate 3 contract test: scripts/test_copc_metallic_liner.py against
scripts/copc_metallic_liner_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_copc_metallic_liner.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
