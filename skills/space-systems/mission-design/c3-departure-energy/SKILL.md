---
name: c3-departure-energy
description: "Use when you must compute the departure energy of an interplanetary mission from a circular parking orbit: the C3 characteristic energy from a target hyperbolic excess speed and the excess speed back from C3, the injection speed on the departure hyperbola at the parking orbit radius from the vis-viva integral, the injection delta-v above the circular parking speed, the circular parking speed, the parking orbit period, and the declination of the outgoing asymptote from the excess velocity vector. Produces the C3, excess speed, injection speed, injection delta-v, parking period, and asymptote declination that gate the departure-side launch-energy and injection-burn assessment. Trigger: c3 characteristic energy, hyperbolic excess, excess speed, injection delta-v, injection speed, parking orbit, escape hyperbola, asymptote declination, interplanetary departure."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: space-systems
pack: mission-design
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: space-systems
  subdomain: mission-design
  tags: [c3-departure-energy, characteristic-energy, hyperbolic-excess, injection-delta-v, parking-orbit, asymptote-declination, escape-trajectory]
  version: 0.1.0
  author: AeroSkills
---

# C3 Departure Energy (space-systems/mission-design/c3-departure-energy)

Use when the task is the departure-side energy of an interplanetary
mission leaving a circular parking orbit on an escape hyperbola: C3
characteristic energy, hyperbolic excess speed, the injection speed at
the parking radius from the vis-viva integral, the injection delta-v
above the circular parking speed, the parking period, and the
declination of the outgoing asymptote. This leaf implements the
classical two-body departure model in pure Python, stdlib only,
deterministic. It covers the departure only: the parking orbit to the
escape hyperbola asymptote. The encounter at the destination body
belongs to space-systems/orbit-mechanics/gravity-assist-swingby, the
transfer leg after escape to hohmann-transfer, and the launch geometry
of the ascent to launch-window-analysis in this pack.

## Domain quick reference

- Characteristic energy: C3 = v_inf^2, the square of the hyperbolic
  excess speed (m2/s2). C3 = 9 km2/s2 corresponds to v_inf = 3000 m/s.
- Excess speed from C3: v_inf = sqrt(C3). The two conversions form the
  round trip C3 -> v_inf -> C3, exact to float precision.
- Circular parking speed: v_c = sqrt(mu / r) at the parking radius.
- Injection speed on the departure hyperbola (vis-viva evaluated at the
  hyperbola periapsis, which is the parking radius):
  v_p = sqrt(v_inf^2 + 2*mu / r). For v_inf = 0 the hyperbola degrades
  to a parabola and v_p is the local escape speed sqrt(2*mu / r).
- Injection delta-v: dv = v_p - v_c, the burn that raises the circular
  parking speed to the hyperbolic injection speed; always positive for
  a positive excess speed.
- Parking orbit period: T = 2*pi*sqrt(r^3 / mu).
- Outgoing asymptote declination: dec = asin(vz / |v|) in degrees, for
  the excess velocity vector (vx, vy, vz).
- Convenience bundle: departure_energy_assessment returns
  c3_m2_s2, c3_km2_s2, excess_speed_m_s, circular_speed_m_s,
  injection_speed_m_s, injection_delta_v_m_s, parking_period_s and
  asymptote_declination_deg (None when no velocity components are
  given).
- Units are SI throughout: m, m/s, m2/s2, s, deg. MU_EARTH =
  3.986004418e14 m3/s2 and G0 = 9.80665 m/s2 are the module constants.
- ECSS E-ST-10C frames the mission analysis context; the relations
  above are standard engineering methodology, summary-only.

## Workflow

1. Fix the central body gravitational parameter mu (MU_EARTH default)
   and the circular parking orbit radius r in meters.
2. Set the departure energy level: target hyperbolic excess v_inf with
   c3_from_excess_speed, or target C3 with excess_speed_from_c3; the
   round trip identity excess_speed_from_c3(c3_from_excess_speed(v))
   equals v within 1e-6.
3. Compute the circular parking speed with circular_speed.
4. Compute the injection speed on the departure hyperbola at the
   parking radius with injection_speed (vis-viva), then the burn with
   injection_delta_v, which equals v_p - v_c exactly.
5. Get the parking orbit period with parking_period (about 90 min for
   a low Earth parking orbit).
6. When the outgoing excess velocity vector is known, convert it to
   the asymptote declination with asymptote_declination.
7. Bundle the assessment with departure_energy_assessment into one
   dict and report C3, excess speed, injection speed, injection
   delta-v, parking period and asymptote declination.
8. Confirm the deterministic checks with the contract test
   scripts/test_c3_departure_energy.py.

## Worked example

Earth mu = 3.986004418e14 m3/s2, parking radius 6578 km (300 km
circular), target hyperbolic excess 3000 m/s (C3 = 9 km2/s2). Real
module outputs (deterministic, printed by the module):

