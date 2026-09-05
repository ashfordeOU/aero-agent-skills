---
name: sandwich-panels
description: "Use when the task is sandwich panel sizing or analysis, honeycomb or foam core selection, face sheet stress or core shear failure checks, face wrinkling, or sandwich bending stiffness and deflection. Design and analyze aerospace sandwich panels: compute the equivalent bending stiffness from the face modulus, face thickness, and core thickness, the face sheet stresses from a bending moment, the core shear stress from a shear load, the face wrinkling stress from the face and core moduli, and the total deflection of a sandwich beam or panel including the core shear contribution. Trigger: sandwich panel, honeycomb core, foam core, face wrinkling, core shear, face stress, sandwich deflection."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: structures
pack: structures
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: composites
  tags: [sandwich, panel, honeycomb, foam, core, shear, wrinkling, deflection, bending, stiffness, composites]
  version: 0.1.0
  author: Aero Agent Skills
---

# Sandwich Panel Design (structures/composites/sandwich-panels)

Use when the task is sandwich panel design or analysis for aerospace
structures: face sheet stress, core shear, face wrinkling, equivalent
bending stiffness, deflection, and honeycomb versus foam core
selection.

## Domain quick reference

- A sandwich panel is two thin, stiff face sheets bonded to a
  lightweight core. The faces carry the bending moment as a
  tension-compression couple; the core carries the transverse shear;
  the large face separation gives high bending stiffness per unit
  weight.
- Face centroid distance d = c + t, overall thickness h = c + 2t,
  where t is one face thickness and c is the core thickness. The
  couple arm is d, not h.
- Equivalent bending stiffness per unit width,
  D = Ef*t*d^2/(2*(1-nu^2)) + Ef*t^3/(6*(1-nu^2)); the first term
  (face couple) dominates when t is small relative to d.
- Face stress from a bending moment M per unit width: sigma = M/(d*t),
  compression on the loaded face, tension on the opposite face.
- Core shear stress from a shear load V per unit width:
  tau = V/(b*d). The core carries essentially all transverse shear;
  a shear margin of tau_allow/|tau| >= 1 is required.
- Face wrinkling is local buckling of a face sheet into the core:
  sigma_wr = 0.5*(Ef*Ec*Gc)^(1/3). Honeycomb cores resist wrinkling
  better than soft foams; foam is more impact tolerant and forms to
  curved tooling.
- Sandwich beam deflection adds a core shear term to the bending
  term: delta = 5*q*L^4/(384*D) + q*L^2/(8*Gc*d) for a simply
  supported beam under a uniform load q per unit width. The shear
  term is significant for soft cores and short spans.
- Core selection: honeycomb wins on specific shear stiffness
  (Gc/rho, typically 3-10x foam); foam wins on impact tolerance,
  moisture immunity, and cost on contoured parts.

## Workflow

1. Collect the configuration: face modulus Ef and poisson ratio nu,
   face thickness t, core thickness c, core modulus Ec, core shear
   modulus Gc, and the loads (moment M, shear V, or distributed load
   q over span L).
2. Compute the couple arm d = c + t and the equivalent bending
   stiffness D with bending_stiffness.
3. Compute the face stresses from the moment with face_stress and
   check them against the face allowable with face_stress_margin.
4. Compute the core shear stress from the shear load with
   core_shear_stress and check the core with core_shear_margin.
5. Check face wrinkling with wrinkling_stress against the face
   allowable (wrinkling is often the limiting face failure mode).
6. Compute the bending and shear deflection terms with
   sandwich_beam_deflection; check the total against the deflection
   requirement.
7. Select the core type with select_core: weight-critical flat
   panels favor honeycomb, impact- or moisture-critical or contoured
   parts favor foam.

## Pitfalls

- Using the overall thickness h instead of the couple arm d in the
  stress and stiffness formulas; the error is large when t is not
  negligible relative to c.
- Ignoring the core shear deflection term for short spans or foam
  cores; it can exceed the bending deflection.
- Checking only face stress and missing face wrinkling, which is
  driven by the core moduli, not the face strength.
- Applying a face allowable to the core shear stress or vice versa;
  the two failure modes use different allowables.
- Treating honeycomb as universally better: moisture intrusion and
  curved tooling favor foam.
- Reading the wrinkling exponent as 1/2 instead of 1/3.

## Behavior contract (gate 3)

The bending stiffness, face stress, core shear, wrinkling, deflection,
margin, and core selection logic is exercised by the gate 3 contract
test: scripts/test_sandwich_panels.py against
scripts/sandwich_panels_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_sandwich_panels.py

## Compliance

- FAR-25 (14 CFR Part 25, US government work, public domain) and
  CS-25 (EASA, free download) frame the transport aeroplane
  structural certification context; both are referenced only,
  summary-not-copy per standards-map.yaml. The formulas here are
  generic sandwich mechanics, not text from either standard.
- compliance: STANDARDS-REF, gated: false.
