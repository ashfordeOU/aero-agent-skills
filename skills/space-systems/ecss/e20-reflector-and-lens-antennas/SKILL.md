---
name: e20-reflector-and-lens-antennas
description: "Use when compute the dissipative loss, depolarisation and diffusivity of a reflecting or transmitting antenna surface under ECSS-E-ST-20C clause 7.2.2.2.2: categorize each surface as reflecting-surface (metal-reflector, mesh-reflector, grid-polariser) or transmitting-surface (dielectric-lens, radome-wall, dichroic-panel), derive conductor-loss from the surface-resistance at the operating frequency or dielectric-loss from wall-thickness, permittivity and loss-tangent, convert rms-surface-roughness into a specular-efficiency and a diffuse-scattered fraction, combine depolarisation contributions into a cross-polar-discrimination and an axial-ratio, then check the summed surface-loss-budget, diffusivity and cross-polar-discrimination against the antenna requirement. Trigger: ecss, e-st-20-electrical-scope, reflector-and-lens-antennas, reflecting-surface, transmitting-surface, cross-polar-discrimination, diffuse-scattering, surface-roughness-efficiency, dielectric-loss-tangent, conductor-surface-resistance."
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
  tags: [ecss, e-st-20-electrical-scope, e20-reflector-and-lens-antennas, reflecting-surface, transmitting-surface, cross-polar-discrimination, diffuse-scattering, surface-roughness-efficiency]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical — Reflector and Lens Antenna Surfaces (space-systems/ecss/e20-reflector-and-lens-antennas)

Use when the task is the surface-quality assessment of ECSS-E-ST-20C
clause 7.2.2.2.2 -- quantifying the loss, the depolarisation and the
diffusivity introduced by a reflecting or a transmitting antenna
surface, and rolling those three effects into the antenna's
radiation-performance budget.

## Domain quick reference

- Clause 7.2.2.2.2 separates an antenna surface into two families.
  A reflecting-surface (solid metal-reflector, mesh-reflector,
  grid-polariser, sub-reflector) returns the incident field; its
  dissipative term is the conductor-loss set by the surface-resistance
  Rs = sqrt(pi f mu0 / sigma), which rises as the square root of
  frequency and falls as the square root of conductivity. A
  transmitting-surface (dielectric-lens, radome-wall, dichroic-panel)
  passes the field; its dissipative term is the dielectric-loss set by
  the loss-tangent, the relative-permittivity and the refracted path
  length through the wall, which is longer than the wall-thickness at
  oblique incidence.
- Diffusivity is the fraction of incident power that leaves the
  surface outside the specular direction because of rms-surface-
  roughness. It is a phase-error efficiency, not a dissipation: the
  power is scattered into the sidelobe-region and the wide-angle
  pattern rather than absorbed, so it degrades on-axis directivity and
  raises stray radiation at the same time. A reflecting-surface sees
  the round-trip path error (a factor 4 pi sigma cos(theta) / lambda);
  a transmitting-surface sees only the refractive-index excess
  (a factor 2 pi (n - 1) sigma / lambda), so the identical roughness
  costs a reflecting-surface far more.
- Depolarisation is the conversion of the wanted polarisation into the
  orthogonal one by surface anisotropy -- mesh weave direction, grid
  pitch error, lens birefringence, a non-symmetric curvature error.
  Contributions combine in orthogonal power, not in decibels: each
  contribution is converted to a cross-polar power ratio, the ratios
  are summed, and the sum is converted back to a single
  cross-polar-discrimination. The equivalent axial-ratio follows from
  that discrimination and is the form a circular-polarisation
  requirement is usually written in.

## Workflow

1. Categorize every surface in the radiating path as reflecting or
   transmitting. Reject an unrecognized surface family before it
   enters the budget -- the two families take different loss models
   and different roughness sensitivities.
2. Compute the dissipative term. Reflecting: surface-resistance at the
   operating frequency, absorptivity at the incidence angle, repeated
   per bounce for a dual-reflector chain. Transmitting: attenuation
   constant from loss-tangent and relative-permittivity times the
   refracted path length through the wall.
3. Convert rms-surface-roughness into a specular-efficiency with the
   family-appropriate phase-error factor, and read the complement as
   the diffuse-scattered fraction; express it also as an equivalent
   scatter-loss in decibels for the budget.
4. Convert each depolarisation contribution into a cross-polar power
   ratio, sum the ratios, convert back to one cross-polar-
   discrimination, and derive the equivalent axial-ratio.
5. Sum the dissipative and scatter terms into the surface-loss-budget
   and compare budget, diffuse fraction and cross-polar-discrimination
   against the antenna requirement. Absorb representation error at an
   exact limit with a named tolerance -- never widen the limit itself.
6. Aggregate per surface; the radiating path is compliant only when
   every surface's finding list is empty.

## Pitfalls

- Applying the reflecting-surface roughness factor to a lens or a
  radome-wall. The transmitting phase error scales with the
  refractive-index excess, not with a round trip, so reusing the
  reflector factor overstates the diffuse fraction by a large margin.
- Adding depolarisation contributions in decibels. Cross-polar terms
  add in power; summing decibels understates the combined cross-polar
  level and passes a surface that is actually out of specification.
- Treating the diffuse-scattered fraction as dissipated. It leaves the
  aperture as wide-angle radiation, so it belongs in both the
  directivity budget and the stray-radiation case.
- Ignoring incidence angle on a transmitting-surface. At oblique
  incidence the refracted path through the wall exceeds the
  wall-thickness, and the dielectric-loss grows with it.
- Reading "no violation" from a surface whose requirement fields were
  never populated -- an absent limit is an open requirement, which is
  a finding, not a pass.

## Behavior contract (gate 3)

The surface-categorization, conductor-loss, dielectric-loss,
diffusivity and depolarisation logic is exercised by the gate 3
contract test: scripts/test_e20_reflector_and_lens_antennas.py against
scripts/e20_reflector_and_lens_antennas_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_reflector_and_lens_antennas.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
