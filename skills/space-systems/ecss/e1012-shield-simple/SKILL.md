---
name: e1012-shield-simple
description: "Use when run the simplified shielding analysis for a sensitive component under ECSS-E-ST-10-12C §6.2.2: model the shield as a planar slab, a spherical shell, or a set of solid-angle sectors, compute the areal density of each layer as thickness × density, invert that relation to derive the thickness needed for an areal-density budget, flux-weight the mean areal density across sectors, verify the sector set covers the full 4π sphere within tolerance, and report the minimum and maximum shielded ray directions as the worst- and best-case exposure paths. Trigger: ecss, e-st-10-12c, simplified-shielding, planar-slab, spherical-shell, solid-angle-sectoring, areal-density, shielding-summary."
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
  tags: [ecss, e-st-10-12c, simplified-shielding, planar-slab, spherical-shell, solid-angle-sectoring, areal-density]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Space Environment — Simplified Shielding Geometry (space-systems/ecss/e1012-shield-simple)

Use when the task is a simplified shielding computation under
ECSS-E-ST-10-12C §6.2.2 — reducing a shielding problem to a planar slab, a
spherical shell, or a small set of solid-angle sectors, and computing areal
density, the inverse thickness, and sector coverage with stdlib arithmetic
alone.

## Domain quick reference

- §6.2.2 permits simplified shielding approaches when the surrounding structure
  is regular enough that a small number of representative ray directions
  captures the shielding distribution. Three geometry families are supported
  here, and they are independent: planar, spherical, and solid-angle sectoring.
- **Areal density** is the governing quantity and is conserved across
  materials: `areal_density (g/cm²) = thickness (cm) × density (g/cm³)`. The
  planar model returns it directly from a slab thickness; the spherical models
  return it along a radial ray (shell thickness or sphere radius); the sector
  model carries one areal-density value per sector direction.
- **Planar** geometry treats the shield as a flat slab of uniform thickness, so
  the areal density is constant across the surface and the relation is exactly
  invertible — given an areal-density budget and a material density the
  required physical thickness is the budget divided by the density.
- **Spherical** geometry treats the shield as a shell around the sensitive
  volume. A shell's radial areal density is `(outer − inner) × density`; a
  solid sphere's is `radius × density`. The shell value equals the difference of
  the two solid-sphere values, which is a useful consistency check.
- **Solid-angle sectoring** decomposes the full 4π sr sphere into sectors, each
  carrying a solid angle ω (sr) and its own areal density. The flux-weighted
  mean areal density is `Σ(ωᵢ × ADᵢ) / Σωᵢ`; the minimum and maximum sector
  values bound the worst- and best-shielded directions. A complete sector set
  must sum to 4π sr within a fractional tolerance.

## Workflow

1. Choose the geometry family. Use planar when the shield is a flat plate seen
   at normal incidence; spherical when the sensitive volume is enclosed by a
   shell or is a solid sphere seen radially; sectoring when the shielding
   varies with direction and a coarse angular breakdown is acceptable.
2. For planar geometry, call `planar_areal_density(thickness_cm,
   density_g_cm3)`. If instead an areal-density budget is the input, call
   `planar_thickness_from_areal_density(areal_density_g_cm2, density_g_cm3)` to
   obtain the required physical thickness. Both reject negative thickness or
   areal density and non-positive density.
3. For spherical geometry, call `spherical_shell_areal_density(outer_radius_cm,
   inner_radius_cm, density_g_cm3)` for an enclosing shell, which requires the
   outer radius to exceed the inner radius, or `solid_sphere_areal_density(
   radius_cm, density_g_cm3)` for a solid body seen along a radial ray.
4. For sectoring, build the sector set with `build_uniform_sectoring(n_sectors,
   density_g_cm3, thickness_cm)` for a uniform shell, or supply an explicit
   list of `{"solid_angle_sr": ω, "areal_density_g_cm2": AD}` dicts. Each
   sector must carry both keys, a strictly positive solid angle, and a
   non-negative areal density.
5. Confirm the sector set covers the sphere with
   `total_solid_angle_check(sectors, tolerance=0.01)`; a partial set returns
   False. Then take `solid_angle_weighted_areal_density(sectors)` as the mean
   ray, and `minimum_sector_areal_density` / `maximum_sector_areal_density` as
   the bounding directions.
6. Aggregate the direction picture with `shielding_summary(sectors)`, which
   returns the sector count, the minimum, maximum and flux-weighted mean areal
   densities, and the full-sphere coverage flag in one dict.
7. Feed the resulting areal density (single value, or the weighted mean / worst
   direction) into the dose or fluence attenuation step of the shielding
   calculation process; the simplified geometry provides the areal density, not
   the environment response.

## Pitfalls

- Applying the planar relation to a curved or strongly directional shield — a
  slab model assumes uniform areal density across the surface and cannot
  represent angular variation; that case needs sectoring.
- Confusing shell thickness with shell radius in the spherical model — a shell
  uses `(outer − inner)`, a solid sphere uses `radius`; using the radius for a
  thin shell overstates the shielding substantially.
- Treating a partial or overlapping sector set as complete — the weighted mean
  is only meaningful if the sector solid angles sum to 4π sr; run
  `total_solid_angle_check` before trusting the mean, and treat False as an
  invalid model rather than a small error.
- Weighting sectors by their areal density instead of their solid angle — the
  mean must weight each sector's areal density by the solid angle it subtends,
  otherwise a narrow but heavily shielded direction dominates incorrectly.
- Reporting only the flux-weighted mean — a mean that meets the budget can hide
  a minimum-direction sector that does not; always report the minimum bounding
  ray alongside the mean.

## Behavior contract (gate 3)

The planar, spherical, and solid-angle sectoring logic is exercised by the
gate 3 contract test: `scripts/test_e1012_shield_simple.py` against
`scripts/e1012_shield_simple_logic.py` (stdlib unittest, offline). The test
exercises `planar_areal_density` and its inverse
`planar_thickness_from_areal_density` (round-trip and zero cases),
`spherical_shell_areal_density` and `solid_sphere_areal_density` (including
the shell-equals-difference-of-solids identity),
`build_uniform_sectoring`, `solid_angle_weighted_areal_density`,
`total_solid_angle_check`, `minimum_sector_areal_density`,
`maximum_sector_areal_density`, and `shielding_summary`, together with the
`ShieldingError` raised on every invalid input (negative or zero thickness and
density, outer radius not exceeding inner, non-positive radius, empty sector
list, missing sector key, negative sector areal density, non-positive sector
count). Run:

python3 scripts/test_e1012_shield_simple.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and paraphrase
  per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
