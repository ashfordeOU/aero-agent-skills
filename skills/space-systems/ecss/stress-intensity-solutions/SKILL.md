---
name: stress-intensity-solutions
description: "Use when determine the applicable stress-intensity-factor K-solution for a crack geometry in a metallic spacecraft structure under ECSS-E-ST-32C clause 7.2.7: categorize the crack into the matching geometry family (surface semi-elliptical, center through, edge through, corner at hole), retrieve the corresponding solution from ESACRACK or an approved fracture-mechanics compendium, evaluate the boundary-correction factors (Newman-Raju, Feddersen, Tada-Paris-Irwin) for the a/c, a/t, and a/W ratios, and verify that linear-elastic fracture-mechanics dominance holds before using K in crack-growth or fracture-allowable calculations. Trigger: ecss, e-st-32-structures-scope, stress-intensity-factor, K-solution, crack-geometry, ESACRACK, fracture-mechanics, Newman-Raju, boundary-correction."
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
  tags: [ecss, e-st-32-structures-scope, stress-intensity-factor, k-solution, crack-geometry, esacrack, fracture-mechanics, newman-raju]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Stress Intensity Factor K-Solutions (space-systems/ecss/stress-intensity-solutions)

Use when the task is selecting and evaluating the applicable K-solution for a
crack geometry per ECSS-E-ST-32C clause 7.2.7 — categorizing the crack
geometry, retrieving the matched solution from ESACRACK or an approved
compendium, and computing the stress intensity factor with the correct
boundary-correction factors before it feeds into crack-growth or fracture
assessment.

## Domain quick reference

- Clause 7.2.7 requires that the K-solution used in a fracture-control
  analysis be taken from ESACRACK or an equivalent peer-reviewed compendium,
  matched to the actual crack geometry and structural boundary conditions.
  The solution is not interchangeable between geometry families.
- Crack geometries are categorized into four principal families: surface
  semi-elliptical crack in a plate (uses Newman-Raju 1984 correction factors),
  center through crack in a plate (Feddersen finite-width correction), single
  edge through crack in a plate (Tada-Paris-Irwin polynomial), and quarter-
  elliptical corner crack at a circular hole (Kt-augmented solution). Each
  family has distinct governing parameters: a/c and a/t for surface cracks;
  a/W for through and edge cracks; a/R and a/t for corner-at-hole cracks.
- K is expressed in stress × length^0.5 units consistent with the fracture
  toughness K_Ic from the material allowables database. The Mode-I opening
  solution covers the vast majority of spacecraft structural cracks under
  tension-dominated loading; Modes II and III are secondary contributors and
  require separate mixed-mode assessment outside this leaf.
- The linear-elastic fracture-mechanics (LEFM) dominance condition must be
  checked: the plastic zone radius r_p = (1/(2π)) * (K/σ_ys)^2 must be small
  relative to the crack dimension a and the remaining ligament. When this
  condition is not met, an elastic-plastic correction (J-integral or CTOD
  approach) supersedes the K solution.

## Workflow

1. Categorize the crack geometry from the inspection record or initial-flaw
   assumption: identify the crack type (surface, through, edge, or corner),
   the relevant dimensions (a, c, t, W, R), and the primary loading mode
   (tension, bending, or combined). Reject any geometry whose parameters fall
   outside the validity bounds of the available K-solutions.
2. Match the crack geometry to the appropriate K-solution family. Select the
   corresponding formula and correction-factor set from ESACRACK or the
   approved compendium entry. Record the solution reference (author, year,
   equation number) in the fracture-control analysis document.
3. Evaluate the boundary-correction factors for the specific a/c, a/t, and
   a/W ratios at each crack size step of interest:
   - Surface semi-elliptical: compute the elliptic shape factor Q from the
     Newman-Raju approximation (Q = 1 + 1.464*(a/c)^1.65 for a/c ≤ 1), then
     evaluate the angular-correction terms M1, M2, M3 and the angular function
     f_phi at the parametric angle of interest (deepest point phi=90°, surface
     ends phi=0°).
   - Center through crack (finite plate): apply the Feddersen secant correction
     K = sigma * sqrt(pi*a * sec(pi*a/(2*W))). Verify a < W.
   - Edge through crack: apply the Tada-Paris-Irwin polynomial F(a/W) valid
     for a/W < 0.6; flag the solution if a/W exceeds this limit.
   - Corner crack at hole: apply the Kt-augmented formula with effective stress
     concentration Kt_eff = 3*(1 - a/(a+R)), reduced by the empirical factor
     0.97.
4. Compute K = sigma * F * sqrt(pi*a/Q) (or the geometry-specific form) at
   each crack size. Confirm K is positive and increasing with crack size for
   tension loading; a non-monotonic result signals a parameter or formula error.
5. Verify LEFM dominance: check that the plastic zone radius is small relative
   to the crack dimension and the remaining ligament. If the LEFM condition is
   violated, flag the result and escalate to an elastic-plastic method.
6. Record the selected K-solution reference, the computed K vs. crack-size
   table, the validity bounds checked, and the LEFM dominance status in the
   fracture-control analysis note.

## Pitfalls

- Applying a through-crack K-solution to a surface crack or vice versa —
  the through-crack formula treats the crack as spanning the full thickness
  (stress intensity is lower per unit depth than a surface crack where the
  crack front shape factor Q applies). Always match the solution to the actual
  crack front geometry from the inspection or initial-flaw assumption.
- Ignoring the a/W validity bound for the edge-crack polynomial — the
  Tada-Paris-Irwin formula is calibrated for a/W < 0.6 and diverges from
  the exact solution above that ratio. Use a full-range formula or a handbook
  table when a/W ≥ 0.6.
- Using K at phi=0° (surface intercept) as the governing point without
  checking phi=90° (deepest point) — for many surface-crack geometries the
  deepest point governs the crack-growth life, while the surface-end point
  governs when the crack is very shallow (a/t small) and wide (a/c small).
  Both points should be evaluated and the critical one selected.
- Omitting the LEFM check and applying K beyond the small-scale yielding
  limit — fracture toughness K_Ic values from test data already embed LEFM
  assumptions; applying them to a situation where the plastic zone is
  significant leads to unconservative life estimates.

## Behavior contract (gate 3)

The geometry categorization, shape-factor evaluation, K computation, and LEFM
dominance check logic is exercised by the gate 3 contract test:
scripts/test_stress_intensity_solutions.py against
scripts/stress_intensity_solutions_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_stress_intensity_solutions.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
