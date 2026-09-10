---
name: e1004-gravity
description: "Use when you need to define the gravity environment (magnitude and gradient) for a mission orbit under ECSS-E-ST-10-04C: select and apply the Earth gravity model appropriate to the orbit regime (point-mass/low-degree geopotential vs. high-degree geopotential, plus third-body and solid-Earth-tide perturbation terms), compute the gravitational acceleration magnitude and radial gravity gradient at the mission orbit's altitude, verify the mission's stated altitude falls inside the selected model's validity range, and check that the perturbation terms included for the case cover what the orbit regime and mission duration require. Trigger: gravity model, geopotential, Earth gravity field, third-body perturbation, solid Earth tide, gravity gradient, gravitational acceleration, mission orbit, e-st-10-04, ecss, space environment."
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
  tags: [ecss, e-st-10-04c, gravity, geopotential, third-body, tides, gravity-gradient, space-environment]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Gravity Environment (space-systems/ecss/e1004-gravity)

Use when the task is selecting and applying a gravity model under
ECSS-E-ST-10-04C clause 4.2, to define the gravity environment
(magnitude and gradient of the gravitational acceleration, plus the
perturbation terms that must be included) for a mission orbit.

## Domain quick reference

- The gravity environment for an Earth-orbiting mission is built from
  three ingredients: the Earth gravity field itself (point-mass term
  plus the oblateness/higher-degree geopotential terms), third-body
  perturbations (Sun and Moon gravitational attraction), and
  solid-Earth-tide perturbations (periodic deformation of the Earth's
  mass distribution). Which of these matter, and to what degree,
  depends on the orbit regime and how long the mission needs the
  gravity model to stay valid.
- Low Earth orbit (LEO) altitudes sit close enough to the Earth's
  non-spherical mass distribution that a high-degree geopotential
  model is needed to capture short-period perturbations; third-body
  and tidal effects are comparatively small there unless the mission
  duration is long enough for them to accumulate.
- Higher orbit regimes (MEO, GEO, and highly-elliptical orbits, HEO)
  sit far enough from Earth that a low-degree geopotential (dominated
  by the J2 oblateness term) is normally sufficient for the Earth
  field itself, but third-body attraction from the Sun and Moon
  becomes a dominant perturbation there and must always be included.
- Solid-Earth-tide perturbation becomes significant relative to the
  other terms only once a mission's required validity duration is
  long enough for the periodic tidal deformation to accumulate into a
  non-negligible effect on the orbit -- for a short-duration mission
  it can usually be neglected.
- The gravitational acceleration magnitude at a given orbital radius
  follows the point-mass relation g = GM/r^2 (GM = Earth's
  gravitational parameter, r = distance from Earth's center); the
  first-order radial gravity gradient (how quickly g changes with
  radius) follows dg/dr = -2*GM/r^3, and its magnitude is what drives
  gravity-gradient torque and tidal-stretching effects on a spacecraft
  structure.
- Every gravity model has a validity range: a geopotential model
  tuned for one orbit regime's altitude band should not be applied
  outside that band without re-justification.

## Workflow

1. For each mission orbit case, record its orbit regime ("leo", "meo",
   "geo", or "heo"), the orbit's altitude above the Earth's surface
   (meters), the mission duration the gravity environment must remain
   valid for (days), and the set of perturbation terms the analysis
   currently includes (from: earth_geopotential_high_degree,
   earth_geopotential_low_degree, third_body, solid_earth_tide).
2. Select the applicable Earth gravity model from the orbit regime
   (high-degree geopotential for LEO; low-degree/J2-dominant
   geopotential for MEO, GEO, and HEO).
3. Determine the minimum perturbation term set the orbit regime and
   mission duration require: MEO/GEO/HEO always require third-body
   terms in addition to the geopotential term; any regime whose
   mission duration exceeds the tide-accumulation threshold also
   requires the solid-Earth-tide term (and, for LEO, the third-body
   term as well, since long-duration LEO lifetime/station-keeping
   analyses can no longer neglect it).
4. Check that the case's included perturbation terms are a superset of
   the required term set; flag any missing term rather than silently
   dropping it from the environment definition.
5. Verify the case's stated altitude falls inside the selected
   gravity model's validity altitude range for that orbit regime; flag
   a case whose altitude does not match its declared regime.
6. Compute the gravitational acceleration magnitude and the radial
   gravity gradient magnitude at the case's orbital radius (Earth
   radius plus altitude) from the point-mass relations.
7. Mark the case compliant only when its perturbation term coverage is
   adequate and its altitude is inside the validity range; roll every
   case's compliance into the assessment record and do not close the
   gravity environment definition while any case remains
   non-compliant.

## Pitfalls

- Applying a low-degree (J2-only) geopotential model to a LEO mission,
  understating the short-period perturbations that a high-degree
  geopotential model would capture.
- Omitting third-body (Sun/Moon) perturbation terms for MEO, GEO, or
  HEO missions, where they are a dominant rather than secondary
  effect, not an optional refinement.
- Neglecting solid-Earth-tide accumulation for a long-duration mission
  because the per-orbit effect looks small in isolation, when it
  accumulates into a non-negligible perturbation over the mission
  duration.
- Reusing a gravity model's validity range from one orbit regime for a
  case whose stated altitude actually belongs to a different regime,
  which produces a gravity environment that looks defined but is
  actually invalid at the case's true altitude.
- Confusing the gravitational acceleration magnitude with the gravity
  gradient magnitude -- the environment definition (magnitude,
  gradient) requires both, since the gradient drives gravity-gradient
  torque and structural tidal-stretching assessments that the
  magnitude alone does not capture.

## Behavior contract (gate 3)

The model-selection, perturbation-term-coverage, altitude-validity,
magnitude, and gradient logic is exercised by the gate 3 contract
test: scripts/test_e1004_gravity.py against
scripts/e1004_gravity_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1004_gravity.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
