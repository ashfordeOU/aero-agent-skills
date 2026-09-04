---
name: thrust-chamber-cooling
description: "Use when you must estimate the regenerative cooling of a liquid rocket thrust chamber: the throat area and propellant mass flow anchor of the operating point, the Bartz hot gas convective coefficient at the throat, the coolant side convective coefficient from the channel flow with the Dittus-Boelter correlation, the series wall resistance network giving the heat flux and the hot and cold wall temperatures, the coolant mass flux required to hold a copper wall temperature limit, and the film cooling handoff verdict when plain regenerative flow cannot hold the limit. Produces the heat flux, hot and cold wall temperatures, the plain regenerative shortfall and the required coolant mass flux. Trigger: regenerative cooling, thrust chamber cooling, Bartz heat transfer, throat heat flux, coolant channel sizing, copper wall limit, film cooling, rocket chamber wall, throat wall temperature."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: ecss
    reference-only: true
gated: false
domain: propulsion
pack: rocket
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: propulsion
  subdomain: rocket
  tags: [thrust-chamber-cooling, regenerative-cooling, bartz-heat-transfer, throat-heat-flux, coolant-channel-sizing, copper-wall-limit, film-cooling-rocket]
  version: 0.1.0
  author: Aero Agent Skills
---

# Thrust Chamber Cooling (propulsion/rocket/thrust-chamber-cooling)

Use when the task is the thermal design of a liquid rocket thrust
chamber and nozzle wall: the throat area and mass flow anchor, the
hot-gas side Bartz convective coefficient at the throat, the
coolant-side coefficient from the regenerative channel flow, the series
wall resistance network giving the heat flux and the hot and cold wall
temperatures, and the coolant mass flux required to hold a copper wall
temperature limit before handing off to film cooling. This leaf
implements the regenerative cooling thermal balance in pure Python,
stdlib only. It pairs with propulsion/rocket/combustion-chamber-design,
which sizes the chamber and delivers the operating point, and
propulsion/rocket/nozzle-design, which takes the geometry downstream.
The gas-turbine analogue with air-cooled blades lives in
propulsion/axial-compressor/turbine-blade-cooling; this leaf is the
rocket chamber wall counterpart.

## Domain quick reference

- Throat area: A_t = pi d^2 / 4 for a circular throat of diameter d.
  The throat is the reference station of the whole thermal balance.
- Mass flow anchor: m_dot = Pc * A_t / c-star, with c-star the
  delivered characteristic velocity from the chamber design leaf.
- Recovery temperature at the throat (M = 1): T_t = T_c / (1 +
  (gamma - 1) / 2) with T_c the chamber total temperature, and
  T_aw = T_t * (1 + r * (gamma - 1) / 2) with the recovery factor
  r = Pr^(1/3). T_aw sits between T_t and T_c; the recovery
  temperature drives the hot wall balance.
- Bartz hot gas coefficient (SI form, throat station At/A = 1):
  h_g = 0.026 * (mu^0.2 * cp / Pr^0.6) * (Pc / c-star)^0.8 / Dt^0.2 *
  sigma, with sigma the transport-property correction (about 1 at the
  throat). h_g scales as Pc^0.8 and Dt^-0.2.
- Coolant side, Dittus-Boelter for the heated channel flow: Re =
  G * D_h / mu, Pr = cp * mu / k, Nu = 0.023 * Re^0.8 * Pr^0.4,
  h_c = Nu * k / D_h, with G the coolant mass flux and D_h the channel
  hydraulic diameter.
- Series wall network: R = 1/h_g + t_w/k_w + 1/h_c; q = (T_aw -
  T_cool) / R; T_wg = T_aw - q/h_g; T_wc = T_cool + q/h_c; and the
  wall drop T_wg - T_wc = q * t_w/k_w. Copper walls run at high flux,
  so the wall drop is small relative to the convective drops.
