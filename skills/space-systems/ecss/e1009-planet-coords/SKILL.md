---
name: e1009-planet-coords
description: "Use when define a planetary body-fixed coordinate frame per ECSS-E-ST-10-09C §5.4.6: retrieve WGCCRE rotation-model coefficients for the target body, compute the right ascension and declination of the North Pole in ICRF from the polynomial evaluated at the given epoch, determine the prime-meridian angle W, validate that pole angles fall within physical bounds, derive the pole unit vector in ICRF Cartesian form, and verify the prime-meridian wraps to [0°, 360°). Apply to any Solar System body that carries a WGCCRE entry—planets, dwarf planets, or major moons. Trigger: ecss, e-st-10-system-scope, planet-coords, wgccre, body-fixed-frame, pole-orientation, prime-meridian, rotation-elements, icrf."
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
  tags: [ecss, e-st-10-system-scope, planet-coords, wgccre, body-fixed-frame, pole-orientation, prime-meridian, rotation-elements]
  version: 0.1.0
  author: Aero Agent Skills
---

# ECSS Coordinate Systems — Planetary Body-Fixed Frames (space-systems/ecss/e1009-planet-coords)

Use when the task is to define the body-fixed coordinate frame for a Solar
System body in line with ECSS-E-ST-10-09C §5.4.6, which anchors planetary
frame definitions to the IAU Working Group on Cartographic Coordinates and
Rotational Elements (WGCCRE) conventions. The frame is specified by three
time-varying quantities: the ICRF right ascension and declination of the
body's North Pole and the prime-meridian angle, all evaluated as polynomials
at the required epoch.

## Domain quick reference

- ECSS-E-ST-10-09C §5.4.6 mandates use of WGCCRE rotation models for
  planetary and major-moon body-fixed frames. Each model expresses pole
  orientation (right ascension α₀, declination δ₀ in ICRF) and prime-
  meridian location (W) as polynomial functions of time, updated
  periodically by the IAU.
- The North Pole is defined as the rotation-axis pole for which the
  body appears to rotate counterclockwise when viewed from above; for
  retrograde rotators (e.g. Venus) the pole lies below the ecliptic
  plane and W advances at a negative rate.
- Time is parameterised in two complementary variables: T is the number
  of Julian centuries elapsed since J2000 (used in the α₀ and δ₀ linear
  terms), and d is the number of days since J2000 (used in the prime-
  meridian rate W₁·d to track the faster daily rotation).
- The prime meridian angle W is measured eastward along the body's
  equator from the body's ascending node on the ICRF equatorial plane
  to the adopted zero-longitude feature (e.g. a crater, a surface mark),
  and must always be reduced to the interval [0°, 360°).
- A body not listed in the current WGCCRE report has no ECSS-sanctioned
  body-fixed frame; a mission using such a body must propose and register
  a provisional frame before mission-critical coordinate work proceeds.

## Workflow

1. Identify the target body and locate its WGCCRE rotation-model entry
   (α₀, α₁, δ₀, δ₁, W₀, W₁ and any periodic terms). Reject a body
   with no WGCCRE entry and flag it as requiring a provisional frame.
2. Convert the required epoch to days from J2000 (d) and to Julian
   centuries from J2000 (T = d / 36 525). Verify the epoch is within the
   validity range of the rotation model (typically within ±200 years of
   J2000).
3. Evaluate the pole right ascension: α = α₀ + α₁·T (add any body-
   specific periodic terms if documented in the WGCCRE entry).
4. Evaluate the pole declination: δ = δ₀ + δ₁·T (same periodic-term
   treatment).
5. Evaluate the prime-meridian angle: W = (W₀ + W₁·d) mod 360. Confirm
   the result is in [0°, 360°); apply a correction if not.
6. Validate physical bounds: α must be in [−180°, 360°] and δ in
   [−90°, 90°]; any violation indicates a model-coefficient error or
   an epoch far outside the validity range.
7. Derive the pole unit vector in ICRF Cartesian form:
   x = cos δ · cos α, y = cos δ · sin α, z = sin δ. This vector is the
   body frame's Z-axis expressed in ICRF.
8. Record the result (body name, epoch, α, δ, W, pole unit vector) in
   the mission coordinate-system register and confirm it matches any
   existing entry for the same body and epoch within the agreed
   numerical tolerance.

## Pitfalls

- Confusing the T (century) and d (day) time arguments — the pole terms
  use T (centuries) while the prime-meridian rate uses d (days). Swapping
  them produces an error of roughly four orders of magnitude in the
  prime-meridian position.
- Omitting body-specific periodic terms listed in the WGCCRE report —
  for bodies such as Jupiter and its moons, the periodic contributions
  can exceed several degrees and are not negligible for any precision
  work.
- Treating retrograde rotators (negative W₁) as prograde — the prime
  meridian advances in the opposite sense, so the body-fixed X-axis
  points in the opposite direction relative to the ascending node.
- Applying a single static value of α₀ and δ₀ across a multi-year
  mission without re-evaluating at each required epoch — pole precession
  accumulates at roughly 0.01°–0.06° per year for the terrestrial
  planets and must be re-evaluated for each independent coordinate
  computation.
- Using the body-fixed frame without registering it in the mission
  coordinate-system register — downstream reference-frame transforms
  become untraceable and errors propagate silently.

## Behavior contract (gate 3)

The body validation, time parameterisation, pole evaluation, prime-
meridian wrapping, range checking, and pole-unit-vector logic are
exercised by the gate 3 contract test:
scripts/test_e1009_planet_coords.py against
scripts/e1009_planet_coords_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_e1009_planet_coords.py

## Compliance

- ECSS standards are freely downloadable (ESA); cite the source and
  paraphrase per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
