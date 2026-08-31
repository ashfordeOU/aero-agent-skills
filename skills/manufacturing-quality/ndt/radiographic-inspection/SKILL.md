---
name: radiographic-inspection
description: "Use when you must plan and evaluate a radiographic inspection (RT) for aerospace NDT: compute the geometric unsharpness from the focal spot size, the source-to-object distance, and the object-to-detector distance; size the image quality indicator (IQI) penetrameter and its percent sensitivity; apply the inverse-square law to X-ray or gamma-ray exposure time; check the film density against the 2.0 to 4.0 band; and classify indications such as porosity, cracks, inclusions, and slag. Produces the setup geometry, exposure settings, and the sensitivity and density verdicts that gate radiographic acceptance of welds and castings. Trigger: radiography, X-ray, gamma ray, IQI, penetrameter, geometric unsharpness, film density, porosity."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [radiographic-inspection, radiography, x-ray, gamma-ray, iqi, penetrameter, geometric-unsharpness, unsharpness, film-density, film, density, porosity, exposure-time, inverse-square, source-to-object, object-to-detector, sensitivity, weld, casting, radiograph]
  version: 0.1.0
  author: AeroSkills
---

# Radiographic Inspection (manufacturing-quality/ndt/radiographic-inspection)

Use when the task is executing industrial radiography (RT) on an
aerospace part: computing the setup geometry (geometric unsharpness),
selecting and reading the image quality indicator (IQI) penetrameter,
setting the exposure time for X-ray or gamma-ray sources, judging the
processed film density, and classifying the discontinuities that the
radiograph reveals.

## Domain quick reference

- Geometric unsharpness: Ug = F * ODD / SOD, with F the effective focal
  spot size, SOD the source-to-object distance, and ODD the
  object-to-detector distance, all in mm. Example: a 3 mm focal spot at
  500 mm SOD with 30 mm ODD gives Ug = 3 * 30 / 500 = 0.18 mm. A finer
  focal spot and a longer source distance reduce unsharpness; a typical
  limit for fine-detail work is 0.25 mm. X-ray tubes can have small
  focal spots (fractions of a mm), while gamma-ray isotopes such as
  Ir-192 and Co-60 have larger effective focal spots, so gamma setups
  trade more unsharpness for portability.
- Exposure time by the inverse-square law: t2 = t1 * (d2 / d1)^2, with
  t1 the exposure time measured or charted at reference distance d1 and
  t2 the time needed at distance d2. Doubling the source-to-film
  distance quadruples the required time; halving it quarters the time.
  Example: 4 min at 900 mm becomes 1 min at 450 mm.
- IQI (penetrameter) sensitivity: sensitivity percent =
  visible_thickness / part_thickness * 100, where visible_thickness is
  the thinnest IQI feature (hole or step) visible on the radiograph and
  part_thickness is the section thickness examined. Typical aerospace
  acceptance requires 2 percent or better; the penetrameter is placed on
  the source side of the part.
- Film density: optical density of the processed film, typically judged
  against a 2.0 to 4.0 band (density below the band is underexposed and
  too light, above it is overexposed and too dark). The governing
  specification may set a narrower range; the 2.0 to 4.0 band is common
  practice, not a universal requirement.
- Discontinuities on the radiograph: porosity appears as round or
  globular voids (often clustered), cracks as sharp, narrow, elongated
  lines, inclusions as compact foreign material (metallic inclusions
  appear brighter on the film), and slag as flat, planar, or angular
  nonmetallic residue, typically in weld context.
- AS9100 clause 8.5.1.3 frames NDT as a special process: radiography is
  performed to an approved written procedure by qualified, certified
  personnel, with calibrated equipment and recorded results, before the
  part is accepted or released.

## Workflow

1. Define the inspection geometry: the effective focal spot F, the
   source-to-object distance SOD, and the object-to-detector distance
   ODD. Compute the geometric unsharpness with
   geometric_unsharpness(F, SOD, ODD) and confirm it is at or below the
   required limit (default 0.25 mm for fine detail); rework the geometry
   otherwise.
2. Select the IQI penetrameter for the section thickness, place it on
   the source side, and determine the sensitivity with
   iqi_sensitivity_percent(visible_thickness, part_thickness); confirm
   the sensitivity meets the acceptance requirement (typically 2
   percent or better).
3. Establish the baseline exposure (chart or prior technique) at its
   reference distance and recompute for the actual source-to-film
   distance with exposure_time(base_time, distance, reference_distance)
   using the inverse-square law.
4. Expose and process the film, then check the density with
   density_verdict(film_density) against the 2.0 to 4.0 band; reshoot
   if the density is out of band.
5. Read the radiograph and classify each indication with
   discontinuity_class(geometry_descriptor) as porosity, crack,
   inclusion, or slag, then disposition against the approved acceptance
   criteria.
6. Combine the checks with rt_setup_verdict(unsharpness, sensitivity,
   density); a failing check means the technique or the exposure must be
   reworked and the part reshoot before acceptance.

## Pitfalls

- Zero source-to-object distance: Ug = F * ODD / SOD is undefined at
  SOD = 0; the module raises ValueError instead of dividing by zero.
- Ignoring the object-to-detector distance: film held far off the part
  inflates unsharpness; keep the detector as close to the object as the
  geometry allows.
- Scaling exposure linearly with distance: the inverse-square law is
  quadratic, so doubling distance needs 4x the time, not 2x.
- IQI on the wrong side or wrong size: the penetrameter goes on the
  source side and its feature sizes must match the section thickness,
  or the sensitivity reading is meaningless.
- Judging the image without the density check: a radiograph can show a
  clear image while the film density is outside the band, which fails
  the technique requirements.
- Confusing film density with material density: the density verdict
  here is the optical density of the processed film, not the density of
  the part material.
- Misclassifying indications: porosity is round and globular, cracks
  are sharp and elongated; reading a crack as porosity changes the
  disposition from reject to accept.
- Verbatim clause text: AS9100 is proprietary; this skill paraphrases
  the special-process framing and references the standard only.

## Behavior contract (gate 3)

The inspection math is exercised by the gate 3 contract test:
scripts/test_radiographic_inspection.py against
scripts/radiographic_inspection.py (stdlib unittest, offline). Run:
python3 scripts/test_radiographic_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  NDT as a special process requiring controlled procedures, qualified
  personnel, and records; the formulas and technique practice above are
  common RT methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
