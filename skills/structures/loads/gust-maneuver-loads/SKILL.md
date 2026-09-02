---
name: gust-maneuver-loads
description: "Use when you must compute aircraft structural loads from gust and maneuver conditions per FAR 25.341 and FAR 25.337: discrete 1-cosine gust load factor n = 1 + (rho0*V_e*a*K_g*U_de)/(2*W/S), gust alleviation factor K_g = 0.88*mu_g/(5.3+mu_g) with mass ratio mu_g = 2*(W/S)/(rho*cbar*a*g), limit maneuvering load factor 2.5 (normal) or 3.8 (commuter/transport) at VA with linear variation to 0 at VD, V-n diagram construction with the corner point at VA and gust lines at VB/VC/VD, envelope verdicts and margin checks. Produces the V-n diagram, gust and maneuver load factors, and pass/fail envelope margins. Trigger: gust loads, maneuver loads, gust load factor, V-n diagram, flight envelope, FAR 25.341, FAR 25.337, discrete gust, 1-cosine gust, gust alleviation factor, mass ratio, load factor, corner point, maneuvering speed, VA VB VC VD, margin check."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
gated: false
domain: structures
pack: loads
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: structures
  subdomain: loads
  tags: [gust-loads, maneuver-loads, v-n-diagram, far-25-341, far-25-337, load-factor, envelope, discrete-gust, 1-cosine, gust-alleviation-factor, mass-ratio, maneuvering-speed, corner-point, margin-check, limit-load-factor]
  version: 0.1.0
  author: Aero Agent Skills
---

# Gust and Maneuver Loads (structures/loads/gust-maneuver-loads)

Use when a structure must be sized or checked against the FAR 25 gust
and maneuver design load cases: the discrete gust load factor from a
1-cosine gust (FAR 25.341), the limit maneuvering load factor and its
speed variation (FAR 25.337 and FAR 25.333), the V-n flight envelope
with its corner point and gust lines, and the pass/fail margin of a
flight condition against that envelope. The formulas follow the
standard V-g gust analysis used in transport certification; see
references/far-25-loads.md for the paraphrased requirement summary.

## Domain quick reference

- Discrete gust load factor (FAR 25.341(b)): the airplane is subjected
  to a 1-cosine gust of design velocity U_de at equivalent airspeed
  V_e, giving

      n = 1 + (rho0 * V_e * a * K_g * U_de) / (2 * W/S)

  with rho0 = 0.002378 slugs/ft^3 (sea-level density, used with
  equivalent airspeed so the equation holds at any altitude), V_e in
  ft/s, a the lift-curve slope in 1/rad, U_de in ft/s EAS, W/S the wing
  loading in lb/ft^2. With V in knots the identical factor reads
  n = 1 + (K_g * U_de * V_KEAS * a) / (498 * W/S).
- Gust alleviation factor (FAR 25.341(b)(2)):

      K_g = 0.88 * mu_g / (5.3 + mu_g),
      mu_g = 2 * (W/S) / (rho * cbar * a * g)

  mu_g is the mass ratio at the flight-altitude density rho (sea level
  by default), cbar the mean geometric chord in ft, g = 32.174 ft/s^2.
  K_g rises from near 0 for light airplanes toward 0.88 for heavy ones.
- Design gust velocities (FAR 25.341(a), fps EAS): 66 between VB and
  VC at sea level (linear to 38 at 15,000 ft), 50 at VC at sea level
  (linear to 25 at 15,000 ft), 25 at VD at sea level (linear to 12.5 at
  50,000 ft). U_de = 0 or |U_de| > 66 fps is an invalid gust velocity.
- Limit maneuvering load factor at VA (FAR 25.337(b)(1)): 2.5 for
  normal category, 3.8 for commuter and transport category. It is
  constant up to VA and varies linearly to 0 at VD (FAR 25.333(b)).
  Negative limit: -1.0 up to VC, linear to 0 at VD (FAR 25.333(c)).
- V-n diagram: corner at VA = VS * sqrt(n_VA); positive envelope runs
  along the stall line n = (V/VS)^2 from VS to VA, the n_VA plateau
  (covered by the stall line below VA), then linear to (VD, 0); gust
  lines at VB, VC, VD from the load factor formula. Gust conditions at
  VB with the 66 fps design gust often sit above the maneuver envelope
  near the corner, so they drive the design there (envelope_margins
  reports this as gust_critical).

## Workflow

1. Gather W/S, cbar, a, rho (flight altitude) and the design speeds
   VS, VB/VC/VD.