- Wall limit sizing: q_lim = h_g * (T_aw - T_lim) fixes the flux that
  holds the hot wall at the limit; R_lim = (T_aw - T_cool) / q_lim
  gives the network resistance, the required h_c follows from the
  series network, and inverting the Dittus-Boelter correlation gives
  the required Re and mass flux G.
- Film cooling handoff: when the plain-regenerative hot wall
  temperature exceeds the wall limit, regenerative flow alone cannot
  hold the copper wall and film cooling takes over.
- ECSS frames the propulsion context; the relations above are standard
  engineering methodology (Bartz, Dittus-Boelter), summary-only.

## Workflow

1. Fix the operating point from the chamber design leaf: chamber
   pressure Pc, c-star, chamber temperature T_c, gamma, throat
   diameter, and the hot gas transport properties mu, cp, Pr.
2. Anchor the flow: throat_area from the diameter and
   chamber_mass_flow from Pc, A_t and c-star.
3. Get the recovery temperature with
   adiabatic_wall_temperature(T_c, gamma, Pr_gas), the M = 1
   throat-station reference for the hot side.
4. Compute the hot gas coefficient with
   bartz_hot_gas_coefficient (sigma 1 at the throat).
5. Compute the coolant side with coolant_side_coefficient from the
   channel mass flux, D_h and the coolant properties; the dict returns
   h_c, Re, Nu and Pr.
6. Balance the wall with wall_heat_flux(h_g, h_c, t_w, k_w, T_aw,
   T_cool): q, T_wg, T_wc and the wall drop in one dict.
7. Compare T_wg with the copper wall limit using
   film_cooling_handoff; when True, quantify the fix with
   coolant_mass_flux_for_wall_limit, which returns the h_c, Re and
   mass flux needed to hold the limit.
8. For a one-call design pass, run chamber_cooling_summary with all
   inputs; it returns the flat dict of every quantity above.
9. Confirm the deterministic checks with the contract test
   scripts/test_thrust_chamber_cooling.py.

## Worked example

LOX/RP-1 subscale chamber: Pc = 7.0 MPa, c-star = 1750 m/s, Tc =
3500 K, gamma = 1.2, Dt = 0.15 m, Pr_g = 0.72, mu_g = 8.0e-5 Pa s,
cp_g = 2000 J/(kg K). RP-1 coolant at 300 K in rectangular channels
D_h = 2 mm with G_c = 12000 kg/m2 s, mu_c = 0.0022 Pa s, cp_c =
2000 J/(kg K), k_c = 0.13 W/(m K). Copper wall 1.5 mm, k_w =
390 W/(m K), wall limit 800 K. Module outputs:

- Throat area 0.017671 m2; chamber mass flow 70.6858 kg/s.
- Throat static temperature 3181.82 K; recovery temperature
  3466.998 K (about 3467 K).
- Bartz hot gas coefficient 10681.98 W/m2K, close to the 10682 anchor.
- Coolant side: Re 10909.1, Pr 33.85, Nu 159.87, h_c 10391.44 W/m2K.
- Wall balance: q = 16.350 MW/m2, T_wg = 1936.34 K, T_wc =
  1873.45 K, wall drop 62.89 K.
- Handoff verdict True: the plain-regenerative hot wall at 1936 K
  blows past the 800 K copper limit.
- To hold the limit: required h_c 72968 W/m2K, required Re 124698,
  required mass flux 137168 kg/m2 s, roughly 11 times the 12000 kg/m2 s
  reference flow, the shortfall that motivates film cooling.

## Verification

- Confirm the worked example outputs above: throat_area, mass flow,
  recovery temperature, h_g, the coolant side dict, the wall balance
  dict and the handoff verdict (True at the 800 K limit).
- Confirm the scaling laws: doubling Pc doubles m_dot at fixed A_t and
  c-star and raises h_g by 2^0.8; doubling Dt lowers h_g by 2^-0.2;
  sigma enters h_g linearly; doubling the coolant mass flux raises h_c
  by 2^0.8 through Re^0.8.
