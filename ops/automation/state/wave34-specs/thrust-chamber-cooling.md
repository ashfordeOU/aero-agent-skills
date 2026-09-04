# Wave-34 leaf spec: thrust-chamber-cooling (propulsion, rocket pack)

- Path: skills/propulsion/rocket/thrust-chamber-cooling/
- Pack: rocket. Closest siblings: combustion-chamber-design (sizes the
  chamber volume, c-star and contraction ratio; ZERO cooling claims),
  nozzle-design (expansion and thrust only), turbine-blade-cooling
  (gas-turbine AIRFOIL cooling: air-cooled blades, cooling
  effectiveness, bleed air; never a rocket chamber wall),
  regenerative-cycle (gas-turbine regenerator, gas side, not rocket
  chamber walls). Repo-wide grep: zero hits for regenerative-cooling,
  Bartz, coolant-channel, thrust-chamber cooling, hot-wall balance.
- Standards id: ecss (reference-only; rocket-pack convention, matches
  combustion-chamber-design). Ledger Standard: ecss.
- Family: propulsion

## Claim

Perform the thermal design of a liquid rocket thrust chamber and nozzle
wall: throat-area and mass-flow anchor, the hot-gas side Bartz
convective heat transfer coefficient at the throat, the coolant-side
convective coefficient from the coolant channel flow (Dittus-Boelter),
the series wall resistance network giving the heat flux and the hot and
cold wall temperatures, the coolant mass flux required to hold a copper
wall temperature limit, and the film-cooling handoff verdict when plain
regenerative flow cannot hold the limit. Produces the heat flux,
hot/cold wall temperatures, the plain-regenerative shortfall and the
coolant mass flux required to hold the wall limit.

Does NOT do: chamber sizing and c-star (combustion-chamber-design);
nozzle expansion and thrust (nozzle-design); gas-turbine airfoil
cooling effectiveness and bleed (turbine-blade-cooling); regenerator
cycle thermodynamics (regenerative-cycle); film cooling of gas-turbine
airfoils (turbine-blade-cooling owns the turbine film-cooling context).

## Model (implement exactly)

Module constants:
- G0 = 9.80665 m/s2.
- Defaults for the worked example are function defaults where noted.

Conventions: SI throughout. The throat is the reference station
(At/A = 1 in the Bartz correlation). The recovery temperature at the
throat uses r = Pr^(1/3): T_aw = T_t (1 + r (gamma - 1)/2) with T_t =
T_c / (1 + (gamma - 1)/2) (M = 1 at the throat, T_c the chamber total
temperature).

Functions (pure stdlib):
- throat_area(diameter_m) -> pi d^2 / 4. ValueError on non-positive
  diameter.
- chamber_mass_flow(chamber_pressure_pa, throat_area_m2, cstar_m_s) ->
  mdot = Pc At / c*. ValueError on non-positive inputs.
- adiabatic_wall_temperature(chamber_temp_k, gamma, prandtl = 0.72) ->
  {throat_static_temp_k, recovery_temp_k} with the M = 1 relations
  above. ValueErrors: chamber_temp_k <= 0, gamma <= 1, prandtl <= 0.
- bartz_hot_gas_coefficient(chamber_pressure_pa, cstar_m_s,
  throat_diameter_m, mu_gas, cp_gas, prandtl_gas, sigma = 1.0) ->
  h_g = 0.026 (mu^0.2 cp / Pr^0.6) (Pc / c*)^0.8 / Dt^0.2 * sigma
  (SI form). ValueErrors on non-positive inputs, sigma <= 0.
- coolant_side_coefficient(mass_flux, hydraulic_diameter_m, mu_c,
  cp_c, k_c) -> dict {h_c, reynolds, nusselt, prandtl} by
  Dittus-Boelter: Re = G Dh / mu; Pr = cp mu / k; Nu = 0.023 Re^0.8
  Pr^0.4; h = Nu k / Dh. ValueErrors on non-positive inputs.
- wall_heat_flux(hot_coeff, cold_coeff, wall_thickness_m,
  wall_conductivity, recovery_temp_k, coolant_temp_k) -> dict
  {heat_flux_wm2, hot_wall_temp_k, cold_wall_temp_k,
  wall_delta_temp_k} with R = 1/h_g + t_w/k_w + 1/h_c; q = (T_aw -
  T_cool)/R; T_wg = T_aw - q/h_g; T_wc = T_cool + q/h_c; dT = q
  t_w/k_w. ValueErrors on non-positive inputs.
- coolant_mass_flux_for_wall_limit(hot_coeff, wall_thickness_m,
  wall_conductivity, recovery_temp_k, coolant_temp_k, wall_limit_k,
  coolant_props) -> dict {required_h_c, required_reynolds,
  required_mass_flux} solving for the h_c that holds the hot wall at
  the limit (q_lim = h_g (T_aw - T_lim); R_lim = (T_aw - T_cool) /
  q_lim; h_c_req from the series network; then invert the
  Dittus-Boelter correlation). ValueErrors on non-physical inputs
  (wall_limit above recovery temp etc.).
- film_cooling_handoff(hot_wall_temp_k, wall_limit_k) -> bool verdict
  (True when the plain-regenerative hot wall exceeds the limit).
- chamber_cooling_summary(...) -> dict with all keys above.

## Worked example

LOX/RP-1 subscale chamber: Pc = 7.0 MPa, c-star = 1750 m/s, Tc = 3500 K,
gamma = 1.2, Dt = 0.15 m, Pr_g = 0.72, mu_g = 8.0e-5 Pa s, cp_g =
2000 J/(kg K); RP-1 coolant at 300 K in rectangular channels D_h = 2 mm
with G_c = 12000 kg/m2 s, mu_c = 0.0022 Pa s, cp_c = 2000 J/(kg K),
k_c = 0.13 W/(m K); copper wall 1.5 mm, k_w = 390 W/(m K), wall limit
800 K.

