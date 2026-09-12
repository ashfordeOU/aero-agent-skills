---
name: thermo-elastic-hygrothermal-analysis
description: "Use when verify thermo-elastic and hygrothermal stress/strain levels in a spacecraft structure under ECSS-E-ST-32C clause 4.6.2.11: categorize the load case as thermal-only, hygral-only, or combined; compute free thermal and hygral strains for each structural member or laminate ply; apply the appropriate restraint factor to obtain the induced thermal stress; aggregate hygrothermal force and moment resultants for composite laminates via classical laminate theory; and compute margins of safety against allowable stress and strain limits to confirm compliance. Trigger: ecss, e-st-32-structures-scope, thermo-elastic, hygrothermal, thermal-stress, laminate-hygrothermal-response, CTE, CME, composite-laminate, margin-of-safety."
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
  tags: [ecss, e-st-32-structures-scope, thermo-elastic, hygrothermal, thermal-stress, laminate-hygrothermal-response, CTE, CME, composite-laminate, margin-of-safety]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Thermo-elastic and Hygrothermal Analysis (space-systems/ecss/thermo-elastic-hygrothermal-analysis)

Use when the task is verifying thermo-elastic and hygrothermal stress and
strain levels in spacecraft structural members or composite laminates under
ECSS-E-ST-32C clause 4.6.2.11 — determining free thermal and hygral strains,
computing induced stresses from structural restraint, aggregating hygrothermal
resultants for laminate plies, and checking margins of safety against
allowable limits.

## Domain quick reference

- Thermal strain is the product of the coefficient of thermal expansion (CTE,
  α) and the temperature change ΔT. For an unconstrained member this strain
  produces no stress; for a restrained member the mechanical strain is the
  negative of the free thermal strain, producing a compressive thermal stress
  when ΔT is positive.
- A restraint factor R (0 = free, 1 = fully constrained) linearly scales
  the induced stress: σ_th = −R · E · α · ΔT. Most real joints fall between
  these extremes; an assumed R = 1.0 is conservative.
- Moisture expansion in polymer-matrix composites is governed by the
  coefficient of moisture expansion (CME, β). The hygral free strain is
  β · ΔM, where ΔM is the absorbed moisture mass fraction change. Thermal and
  hygral strains are additive; the combined hygrothermal free strain is
  α · ΔT + β · ΔM.
- For composite laminates the hygrothermal effect is expressed as in-plane
  force resultants N and bending moment resultants M per unit width, obtained
  by summing Q₁₁ · (α · ΔT + β · ΔM) · t over each ply (for N) and
  weighting by the ply mid-plane offset z (for M). A symmetric laminate has
  M = 0; an asymmetric laminate couples in-plane loads into bending and must
  be checked for both resultants.
- Margins of safety are computed as MoS = (allowable / |demand|) − 1.
  A MoS ≥ 0 is a pass; MoS < 0 is a failure requiring design action.

## Workflow

1. Categorize the load case for each structural element or laminate as
   thermal-only (ΔM = 0), hygral-only (ΔT = 0), or combined (both non-zero);
   elements with ΔT = 0 and ΔM = 0 carry no hygrothermal load and are excluded
   from further analysis.
2. For each isotropic or orthotropic structural member, compute the free
   thermal strain ε_th = α · ΔT and, if moisture is present, the free hygral
   strain ε_h = β · ΔM. Record the combined free strain ε_free = ε_th + ε_h.
3. Determine the restraint factor R for each member from boundary conditions
   (0 = fully free, 1 = fully fixed). Apply it to compute the induced thermal
   stress: σ = −R · E · α · ΔT. If moisture-induced stress is required,
   similarly compute σ_h = −R · E · β · ΔM.
4. For composite laminates, assemble the ply table (Q₁₁, α, β, thickness t,
   mid-plane offset z for each ply) and compute the hygrothermal force
   resultant N = Σ Q₁₁ · (α · ΔT + β · ΔM) · t and moment resultant
   M = Σ Q₁₁ · (α · ΔT + β · ΔM) · t · z.
5. Retrieve the allowable stress (for isotropic members) or allowable
   resultants (for laminates) from the design allowables database. Flag any
   member or ply with no allowable on record as an open finding before
   computing MoS.
6. Compute the margin of safety for each demand–allowable pair and record the
   result as PASS (MoS ≥ 0) or FAIL (MoS < 0). The structural element is
   compliant only when all relevant MoS values are non-negative.

## Pitfalls

- Omitting the restraint factor and applying the full free strain as stress —
  a free-floating element carries no thermal stress regardless of ΔT; using
  R = 1 for all elements is conservative, but assuming R = 0 when restraints
  exist is non-conservative and must be justified.
- Treating the hygral and thermal effects as mutually exclusive when both ΔT
  and ΔM are non-zero — spacecraft structures in orbit experience simultaneous
  temperature cycling and absorbed moisture release; the combined strain must
  be used, not the larger of the two alone.
- Ignoring bending-extension coupling in asymmetric laminates — the moment
  resultant M drives out-of-plane deflection and secondary bending stresses
  that are not captured if only the force resultant N is checked.
- Using CTE values measured at room temperature for extreme-temperature
  ranges — CTE is temperature-dependent; for large ΔT excursions, integrate α
  over the temperature range or use a representative mean value with
  documented justification.
- Recording MoS = +∞ for zero-demand cases and treating them as
  unconditionally passing without noting they depend on the load case being
  correctly bounded — a zero demand that results from a missing load input
  is a data gap, not a design margin.

## Behavior contract (gate 3)

The thermal-strain, hygral-strain, restraint-stress, hygrothermal-resultant,
MoS, and end-to-end verification logic is exercised by the gate 3 contract
test: scripts/test_thermo_elastic_hygrothermal_analysis.py against
scripts/thermo_elastic_hygrothermal_analysis_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_thermo_elastic_hygrothermal_analysis.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
