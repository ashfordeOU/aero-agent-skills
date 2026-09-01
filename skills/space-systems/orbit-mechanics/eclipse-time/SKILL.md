---
name: eclipse-time
description: "Use when you must compute the time a spacecraft spends inside the earth shadow during each orbit: derive the beta angle of the orbit plane relative to the sun vector from the inclination, the right ascension of the ascending node, and the sun position, then evaluate the shadow fraction from the beta angle and the orbit radius and multiply by the orbital period to produce the eclipse time and the daylight fraction. Produces the beta angle in degrees, the shadow fraction, and the eclipse time in seconds that gate eclipse duration inputs for spacecraft power and thermal sizing. Trigger: eclipse time, earth shadow, beta angle, shadow fraction, orbit plane, sun vector, eclipse duration."
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
  subdomain: orbit-mechanics
  tags: [eclipse-time, earth-shadow, beta-angle, shadow-fraction, eclipse-duration, orbit-plane, sun-vector, orbit-period]
  version: 0.1.0
  author: AeroSkills
---

# Eclipse Time (space-systems/orbit-mechanics/eclipse-time)

Use when the task is eclipse geometry for a circular Earth orbit:
the beta angle of the orbit plane relative to the sun vector, the
shadow fraction, and the eclipse time that feeds power and thermal
sizing.

## Domain quick reference

- Units: altitude in km in, meters internally; angles in radians,
  degrees for display; period and eclipse time in seconds; fractions
  dimensionless in [0, 1].
- Gravitational parameter mu = 3.986004418e14 m^3/s^2, mean Earth
  radius Re = 6371000 m.
- Orbital period: T = 2 pi sqrt(a^3 / mu) with a = Re + altitude.
  At 500 km altitude T = 5668 s (94.5 min); at GEO (35786 km) T =
  86142 s (23.93 h).
- Beta angle from orbit and sun geometry: sin(beta) = sin(i) cos(delta)
  sin(RAAN - alpha) + cos(i) sin(delta), with i the inclination, delta
  the sun declination, alpha the sun right ascension. Range [-90, 90]
  deg.
- Shadow fraction (spherical Earth, umbra only): f = arccos(
  sqrt(r^2 - Re^2) / (r cos(beta))) / pi while |beta| < beta_max =
  arcsin(Re / r); f = 0 otherwise. beta_max is about 68 deg at 500 km
  and about 8.7 deg at GEO.
- Eclipse time = shadow fraction times orbital period. At 500 km with
  beta = 0 the eclipse is about 2142 s (35.7 min); the GEO maximum is
  about 4160 s (69 min).
- Daylight fraction = 1 - shadow fraction.

## Workflow

1. Take the circular orbit altitude in km and the orbit and sun
   angles: inclination, RAAN, sun declination, sun right ascension.
2. Compute the orbital period with orbital_period.
3. Compute the beta angle with beta_angle (radians) or
   beta_angle_deg (degrees).
4. Evaluate the shadow fraction with shadow_fraction and the eclipse
   time with eclipse_time.
5. Pack the full solution with eclipse_properties for the power and
   thermal sizing handoff.
6. Gate on the eclipse duration band: a beta angle above beta_max
   means a fully sunlit orbit with zero eclipse time.

## Pitfalls

- Feeding degrees into radian-based functions; beta_angle_deg exists
  for degree input.
- Using a negative altitude or an orbit radius at or below Re, which
  raise ValueError.
- Forgetting the beta_max cutoff: beyond about 68 deg at 500 km the
  orbit is fully sunlit and the shadow fraction is exactly zero.
- Confusing the beta angle with the sun elevation above the local
  horizon; the beta angle is an orbit-plane-to-sun-vector angle.
- Treating the geometric umbra estimate as exact; real eclipse
  durations shift slightly with penumbra, Earth oblateness, and the
  finite sun radius.

## Behavior contract (gate 3)

The period, beta angle, shadow fraction, and eclipse time logic is
exercised by the gate 3 contract test: scripts/test_eclipse_time.py
against scripts/eclipse_time_logic.py (stdlib unittest, offline). Run:
python3 scripts/test_eclipse_time.py

## Compliance

- Standards referenced, not reproduced: ECSS series text is copyright
  ESA; the beta angle and shadow fraction geometry are common
  astrodynamics, summary-only per standards-map.yaml (ecss is a free
  ESA download).
- compliance: STANDARDS-REF, gated: false.