Run your module and take the real outputs as assert targets, then check
the magnitude bounds (independently verified at prep):
- throat_area = pi 0.15^2/4 = 0.017671 m2.
- chamber_mass_flow = 7.0e6 * 0.017671 / 1750 = 70.6858 kg/s.
- adiabatic_wall_temperature: throat static T_t = 3500/1.1 = 3181.82 K;
  T_aw = T_t (1 + 0.72^(1/3) * 0.1) = 3467.00 K.
- bartz hot gas h_g (sigma 1) = 10682.0 W/m2K.
- coolant side: Re_c = 12000*0.002/0.0022 = 10909.1; Pr_c =
  2000*0.0022/0.13 = 33.85; Nu_c = 159.87; h_c = 10391.4 W/m2K.
- wall_heat_flux: q = 16.350 MW/m2; T_wg = 1936.3 K; T_wc = 1873.5 K;
  dT across wall = 62.9 K.
- film_cooling_handoff: T_wg 1936.3 K > 800 K limit, so True (plain
  regenerative cannot hold the limit at this mass flux).
- coolant_mass_flux_for_wall_limit: q_lim = 28.489 MW/m2 at 800 K;
  required h_c = 72968 W/m2K; required mass flux = 137168 kg/m2 s
  (Re 124698) - far above the 12000 kg/m2 s reference, quantifying the
  shortfall that motivates film cooling.

If a value falls outside its bound, your implementation has a bug: find
it before writing tests. In the SKILL.md worked example show your
module's real outputs (do not invent them).

## Validation list (contract test must include)

- ValueError: non-positive pressure/c-star/diameter/viscosities/cp/k/
  conductivity/thickness/mass flux/coolant temp; sigma <= 0; gamma <= 1.
- Mass flow: worked case 70.6858 kg/s within 1e-3; doubling pressure
  doubles mdot at fixed At and c*.
- Recovery temp: T_t = Tc/1.1 for gamma 1.2; T_aw > T_t; T_aw equals
  T_t when Pr -> 0 limit behavior (r -> 0) is not asserted numerically,
  but the ordering T_t < T_aw < T_c holds.
- Bartz scaling: h_g scales as Pc^0.8, Dt^-0.2, sigma linearly; the
  worked 10682 W/m2K within 1%.
- Coolant side: Re/Nu/Pr match the worked values to 1e-6; Nu follows
  0.023 Re^0.8 Pr^0.4.
- Series network: q equals (T_aw - T_cool)/R_total; T_wg - T_wc equals
  q t_w/k_w to 1e-9; T_wc > T_cool and T_wg < T_aw.
- Handoff: worked case reports True; with an artificially high coolant
  mass flux that holds the wall under 800 K the verdict is False.
- Determinism: identical floats run-to-run (no RNG).
- Convenience dict keys exactly as documented.

## Corpus fragment (eval/hit1-wave34-thrust-chamber-cooling.yaml)

Query 1 (copy verbatim):
  "estimate the thrust chamber cooling heat flux and wall temperature of a liquid rocket from the Bartz hot gas coefficient and the coolant side heat transfer"
  intent: "propulsion; rocket thrust chamber cooling heat flux and wall temperature from Bartz and coolant convection"
  expected_skill: "propulsion/rocket/thrust-chamber-cooling"
Query 2 (copy verbatim):
  "compute the regenerative coolant mass flux required to hold the copper wall temperature limit of a rocket nozzle throat and the film cooling handoff verdict"
  intent: "propulsion; regenerative coolant mass flux for wall limit and film cooling handoff in a rocket chamber"
  expected_skill: "propulsion/rocket/thrust-chamber-cooling"
Task ids: w34-thrust-chamber-cooling-1 and -2.

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must estimate the regenerative
cooling of a liquid rocket thrust chamber:" and include the outputs in
the Claim. First tag: thrust-chamber-cooling. Additional tags ONLY:
regenerative-cooling, bartz-heat-transfer, throat-heat-flux,
coolant-channel-sizing, copper-wall-limit, film-cooling-rocket.
NEVER single generic words (cooling, chamber, rocket, heat, wall,
copper, film). 50-150 words, <=1000 chars, no em dash, no "classified",
action verb present.

FORBIDDEN TOKENS (belong to siblings): cooling effectiveness, bleed
air, airfoil, turbine blade, film cooling of airfoils
(turbine-blade-cooling owns the gas-turbine airfoil cooling context);
c-star, chamber volume, contraction ratio as sizing outputs
(combustion-chamber-design); expansion ratio, thrust coefficient
(nozzle-design); regenerator, recuperator (regenerative-cycle). The
words "Bartz", "thrust chamber", "coolant channel", "hot wall", "wall
limit" are this leaf's own.

Tags: [thrust-chamber-cooling, regenerative-cooling,
bartz-heat-transfer, throat-heat-flux, coolant-channel-sizing,
copper-wall-limit, film-cooling-rocket]

Sibling-citation lines for Related leaves:
propulsion/rocket/combustion-chamber-design (chamber sizing sibling;
boundary: volume/c-star vs wall thermal design),
propulsion/rocket/nozzle-design (nozzle expansion sibling),
propulsion/axial-compressor/turbine-blade-cooling (gas-turbine airfoil
cooling boundary: this leaf is the rocket chamber wall analogue).

Ledger Standard: ecss.
