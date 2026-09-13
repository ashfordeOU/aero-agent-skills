---
name: e20-antenna-support-structure-scattering
description: "Use when compute the support-structure-scattering assessment of ECSS-E-ST-20C clause 7.2.2.3.6: categorize every feed-support-strut, subreflector tripod-leg and rim-fitting by the field-region it intercepts, separate plane-wave-scattering in the collimated aperture-field from spherical-wave-scattering in the diverging feed-wave and from rim edge-diffraction, magnify each feed-region shadow onto the reflector, sum the projected aperture-blockage-area, derive the blockage-efficiency antenna-gain-loss, predict the scattered side-lobe-level and split it into co-polar and cross-polar shares from the strut-tilt, and judge each figure against the declared allowable. Trigger: ecss, e-st-20-electrical-scope, support-structure-scattering, feed-support-strut, aperture-blockage, plane-wave-scattering, spherical-wave-scattering, edge-diffraction, side-lobe-degradation, reflector-antenna-blockage."
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
  tags: [ecss, e-st-20-electrical-scope, e20-antenna-support-structure-scattering, support-structure-scattering, feed-support-strut, aperture-blockage, plane-wave-scattering, spherical-wave-scattering, edge-diffraction, reflector-antenna-blockage]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Electrical and Optical Engineering — Support-Structure Scattering (space-systems/ecss/e20-antenna-support-structure-scattering)

Use when the task is the support-structure-scattering assessment of
ECSS-E-ST-20C clause 7.2.2.3.6 -- deciding which mechanical supports of a
reflector-antenna actually perturb the radiated field, converting each one
into an equivalent aperture-blockage-area, and turning that area into the
antenna-gain-loss, scattered side-lobe-level and cross-polar-level the
antenna budget has to absorb.

## Domain quick reference

- A support perturbs the antenna only through the field it intercepts.
  Four field-regions are recognised and each maps to exactly one
  mechanism: the collimated aperture-field (plane-wave-scattering, the
  classic strut shadow across the projected aperture), the diverging
  feed-wave between the feed phase-centre and the reflector
  (spherical-wave-scattering, a near-feed obstruction whose shadow is
  magnified before it reaches the reflector), the reflector-rim
  (edge-diffraction, a wide-angle lobe rather than an aperture loss) and
  the volume outside the illuminated cone (no-scattering-path, contributes
  nothing and is dropped rather than carried as a worst case). A support
  whose field-region is not one of the four is rejected, never assumed.
- Geometry: a straight strut of width w and length L at tilt t to the
  aperture plane shadows w x L x cos(t) per leg. A support lit by the
  diverging feed-wave at distance ds from the phase-centre, with the
  reflector at dr, casts a shadow magnified by dr/ds, so its equivalent
  aperture-blockage-area is the geometric area times (dr/ds) squared --
  a thin tripod-leg close to the feed can block far more aperture than
  its own cross-section suggests.
- The blocked field is removed coherently from the aperture, so the
  antenna-gain-loss is -20*log10(1 - f) with f the blocked fraction of the
  aperture area. The same intercepted power reappears as a scattered lobe
  spread over a solid angle wider than the main beam by an
  angular-spread-factor s, so its peak sits at 10*log10(f / ((1-f)*s))
  relative to the main-beam peak.
- A thin strut at angle t to the incident electric-field radiates cos^2(t)
  of the scattered power in the co-polar sense and sin^2(t) in the
  cross-polar sense, so the same strut geometry drives both the
  side-lobe-degradation and the polarisation-purity budget. An aligned
  strut produces no cross-polar term at all; a strut at 45 degrees splits
  the scattered power evenly.
- Compliance is per figure, not global: the antenna-gain-loss is judged
  against its allowable, the co-polar scattered lobe against the
  side-lobe allowable, the cross-polar share against the
  cross-polar allowable, and each declared rim edge-diffraction level
  against the side-lobe allowable. An allowable that is absent is a
  finding in its own right, not a pass.

## Workflow

1. Inventory every mechanical item in or near the antenna aperture: feed
   support struts, subreflector tripod legs, hold-down brackets, rim
   fittings, waveguide runs crossing the aperture. Give each a unique id;
   a duplicated id means the same hardware would be counted twice.
2. Categorize each item by the field-region it intercepts, and take the
   mechanism from that region. Drop the items that intercept no
   illuminated field; they contribute neither blockage nor a lobe.
3. Project the blocking items onto the aperture plane: geometric shadow
   for a plane-wave-scattering item, geometric shadow times the squared
   feed magnification for a spherical-wave-scattering item. Reject a
   feed-region item that does not declare both its own distance and the
   reflector distance from the feed phase-centre -- the magnification
   cannot be guessed.
4. Sum the equivalent areas, divide by the aperture area to get the
   blocked fraction, and derive the blockage-efficiency antenna-gain-loss.
   A total that reaches the whole aperture is not a blockage case and is
   rejected.
5. Convert the same fraction into the peak scattered side-lobe-level using
   the declared angular-spread-factor, then split that level into its
   co-polar and cross-polar shares using the strut tilt to the incident
   electric-field.
6. Judge every figure against its declared allowable, add a finding for
   each allowable that is missing from the record, and check every rim
   item's declared edge-diffraction level against the side-lobe allowable.
   The antenna is scattering-compliant only when the finding list is
   empty.

## Pitfalls

- Treating a thin tripod-leg near the feed as a small blockage because its
  cross-section is small -- the feed-wave shadow is magnified by the square
  of the distance ratio, and a 0.2 m leg at a quarter of the feed-to-
  reflector distance blocks sixteen times its own area.
- Adding the scattered lobe to the antenna-gain-loss as if they were two
  independent losses -- they are the same intercepted power counted twice,
  once as energy removed from the main beam and once as energy appearing
  off-axis.
- Judging the total scattered lobe against the co-polar side-lobe
  allowable -- only the cos^2(t) share lands in the co-polar pattern, and
  the remainder has to be charged to the cross-polar budget instead of
  being dropped.
- Reading "no violation" as compliant when no allowable was ever declared
  -- an absent allowable means the antenna specification was not captured,
  which is a finding, not a pass.
- Carrying an item that sits outside the illuminated cone "to be
  conservative" -- it inflates the blocked fraction, the antenna-gain-loss
  and the scattered lobe simultaneously, and hides the supports that
  really drive the budget.

## Behavior contract (gate 3)

The mechanism categorisation, shadow projection and magnification,
blockage-fraction and antenna-gain-loss, scattered side-lobe-level and its
co-polar/cross-polar split, and the allowable-comparison logic are
exercised by the gate 3 contract test:
scripts/test_e20_antenna_support_structure_scattering.py against
scripts/e20_antenna_support_structure_scattering_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_e20_antenna_support_structure_scattering.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