- Confirm the closed forms: Nu = 0.023 Re^0.8 Pr^0.4 and h_c =
  Nu k / D_h to float precision; q equals (T_aw - T_cool) / R_total
  and T_wg - T_wc equals q t_w / k_w.
- Confirm the ordering T_t < T_aw < T_c and T_cool < T_wc < T_wg <
  T_aw, and that feeding the required mass flux back through
  coolant_side_coefficient recovers the required h_c (round trip).
- Confirm ValueError rejection of every non-positive pressure,
  c-star, diameter, viscosity, specific heat, conductivity, thickness,
  mass flux and coolant temperature, of gamma <= 1, of sigma <= 0, of
  a wall limit at or above the recovery temperature, and of a wall
  limit below what infinite coolant convection could hold.
- Determinism: repeated runs return identical floats, no RNG.
- Run the contract test offline: python3
  scripts/test_thrust_chamber_cooling.py (34 tests, deterministic).

## Related leaves

- propulsion/rocket/combustion-chamber-design: chamber sizing sibling;
  boundary: volume/c-star vs wall thermal design.
- propulsion/rocket/nozzle-design: nozzle expansion sibling.
- propulsion/axial-compressor/turbine-blade-cooling: gas-turbine
  airfoil cooling boundary: this leaf is the rocket chamber wall
  analogue.

## Pitfalls

- Reporting the hot wall temperature without the handoff verdict: the
  plain-regenerative hot wall runs at 1936 K in the worked example,
  far past the 800 K copper limit, so film_cooling_handoff must gate
  the design — a flux number alone hides that regenerative flow cannot
  hold the wall.
- Sizing the coolant flow from the reference flux: the flux needed to
  hold the 800 K limit is 137168 kg/m2 s, roughly 11 times the 12000
  kg/m2 s reference flow — the required-flux round trip is the design
  answer, not the channel flow you started with.
- Confusing the recovery temperature with the chamber total
  temperature: the hot side balances against T_aw (3467 K in the
  example), which sits between the throat static 3181.82 K and the
  chamber total 3500 K — using T_c instead of T_aw overdrives the
  flux.
- Applying the wall-limit sizing with the limit at or above the
  recovery temperature: a wall limit at or above T_aw raises
  ValueError, as does a limit below what infinite coolant convection
  could hold — the limit must lie inside the physically reachable
  band.
- Reading the wall drop as the dominant resistance: the copper wall
  drop is 62.89 K of a 1936 K wall temperature, small against the
  convective drops, so the series network is dominated by 1/h_g and
  1/h_c — strengthening the wrong term does not cool the wall.
- Feeding a non-physical operating point: any non-positive pressure,
  c-star, diameter, viscosity, specific heat, conductivity, thickness,
  mass flux or coolant temperature, gamma <= 1 and sigma <= 0 all raise
  ValueError.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_thrust_chamber_cooling.py

The test covers the worked LOX/RP-1 balance (throat area 0.017671 m2,
mass flow 70.6858 kg/s, recovery temperature 3467 K, Bartz h_g 10682
W/m2K within 1%, coolant Re 10909 / Pr 33.85 / Nu 159.87, wall flux
16.35 MW/m2, hot wall 1936.3 K, cold wall 1873.5 K, wall drop 62.9 K),
the scaling laws (Pc^0.8, Dt^-0.2, sigma linear, Re^0.8), the series
network identities, the closed-form Nusselt relation, the wall-limit
sizing round trip (required mass flux 137168 kg/m2 s), the film
cooling handoff verdict flipping to False at a high coolant flow, and
ValueError rejection of non-physical inputs.

## Compliance

- Standards referenced, not reproduced: ECSS propulsion context per
  standards-map.yaml; the Bartz, Dittus-Boelter and series-resistance
  relations above are standard engineering methodology, summary-only.
- compliance: STANDARDS-REF, gated: false.
