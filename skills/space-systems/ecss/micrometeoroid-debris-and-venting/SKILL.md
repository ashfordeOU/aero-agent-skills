---
name: micrometeoroid-debris-and-venting
description: "Use when assess micrometeoroid and orbital debris collision risk and venting adequacy for spacecraft structural components under ECSS-E-ST-32C §4.5.14–4.5.15: categorize each particle threat as a meteoroid or orbital-debris source, estimate the penetrating flux at mission altitude, determine the critical diameter for the shield configuration, compute the Probability of No Penetration via Poisson statistics, check PNP against the required threshold, and verify every enclosed structural volume carries an adequate venting provision. Trigger: ecss, e-st-32-structures-scope, mmod, micrometeoroid, orbital-debris, shielding, probability-of-no-penetration, venting, whipple-shield."
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
  tags: [ecss, e-st-32-structures-scope, mmod, micrometeoroid, orbital-debris, shielding, probability-of-no-penetration, venting, whipple-shield]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Structures — Micrometeoroid, Debris and Venting (space-systems/ecss/micrometeoroid-debris-and-venting)

Use when the task is the MMOD collision design assessment and venting provision
verification of ECSS-E-ST-32C §4.5.14–4.5.15 — categorizing particle threats,
sizing shielding performance via ballistic limit equations, computing the
Probability of No Penetration (PNP), and confirming enclosed structural volumes
carry adequate vent paths.

## Domain quick reference

- §4.5.14 requires the designer to account for two threat families: natural
  micrometeoroids (sporadic background plus stream events, typical encounter
  velocity ~20 km/s) and man-made orbital debris (fragmentation clouds, spent
  rocket bodies, paint flakes, coolant droplets, typical velocity 7–10 km/s in
  LEO). Each source is categorized into exactly one family before its flux is
  evaluated.
- Flux is the cumulative rate of particle impacts per unit area per year above a
  given diameter at the mission altitude. The flux decreases with increasing
  particle diameter following a power law; debris flux peaks near 800 km
  altitude while meteoroid flux is roughly constant below GEO. For detailed work,
  use NASA ORDEM or ESA MASTER; for early screening, a simplified power-law
  model is acceptable.
- The critical diameter d_c is the largest projectile diameter that a given
  shield stops. The penetrating flux is therefore evaluated at d_c — any particle
  at or above d_c penetrates. For a single aluminium wall, d_c scales with wall
  thickness and decreases with impact velocity; a Whipple dual-wall shield
  significantly raises d_c by fragmenting the projectile on the bumper and
  dispersing the debris cloud before it reaches the rear wall.
- The Probability of No Penetration (PNP) is derived from Poisson statistics:
  PNP = exp(−λ) where λ = flux(d_c) × exposed area × mission duration. PNP is
  evaluated against a program-specified threshold (commonly ≥ 0.95 or ≥ 0.99 for
  manned/unmanned missions).
- §4.5.15 mandates venting provisions for enclosed structural volumes. During
  launch ascent, trapped gas expands; if vent paths are absent or undersized,
  the resulting differential pressure can exceed the structural allowable.
  Additionally, an MMOD penetration event into an enclosed volume introduces a
  pressure transient that must vent harmlessly. Every enclosed compartment must
  have at least one defined vent path and a vent-area-to-volume ratio above the
  program minimum threshold.

## Workflow

1. Inventory every particle threat source and categorize each one as
   meteoroid or orbital debris. Reject an unrecognized source type before it
   enters the flux calculation.
2. For each structural component, select the applicable shield configuration
   (single wall, Whipple, stuffed Whipple, or multi-shock) and derive the
   critical diameter d_c using the appropriate ballistic limit equation.
   Document which BLE variant was applied and why.
3. Compute the penetrating flux at d_c for each threat category at the mission
   altitude; sum the contributions across all applicable threat categories to
   obtain total penetrating flux for the component.
4. Compute PNP = exp(−flux × area × duration) for each component. Compare
   against the required PNP threshold; flag any component whose PNP falls below
   the threshold as a shielding-upgrade finding.
5. For every enclosed structural volume (cavities, bays, honeycomb cores if
   sealed), compute the vent-area-to-volume ratio and compare against the
   program minimum (typically 10⁻⁴ m⁻¹). Flag a zero vent area as an
   unconditional non-compliance. Flag an undersized vent area with the shortfall
   in m².
6. Aggregate PNP and venting findings per component; a component is
   MMOD-compliant only when both lists are empty.

## Pitfalls

- Applying flux at an arbitrary small diameter instead of the shield's actual
  critical diameter — this understates the penetrating flux, inflates PNP, and
  produces a non-conservative result.
- Treating meteoroid and debris flux as additive without checking which dominates
  at the mission altitude and diameter of interest. At small sizes below
  ~0.1 mm in LEO, debris flux typically dominates; above ~10 mm, meteoroids may
  dominate. Summing both is always conservative and is the correct approach.
- Conflating the Whipple hypervelocity regime (v > 7 km/s) with the
  sub-hypervelocity regime (3–7 km/s). The ballistic limit equation changes form
  across the transition; applying the hypervelocity formula below 7 km/s
  overpredicts d_c and under-predicts risk.
- Leaving an enclosed volume without any vent provision and recording "no
  differential pressure calculated" as a pass — the absence of a vent path is
  itself a structural non-compliance, not a neutral finding.
- Carrying forward a stuffed-Whipple or multi-shock shield without a
  manufacturer-specific or test-calibrated BLE; the generic Whipple proxy used
  in screening may not be conservative for all impact angles and fill materials.

## Behavior contract (gate 3)

The threat categorization, flux estimation, critical diameter, PNP computation,
venting check, and component aggregation logic is exercised by the gate 3
contract test: scripts/test_micrometeoroid_debris_and_venting.py against
scripts/micrometeoroid_debris_and_venting_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_micrometeoroid_debris_and_venting.py

## Compliance

- ECSS standards are freely downloadable from ESA; cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
