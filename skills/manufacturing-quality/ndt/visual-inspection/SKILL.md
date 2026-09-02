---
name: visual-inspection
description: "Use when you must plan and execute a visual inspection (VT) of an aerospace part and turn viewing geometry and lighting into inspection decisions: compute the borescope aperture ratio that sets light gathering and image brightness, size the magnification needed to resolve a target surface indication size at a given working distance, apply the inverse-square law to convert lamp intensity to illuminance and meet the lighting requirements in lux or foot-candles, size the field of view and the number of scan positions for full surface coverage, and compare measured surface indications with the acceptance criteria for a pass-fail disposition. Produces the aperture ratio, magnification, illuminance, and acceptance verdict that gate visual inspection decisions. Trigger: visual inspection, VT, borescope, aperture ratio, magnification, working distance, illuminance, lux, foot-candles, lighting requirements, surface indication, field of view, resolution limit."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: as9100
    reference-only: true
  - id: nas-410
    reference-only: true
gated: false
domain: manufacturing-quality
pack: manufacturing-quality
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: manufacturing-quality
  subdomain: ndt
  tags: [visual-inspection, aperture-ratio, magnification, lighting-requirements, surface-indications, indication-acceptance, resolution-limit, working-distance, field-of-view, illuminance]
  version: 0.1.0
  author: Aero Agent Skills
---

# Visual Inspection (manufacturing-quality/ndt/visual-inspection)

Use when the task is executing visual inspection (VT) on a part:
computing the borescope aperture ratio that sets image brightness,
sizing the magnification needed to resolve a target surface indication
size at a given working distance, converting lamp intensity to
illuminance under the inverse-square law and checking the lighting
requirements in lux or foot-candles, sizing the field of view and the
number of scan positions for full surface coverage, and comparing
measured surface indications with the acceptance criteria for a
pass-fail disposition.

## Domain quick reference

- Aperture ratio: A = D / d, with D the objective aperture diameter
  and d the working distance in meters. The ratio sets light-gathering
  power: a 6 mm objective at a 100 mm working distance gives A = 0.06,
  and holding the same optic at 50 mm doubles the ratio, which is why
  a borescope is advanced toward the surface before judging fine
  indications.
- Eye resolution: s = d * tan(theta) with theta the acuity limit of 1
  arcminute (2.909e-4 rad). At a 300 mm viewing distance the unaided
  eye resolves about 8.727e-5 m (87.3 micrometers); at the 250 mm near
  point about 7.272e-5 m (72.7 micrometers).
- Magnified resolution: s = d * tan(theta) / M. A 10x magnifier at the
  250 mm near point resolves about 7.272e-6 m (7.3 micrometers); a 5x
  system at 300 mm about 1.745e-5 m (17.5 micrometers).
- Required magnification: M = d * tan(theta) / s. Resolving a 25
  micrometer indication at 250 mm needs about 2.91x; a 50 micrometer
  indication at 300 mm about 1.75x. If the tool magnification falls
  short, the indication class is not reliably seen.
- Inverse-square law: E = I / d^2, with I the lamp intensity in
  candela and d the distance in meters. A 250 cd lamp at 0.5 m gives
  1000 lux, the level commonly required for close inspection of fine
  detail; the same lamp at 1 m gives 250 lux, too dim.
- Lamp intensity: I = E * d^2. Reaching 1000 lux at 0.5 m needs a
  250 cd lamp; reaching it at 1 m needs 1000 cd, four times the
  intensity because the light spreads over four times the area.
- Lamp distance: d = sqrt(I / E). A 250 cd lamp must sit within 0.5 m
  to hold 1000 lux on the surface.
- Units: 1 foot-candle = 10.76391 lux, so 100 fc is about 1076.4 lux
  and 1000 lux is about 92.9 fc; a 100 fc requirement is slightly
  stricter than a 1000 lux requirement on the same surface.
- Field of view: FOV = 2 * d * tan(full_angle / 2). A 40 degree
  borescope at a 50 mm working distance covers about 3.64e-2 m (36.4
  mm); at 100 mm with a 60 degree field about 1.155e-1 m (115.5 mm).
