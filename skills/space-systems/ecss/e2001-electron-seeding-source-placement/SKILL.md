---
name: e2001-electron-seeding-source-placement
description: "Use when verify that a chosen multipactor electron-seeding technique is aimed at the critical-gap where breakdown initiates under ECSS-E-ST-20-01C clause 6.5.5: confirm the declared aim-point is the predicted initiation-site, resolve the source-to-gap sight-line, subtract every intervening areal-density from the beta-particle-range, fold the gap aperture into a solid-angle capture-fraction, check that an ultraviolet-illumination photon clears the target-surface work-function and that an electron-gun beam lands inside the gap within its yield-energy-window, then compare the delivered seed-electron-rate at the gap against the rate the seeding-budget demands. Trigger: ecss, e-st-20-01c, seed-source-placement, critical-gap-aiming, beta-particle-range, solid-angle-capture, photoemission-work-function, landing-energy-window, sight-line-obstruction."
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
  tags: [ecss, e-st-20-electrical-scope, e2001-electron-seeding-source-placement, seed-source-placement, critical-gap-aiming, beta-particle-range, solid-angle-capture, photoemission-work-function]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Multipactor Design and Test — Electron Seeding Source Placement (space-systems/ecss/e2001-electron-seeding-source-placement)

Use when the task is the seed-source aiming rule of ECSS-E-ST-20-01C
clause 6.5.5 -- taking whichever seeding technique has been selected and
proving that the free electrons it makes actually arrive inside the
critical-gap where a multipactor discharge is predicted to start, rather
than somewhere else in the vacuum chamber.

## Domain quick reference

- Seeding is a delivery problem, not a procurement problem. A source
  rated at a high emission-rate contributes nothing unless its output
  reaches the initiation-site: the gap or gap-region the design
  analysis names as the location with the lowest breakdown-threshold.
  The first check is therefore an identity check -- the declared
  aim-point against the predicted initiation-site.
- Emission spreads over the full sphere while the gap subtends a small
  aperture, so only a solid-angle capture-fraction of roughly the gap
  aperture divided by four-pi times the squared source-to-gap distance
  ever enters the gap. Doubling the stand-off quarters the delivered
  rate.
- A beta-emitting radioactive source delivers electrons only while its
  particle-range beats the areal-density of everything in the path.
  The Katz-Penfold range fit turns the emitted energy into a range in
  mass-per-area; each intervening wall contributes thickness times
  density; an absorption coefficient falling off with energy converts
  the surviving path into a transmitted fraction.
- Ultraviolet-illumination seeds indirectly: the photon has to land on
  a gap surface and free an electron, which happens only when the
  photon energy exceeds that surface material's work-function. Any
  opaque item across the sight-line stops the process outright,
  whatever the wavelength.
- An electron-gun aims a beam, so it carries two extra conditions: the
  beam must land within the gap rather than on the surrounding
  structure, and the landing-energy must sit inside the window where
  the surface yields secondaries usefully -- too low and the beam is
  repelled, too high and it buries charge in the wall instead.

## Workflow

1. Reject an unknown technique, then confirm the declared aim-point
   names the same location as the predicted initiation-site; a mismatch
   is a finding regardless of the numbers that follow.
2. Accumulate the areal-density of every intervening item from its
   thickness and density, and note whether any of them is opaque.
3. Compute the solid-angle capture-fraction from the gap aperture and
   the source-to-gap distance.
4. Apply the technique-specific transport check: beta-particle-range
   against the accumulated areal-density (and the resulting transmitted
   fraction) for a radioactive-source; photon energy against the
   target-surface work-function, plus an opaque-barrier check, for
   ultraviolet-illumination; aim-offset against the half-gap and
   landing-energy against the yield-energy-window for an electron-gun.
5. Multiply emission-rate by transmitted fraction by capture-fraction
   to get the delivered seed-electron-rate at the gap.
6. Compare that delivered rate with the rate the seeding-budget
   demands, and report every finding; the placement is acceptable only
   when the finding list is empty.

## Pitfalls

- Crediting the source's nameplate emission-rate as the rate at the
  gap. Solid-angle capture alone routinely costs three to four orders
  of magnitude before any absorption is considered.
- Mounting a beta source behind a bracket or a waveguide wall on the
  assumption that "some electrons get through". When the areal-density
  exceeds the particle-range the transmitted fraction is zero, not
  small.
- Aiming ultraviolet-illumination at a surface whose work-function sits
  above the photon energy. The lamp is on, the geometry looks right,
  and no electron is ever released.
- Aiming the source at the highest-field region computed for the
  nominal build rather than at the gap the analysis flags as the
  initiation-site. They coincide only when the geometry has a single
  dominant gap.
- Turning up the electron-gun energy to force more current in. Beyond
  the yield-energy-window the beam implants charge in the wall and
  perturbs the very surface condition the run is meant to qualify.

## Behavior contract (gate 3)

The aim-point, range, transmission, capture-fraction, work-function,
landing-window and delivered-rate logic is exercised by the gate 3
contract test:
scripts/test_e2001_electron_seeding_source_placement.py against
scripts/e2001_electron_seeding_source_placement_logic.py (stdlib
unittest, offline). Run:
python3 scripts/test_e2001_electron_seeding_source_placement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