- C3 = 9.0 km2/s2 exactly (9000000.0 m2/s2).
- Excess round trip: excess_speed_from_c3(c3_from_excess_speed(3000))
  returns 3000.0 m/s.
- Circular parking speed: 7784.3428 m/s (spec bound 7700-7900).
- Injection speed on the departure hyperbola: 11410.1703 m/s (spec
  bound 11200-11700).
- Injection delta-v: 3625.8275 m/s (spec bound 3400-3900).
- Parking period: 5309.4775 s, about 88.5 min (spec bound 5300-5600).
- Asymptote declination for v = (2000, 2000, 1000) m/s: 19.4712 deg
  (spec bound 16-20); the vector magnitude is exactly 3000 m/s, so it
  matches C3 = 9 km2/s2.


## Pitfalls

- Mixing parking orbit radius with planet radius: every speed and
  period here is evaluated at the parking radius r you pass in, so
  injecting at the wrong altitude (or using the surface radius)
  shifts C3, v_p, dv and T together.
- Confusing C3 with injection speed: C3 = v_inf^2 is the energy at
  infinity; the injection speed at the parking radius is the larger
  vis-viva value v_p = sqrt(v_inf^2 + 2*mu/r), and the burn is the
  difference v_p - v_c, not v_inf.
- Quoting dv as the excess speed: injection delta-v always exceeds
  the hyperbolic excess (3625.8 m/s dv for a 3000 m/s excess in the
  worked example); the escape-speed floor appears only when v_inf = 0.
- Treating the asymptote declination as optional input-agnostic:
  asymptote_declination needs the actual excess velocity components
  and returns None when none are given; the zero vector raises
  ValueError, and a vector whose magnitude does not match sqrt(C3)
  points at an inconsistent energy state.
- Skipping the round-trip check: excess_speed_from_c3(c3_from_
  excess_speed(v)) must return v within 1e-6; a mismatch means a unit
  or conversion slip in the calling code.
- Forgetting the far-radius behavior: v_p approaches v_inf only as
  r grows (residual 130 m/s even at 1e9 m for a 3000 m/s excess), so
  low parking orbits never see the excess speed at injection.
## Verification

- Deterministic: no RNG anywhere; repeated runs return bit-identical
  floats for the full assessment chain.
- Round trip: excess_speed_from_c3(c3_from_excess_speed(v)) equals v
  within 1e-6 for a sweep of physical excess speeds.
- Identities: injection_delta_v equals injection_speed minus
  circular_speed exactly; v_p^2 - v_inf^2 = 2*mu/r holds at any
  radius; zero excess gives the local escape speed sqrt(2*mu/r);
  a GEO parking radius reproduces the sidereal day (86164.09 s).
- Far-radius approach: v_p approaches v_inf as the radius grows; at
  1e9 m the residual v_p - v_inf is 130.05 m/s for the 3000 m/s
  excess (2*mu/r is still about 8.9% of v_inf^2), shrinks monotonically
  and drops below 1 m/s by 1e12 m. The contract test asserts the
  sub-50 m/s bound at 1e9 m for the 12 km/s excess, where 2*mu/r is
  under 1% of v_inf^2 and the exact residual is 33.2 m/s.
- ValueError rejection: negative excess speed, negative C3, mu <= 0,
  radius <= 0 in every function, and the zero velocity vector in
  asymptote_declination.
- The convenience dict contains exactly the eight documented keys.

## Related leaves

- space-systems/mission-design/mission-delta-v-budget: consumes the
  injection delta-v inside a full mission delta-v budget.
- space-systems/mission-design/launch-window-analysis: launch site
  geometry and ascent timeline for the same interplanetary mission.
- space-systems/orbit-mechanics/hohmann-transfer: sizes the transfer
  leg that follows the departure escape.
- space-systems/orbit-mechanics/gravity-assist-swingby: the encounter
  phase after the cruise leg, outside this leaf's departure-side
  claim.
- space-systems/mission-design/entry-descent-landing: the arrival end
  of the mission.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_c3_departure_energy.py

Run from the repo root:

    python3 skills/space-systems/mission-design/c3-departure-energy/scripts/test_c3_departure_energy.py

The test covers the worked example outputs against their spec
magnitude bounds and the module's real values, the C3/excess round
trip, the circular and injection speeds, the injection delta-v
identity, the vis-viva far-radius approach, the parking period, the
asymptote declination, the convenience dict keys, determinism, and
ValueError rejection of every non-physical input (35 tests).

## Compliance

- Standards referenced, not reproduced: ECSS E-ST-10C (space
  engineering) frames the mission analysis context; the C3 and
  vis-viva relations above are standard two-body engineering
  methodology, summary-only per standards-map.yaml.
- compliance: STANDARDS-REF, gated: false.
