---
name: e20-telemetry-and-data-antenna-patterns
description: "Use when characterize the radiation-pattern of a spacecraft telecommand or telemetry-and-data antenna, including scattering from nearby structures, under ECSS-E-ST-20C clause 7.2.2.2.1: validate the angular-sampling of each pattern cut, categorize every nearby structure as blockage, scattering or negligible from its size in wavelengths and whether it obscures the boresight path, apply the worst-case blockage attenuation and scattering ripple to the free-space cut, compute the installed worst-case gain inside the required coverage-cone and the solid-angle-weighted coverage-fraction above the threshold-gain, and report each shortfall against the link requirement. Trigger: ecss, e-st-20-electrical-scope, e20-telemetry-and-data-antenna-patterns, radiation-pattern, telecommand-antenna, structure-scattering, coverage-cone, angular-sampling, blockage-attenuation, low-gain-antenna."
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
  tags: [ecss, e-st-20-electrical-scope, e20-telemetry-and-data-antenna-patterns, radiation-pattern, telecommand-antenna, structure-scattering, coverage-cone, angular-sampling, blockage-attenuation]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical & Optical — Telemetry and Data Antenna Patterns (space-systems/ecss/e20-telemetry-and-data-antenna-patterns)

Use when the task is the radiation-pattern characterization of a command
or telemetry-and-data antenna under ECSS-E-ST-20C clause 7.2.2.2.1 --
covering the angular region the link needs and carrying the effect of the
surrounding spacecraft structures rather than quoting the free-space
pattern of the isolated antenna.

## Domain quick reference

- Command and telemetry-and-data antennas are the link that has to work
  in every attitude, including a tumbling or safe-mode spacecraft. The
  quantity that matters is therefore not the boresight peak but the
  worst-case gain anywhere inside the required coverage-cone, and how
  much of the sphere sits above the threshold-gain the link closes at.
- A pattern cut is a set of gain samples against angle. It is usable
  only if the angles increase strictly, stay inside the half-sphere on
  each side, and are sampled finely enough to resolve the nulls -- a cut
  sampled every few tens of degrees interpolates straight across a deep
  null and reports coverage that does not exist.
- Nearby structures fall into three categories, set by size in
  wavelengths and by whether the structure sits in the path: a structure
  much smaller than a wavelength is negligible whatever it is made of; a
  wavelength-scale or larger structure in the path is blockage; anything
  else conductive, or a large dielectric, scatters. The same physical
  bracket is negligible at one carrier and a blocker an octave up, so
  the categorization is redone per band, never inherited.
- Blockage removes gain over the obscured sector; scattering adds a
  ripple that the worst-case view takes as a loss over its own sector.
  Both bleed into a guard band at the sector edges, where diffraction
  softens the transition rather than stopping at the geometric shadow.
- Coverage-fraction is weighted by solid angle, not by angle: a degree
  near boresight subtends far less sphere than a degree near the horizon,
  and an unweighted angular count overstates polar coverage badly.

## Workflow

1. Validate every pattern cut and check its angular-sampling against the
   step the link analysis needs. Reject a malformed cut; report a coarse
   one as a finding rather than interpolating over it.
2. Convert the carrier to a free-space wavelength and categorize each
   nearby structure as blockage, scattering or negligible from its size
   in wavelengths and whether it obscures the boresight path.
3. Derive the worst-case perturbation of each non-negligible structure
   -- from the measured or specified value where one exists, otherwise
   from its size in wavelengths, capped at the blockage and ripple
   ceilings.
4. Apply the perturbations to the free-space cut over each structure's
   angular sector, with half the level in the guard band either side,
   accumulating the contributions where sectors overlap.
5. From the installed cut, compute the worst-case gain inside the
   required coverage-cone and the solid-angle-weighted coverage-fraction
   above the threshold-gain.
6. Grade both against the link requirement and report the degradation
   the structures cost. The antenna is characterized only when the
   installed numbers, not the free-space ones, meet the requirement.

## Pitfalls

- Quoting the free-space pattern of the isolated antenna as the
  installed performance. The clause exists because the structures are
  part of the antenna once it is mounted; the two numbers differ most
  exactly where the link is weakest.
- Sampling the cut coarsely and reading the interpolation as coverage --
  a deep null between two samples never appears, and the worst-case gain
  comes out optimistic by the depth of the null.
- Categorizing a structure once and reusing it across bands. Size in
  wavelengths is the criterion; a bracket that is negligible at a low
  carrier blocks at a high one.
- Counting coverage in angle instead of solid angle, which inflates the
  contribution of the region near boresight and hides a hole near the
  horizon.
- Stopping the perturbation at the geometric shadow edge. Diffraction
  carries part of the loss into the guard band, and a pattern that meets
  its requirement only just outside the shadow boundary is not verified.
- Reading an exact requirement match as a miss. Accumulated perturbations
  are a sum of decibel terms and land a few ULPs beyond the limit; the
  comparison absorbs that representation error while the required gain
  itself never moves.

## Behavior contract (gate 3)

The cut-validation, angular-sampling, interpolation, structure
categorization, perturbation, coverage-fraction and roll-up logic is
exercised by the gate 3 contract test:
scripts/test_e20_telemetry_and_data_antenna_patterns.py against
scripts/e20_telemetry_and_data_antenna_patterns_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e20_telemetry_and_data_antenna_patterns.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
