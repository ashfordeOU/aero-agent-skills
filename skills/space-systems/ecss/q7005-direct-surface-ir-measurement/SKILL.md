---
name: q7005-direct-surface-ir-measurement
description: "Evaluate an accessible hardware surface for organic contamination by direct infrared reflection under ECSS-Q-ST-70-05C. Use when the part cannot be solvent sampled or a non-contacting reading is wanted, and a reflection spectrum taken against a clean reference area of the same substrate has to become a film thickness and an areal mass. Picks the reflection technique the surface finish actually supports, applies the double-pass path enhancement the incidence angle produces, refuses a grazing reading on a poorly reflecting substrate, and flags a reference area taken from a different material. Trigger: ecss, q-st-70-05, direct-surface-ir-reflection, grazing-incidence-reflection-absorption, diffuse-reflectance-contamination, attenuated-total-reflection-sampling, incidence-angle-path-enhancement, contamination-film-thickness."
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
  tags: [ecss, q-st-70-contamination-infrared-scope, q7005-direct-surface-ir-measurement, direct-surface-ir-reflection, grazing-incidence-reflection-absorption, diffuse-reflectance-contamination, attenuated-total-reflection-sampling, incidence-angle-path-enhancement]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Organic Contamination by IR — Direct Surface Measurement (space-systems/ecss/q7005-direct-surface-ir-measurement)

Use when the task is the direct arm of ECSS-Q-ST-70-05C — reading the
contamination film where it sits, on an accessible surface, with a
reflection technique instead of lifting it into a solvent.

## Domain quick reference

- The direct route does not destroy the deposit and does not depend on a
  recovery fraction, which is its advantage over the extract route. What
  it buys with that is a dependence on the substrate: the surface itself
  is half the optical path, so a technique that suits polished metal
  says nothing on a painted or blanket surface.
- A specular, well reflecting substrate supports grazing-incidence
  reflection-absorption. The beam crosses the film twice, and at a large
  angle from the normal the path through it is longer than the film is
  thick by two over the cosine of that angle. That enhancement is the
  whole sensitivity advantage of the grazing geometry.
- A diffusely scattering or rough surface destroys the specular beam, so
  the reading has to be collected as diffuse reflectance instead, with
  no clean geometric path-length factor and a correspondingly weaker
  quantitative claim.
- A compliant surface that can be pressed against an internal reflection
  element supports attenuated total reflection, which samples only the
  depth the evanescent field reaches. That depth, not the film
  thickness, bounds what the reading can see.
- Every direct reading is differential. The reference is a clean area of
  the same substrate with the same finish; referencing against a
  different material folds the two substrates' own absorptions into the
  result and the difference is indistinguishable from contamination.
- Converting an absorbance to an areal mass needs the absorptivity of
  the contaminant at the band and its density. A thickness reported
  without both is an optical result, not a cleanliness result.

## Workflow

1. Validate the surface record: finish, specular reflectance, whether the
   area is reachable by the instrument, and the spot size against the
   available aperture.
2. Select the reflection technique the finish supports, and refuse a
   surface that is not reachable rather than quoting a reading the
   geometry cannot produce.
3. Validate the incidence angle inside the window of the selected
   technique, and form the double-pass path enhancement from its cosine.
4. Form the net absorbance by differencing the contaminated reading
   against the clean reference area, refusing a reference recorded on a
   different substrate or finish.
5. Convert the net absorbance to a film thickness through the band
   absorptivity and the path enhancement.
6. Convert the thickness to an areal mass through the contaminant
   density, keeping the unit conversion explicit.
7. Report the technique, enhancement, thickness, areal mass and every
   finding: an angle outside the technique window, a substrate too dark
   for the grazing route, a spot larger than the aperture, or a reading
   whose depth exceeds what the evanescent field samples.

## Pitfalls

- Applying the grazing path enhancement to a diffuse-reflectance reading.
  There is no single specular path in diffuse collection, so the cosine
  factor does not exist and using it inflates the thickness by the whole
  enhancement.
- Referencing against a clean coupon of a different alloy or finish. The
  substrate absorptions do not cancel, and the residual reads as a film
  that is not there.
- Treating a near-normal reading as equivalent to a grazing one. At small
  angles the enhancement approaches two, so the same film gives a much
  smaller absorbance and a sensitivity claim carried over from the
  grazing geometry is wrong by that ratio.
- Reporting an attenuated-total-reflection reading as a full film
  thickness. The evanescent field samples a fixed depth; a thicker film
  saturates the reading, and the honest output is a lower bound.
- Quoting a thickness as a cleanliness level. The level is an areal mass,
  and the conversion needs the contaminant density, which is a property
  of the identified species and not a constant.

## Behavior contract (gate 3)

The surface validation, technique selection, incidence-angle window,
path-enhancement formation, reference differencing, thickness conversion
and areal-mass reduction are exercised by the gate 3 contract test:
scripts/test_q7005_direct_surface_ir_measurement.py against
scripts/q7005_direct_surface_ir_measurement_logic.py (stdlib unittest,
offline). Run:
python3 scripts/test_q7005_direct_surface_ir_measurement.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