2. Compute the alleviation factor with
   gust_alleviation_factor(ws, cbar, a, rho): mass ratio mu_g first,
   then K_g = 0.88*mu_g/(5.3+mu_g).
3. Compute the gust load factor at the speeds of interest with
   gust_load_factor(ve, ws, a, u_de, cbar=..., rho=...). Use the FAR
   25.341(a) design velocities (far25_gust_velocity) or the value from
   the applicable gust condition. A down gust takes a negative U_de.
4. Get the maneuver limit with maneuver_limit_load_factor(category)
   (2.5 normal, 3.8 commuter/transport) or its value on the linear
   segment by passing speed, va, vd.
5. Build the whole envelope with vn_diagram(ws, vs, vd, a, cbar): the
   corner at VA, the maneuver envelope polylines, and the gust lines at
   VB/VC/VD with the FAR 25.341(a) gust velocities.
6. Judge any flight condition with envelope_verdict(vn, v, n): PASS or
   FAIL with the fractional margin to the limiting side.
7. Run the margin check with envelope_margins(vn): for each gust speed,
   the maneuver envelope value, the gust load factor, and whether the
   gust condition is critical (margin below zero).

## Worked example

Typical transport at VB: W/S = 100 psf, cbar = 12.5 ft, a = 5.7/rad,
rho = rho0 = 0.002378 slugs/ft^3, V_e = 300 KEAS = 506.34 ft/s,
U_de = 50 fps EAS.

- mu_g = 2*100/(0.002378*12.5*5.7*32.174) = 36.69
- K_g = 0.88*36.69/(5.3+36.69) = 0.769
- n = 1 + 0.002378*506.34*5.7*0.769*50/(2*100) = 2.319

The gust load factor is 2.32, inside the 2-3 band that the regulatory
gust condition implies for this class; the full 66 fps design gust at
VB would give n = 2.42. The corner is VA = VS*sqrt(2.5); with
VS = 230 ft/s that is 363.7 ft/s at n = 2.5 for the normal category,
or 448.4 ft/s at n = 3.8 for a transport category airplane. A flight
condition of (400 ft/s, n = 1.8) passes with margin
(2.147 - 1.8)/2.147 = 0.16 against the positive envelope; (400 ft/s,
n = 2.3) fails. At VB the 66 fps gust line (n = 2.42) exceeds the
maneuver envelope (n = 2.01), so the gust condition is critical near
the corner and must be carried into the structural sizing.

## Verification gate

The behavior contract is scripts/test_gust_load.py against
scripts/gust_load_logic.py (stdlib unittest, offline, deterministic).
Run:

python3 scripts/test_gust_load.py

It asserts: the contract case above gives n = 2.319 within 1% of the
hand calc and inside the 2-3 range; K_g = 0.769 and mu_g = 36.69 within
1%; the maneuver limit is 2.5 (normal) and 3.8 (commuter/transport) at
VA with the linear variation to 0 at VD; the V-n diagram corner sits at
VA = VS*sqrt(n_VA) with gust lines at VB/VC/VD using the FAR 25.341(a)
gust velocities; envelope verdicts PASS and FAIL correctly including
the stall boundary below VA and the negative envelope; margin checks
flag the VB/VD gust conditions as critical; and every invalid input
(zero gust velocity, |U_de| > 66 fps, unknown category, broken speed
ordering, missing inputs) raises ValueError.

## References

- references/far-25-loads.md: paraphrased FAR 25.341, 25.337, 25.333
  and 25.335 summary (gust velocities, alleviation factor, maneuvering
  load factors, envelope shapes, design speeds).
- scripts/gust_load_logic.py: the logic module (pure Python, stdlib
  only).
- scripts/test_gust_load.py: the behavior contract test.

## Related skills

- bird-strike: another FAR 25 design load case (FAR 25.631) feeding the
  same structural sizing flow.
- load-spectrum-counting: the envelope load factors become the peak
  points of the fatigue spectrum.
- goodman-diagram: envelope load factors feed the mean/alternating
  stress check of the fatigue analysis.
- failure-criteria: margins of safety computed on the loads this skill
  produces.
- truss-analysis: member loads from the applied limit load factors.

## Compliance

- FAR 25 is US government work (public domain); summary and physics
  values only, per standards-map.yaml.
- references/far-25-loads.md is a paraphrased technical summary, not
  verbatim regulation text.
- compliance: STANDARDS-REF, gated: false.
