# FAR 25.341, 25.337, 25.333, 25.335 - gust and maneuver loads summary

Paraphrased technical summary of the discrete gust and maneuvering load
requirements of 14 CFR Part 25 (Airworthiness Standards: Transport
Category Airplanes). Paraphrase only, no verbatim regulation text; the
regulation is US government work (public domain). The formulas below
are the standard V-g gust analysis form used throughout transport
certification practice.

## FAR 25.341 - Gust and turbulence loads

Discrete gust design criterion (a 1-cosine gust shape is the design
idealization). For each speed and altitude condition the airplane is
subjected to a discrete vertical gust of design velocity U_de, and the
resulting limit load factor is

    n = 1 + (rho0 * V_e * a * K_g * U_de) / (2 * W/S)

with rho0 the sea-level standard density (0.002378 slugs/ft^3), V_e the
equivalent airspeed in ft/s, a the lift-curve slope per radian, U_de in
ft/s EAS, and W/S the wing loading in lb/ft^2. Using equivalent
airspeed with the sea-level density makes the equation valid at any
altitude. With V in knots equivalent airspeed the same factor reads

    n = 1 + (K_g * U_de * V_KEAS * a) / (498 * W/S)

(498 = 2/(rho0 * 1.68781) absorbs the knot-to-ft/s conversion).

Design gust velocities (fps EAS), with linear interpolation between
the altitude points:

| Speed region | Sea level | Altitude floor | Floor value |
|---|---|---|---|
| Between VB and VC | 66 | 15,000 ft | 38 |
| At VC | 50 | 15,000 ft | 25 |
| At VD | 25 | 50,000 ft | 12.5 |

The gust alleviation factor accounts for the dynamic response of the
airplane (the gust is not felt instantaneously; the airplane responds
as a mass-spring system):

    K_g = 0.88 * mu_g / (5.3 + mu_g)

    mu_g = 2 * (W/S) / (rho * cbar * a * g)

mu_g is the mass ratio evaluated at the flight altitude density rho
(slugs/ft^3), cbar the mean geometric chord (ft), g = 32.174 ft/s^2.
K_g is bounded below 0.88 and rises toward it as the airplane gets
heavier (larger mass ratio). The FAR 25.341(b)(2) definitions of K_g
and mu_g are used verbatim in the skill implementation.

## FAR 25.337 - Limit maneuvering load factors

The positive limit maneuvering load factor at the design maneuvering
speed VA may not be less than 2.5 for normal category airplanes, and
may not be less than 3.8 for commuter category airplanes and for
transport category airplanes with a maximum weight above 50,000 lb.
The negative limit maneuvering load factor may not be less than -1.0.

The limit load factor envelope shape is set by FAR 25.333:

- Positive: the limit maneuvering load factor is constant at the VA
  value up to VA and varies linearly with speed from the value at VA to
  zero at VD.
- Negative: -1.0 at speeds up to VC, varying linearly to zero at VD.
- Below VA the achievable load factor is bounded by the stall boundary
  n = (V/VS)^2, so the usable positive envelope follows the stall line
  from (VS, 1.0) to (VA, n_VA).

## FAR 25.335 - Design airspeeds (summary)

- VS: stalling speed, the 1g stall reference.
- VA: design maneuvering speed, VS * sqrt(n_VA), the speed at which the
  limit maneuvering load factor can just be reached before stall.
- VB: design speed for maximum gust intensity, of the order of 1.8 VS
  for typical transports (the skill default; the corner rises with the
  3.8g category).
- VC: design cruising speed.
- VD: design diving speed, the upper bound of the envelope; both the
  maneuver line and the negative line reduce to zero load factor there.

## Skill mapping

| Requirement | Skill function |
|---|---|
| FAR 25.341(b) load factor | gust_load_factor |
| FAR 25.341(b)(2) K_g, mu_g | gust_alleviation_factor, gust_mass_ratio |
| FAR 25.341(a) gust velocities | far25_gust_velocity |
| FAR 25.337 limit maneuvering factors, 25.333 variation | maneuver_limit_load_factor |
| Envelope construction | vn_diagram |
| Condition check and margins | envelope_verdict, envelope_margins |