- Scan positions: n = ceil(part_area / (field_area * (1 - overlap))).
  A 0.01 m2 surface covered with a 1.6e-3 m2 field at 20 percent
  overlap needs ceil(0.01 / 0.00128) = 8 positions.
- Acceptance: an indication is acceptable when its measured length is
  at or below the acceptance limit in the engineering specification.
  A 1.2 mm indication against a 1.0 mm limit is rejected; a 0.8 mm
  indication is accepted. The limit comes from the specification, not
  from the math.

## Workflow

1. Establish the viewing geometry: working distance d, objective
   aperture D for direct or borescope viewing, and the smallest
   indication class the procedure must resolve.
2. Compute the aperture ratio with aperture_ratio (ratio = D / d) and
   confirm the optic gathers enough light for the working distance.
3. Size the magnification with magnification_for_resolution for the
   target indication size at the viewing distance, then confirm with
   resolvable_size that the available magnification actually resolves
   the class; if not, the optic or the method must change.
4. Verify the lighting: convert the procedure requirement to lux with
   foot_candles_to_lux or lux_to_foot_candles, back out the needed
   lamp intensity with intensity_for_illuminance, and confirm the lamp
   is within distance_for_illuminance so the surface holds at least
   1000 lux (or the procedure minimum) at the inspection distance.
5. Plan the coverage with field_of_view and scan_positions, applying
   the procedure overlap fraction so no seam between fields hides an
   indication.
6. Measure each surface indication, compare it with the acceptance
   criteria with acceptance_verdict, record the results, and
   disposition the part under special-process control by NAS 410
   qualified personnel.

## Pitfalls

- Confusing VT with liquid penetrant inspection: VT sees only what is
  open and visible on the surface; tight surface-breaking cracks that
  are invisible to the eye are the domain of liquid penetrant
  inspection, whose capillary action pulls penetrant into the crack.
  VT is the first pass, PT is the follow-on for tight cracks.
- Confusing VT with method selection: ndt-method-selection decides
  which method fits the defect class and material; VT is one execution
  method and cannot see internal or subsurface conditions at all.
- Forgetting the acuity limit: 10x magnification does not resolve a
  1 micrometer crack, it resolves about 7.3 micrometers at the near
  point; indications finer than the magnified resolution are rated as
  not resolvable, not as acceptable.
- Ignoring the inverse-square falloff: doubling the lamp distance
  quarters the illuminance, so a lamp that meets 1000 lux at 0.5 m
  gives only 250 lux at 1 m and the inspection is out of procedure.
- Mixing lux and foot-candles: 100 fc is about 1076 lux, not 100 lux;
  converting the procedure requirement before comparing lamps avoids
  accepting a dim setup.
- Treating the indication as the flaw: VT indication length is a
  surface projection; an indication at or near the acceptance limit
  must be dispositioned against the criteria and, where the procedure
  requires, confirmed with a higher-sensitivity method before a
  conditional acceptance.
- Skipping coverage overlap: scanning field to field without overlap
  leaves seams where indications hide; the overlap fraction closes the
  gaps at the cost of extra scan positions.
- Routing the disposition to the QMS leaves: VT is an inspection
  method, not a quality-management process; acceptance decisions still
  flow through the nonconformance-control and MRB process of the
  as9100 quality leaves when product does not conform.

## Behavior contract (gate 3)

The inspection math is exercised by the gate 3 contract test:
scripts/test_visual_inspection.py against
scripts/visual_inspection_logic.py (stdlib unittest, offline).
Run:
python3 scripts/test_visual_inspection.py

## Compliance

- Standards referenced, not reproduced: AS9100 clause 8.5.1.3 frames
  NDT as a special process requiring controlled procedures and
  qualified personnel, and NAS 410 sets the qualification and
  certification requirements for the NDT personnel who execute visual
  inspection; the aperture ratio, resolution, illuminance, coverage,
  and acceptance calculations above are common VT methodology,
  summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
