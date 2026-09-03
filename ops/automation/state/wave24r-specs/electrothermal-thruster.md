# Wave-24R leaf spec: electrothermal-thruster (propulsion)

- Path: skills/propulsion/electric/electrothermal-thruster/
- Pack: electric (existing: gridded-ion-thruster, hall-thruster)
- Standards ids: ecss  (Ledger Standard: ecss)
- Family: propulsion

## Claim

Electrothermal thruster (resistojet and arcjet) performance analysis
for spacecraft electric propulsion: convert input electrical power into
propellant enthalpy, expand the heated propellant through a nozzle, and
compute thrust, exhaust velocity, specific impulse, thrust efficiency,
and the power-to-thrust ratio. Produces the performance point plus a
power budget decomposition (heating loss, frozen-flow loss, nozzle
efficiency).

Does NOT do: electrostatic thrusters (gridded-ion-thruster, hall-thruster
own those; no ion acceleration, no Child-Langmuir), thruster system
sizing over a mission (delta-v/propellant belongs to mission-delta-v
leaves). This leaf is the single operating point of a resistojet or
arcjet.

## Model (implement exactly; module constants)

Heating: electrical power P_elec (W) heats propellant (default NH3 or N2;
use a propellant-specific heat capacity cp input, J/(kg K)) from the
plenum temperature T_in (K) to the chamber/plenum temperature T_0 (K):
- Useful heating power P_heat = eta_heat * P_elec  (eta_heat input,
  default 0.85 resistojet / 0.7 arcjet family).
- Mass flow mdot = P_heat / (cp * (T_0 - T_in))  (kg/s).
Exhaust velocity (ideal, nozzle expansion to vacuum):
- v_e = sqrt(2 * cp * eta_nozzle * T_0 * (1 - (p_e/p_0)^((gamma-1)/gamma)))
  with p_e = 0 (vacuum) this reduces to v_e = sqrt(2 * cp * eta_nozzle *
  T_0). Use the vacuum form as the default; gamma is the propellant
  specific-heat ratio (input, default 1.3 for the working-gas family).
- eta_nozzle input (default 0.9); document that real resistojets show
  frozen-flow losses and finite-area-ratio losses folded into
  eta_nozzle.
Thrust and Isp:
- Thrust F = mdot * v_e + (p_e - p_a) * A_e; in vacuum with p_e = 0 the
  pressure term vanishes in the ideal model (assumption documented:
  fully expanded vacuum nozzle), so F = mdot * v_e.
- Specific impulse Isp = v_e / g0.
Efficiency decomposition:
- Thrust efficiency eta_t = F^2 / (2 * mdot * P_elec) (jet power over
  input power); check eta_t <= eta_heat * eta_nozzle (identity).
- Thrust-to-power F/P = F / P_elec (mN/kW for reporting).
Propellant selection support: pure-function table of cp and gamma for
NH3, N2, H2, Xe? (Xe is electrostatic territory; keep NH3, N2, H2, and
He as the electrothermal working fluids; module dict with values: NH3
cp 2090 J/(kg K) at 300 K, gamma 1.31; N2 cp 1040, gamma 1.40; H2 cp
14300, gamma 1.41; He cp 5190, gamma 1.67 - state they are 300 K
values, reference-only).
Typical operating bands (module constants, used for sanity verdicts):
resistojet Isp 200-350 s, arcjet Isp 400-700 s (documented as typical
published bands; the leaf does not enforce them, it reports whether the
point lies in the band).

## Functions

- propellant_properties(name) -> (cp, gamma) or ValueError for unknown
- useful_heating_power(eta_heat, p_elec)
- mass_flow_from_heating(p_heat, cp, t0, t_in)
- exhaust_velocity_ideal(cp, eta_nozzle, t0)  (vacuum form)
- thrust_from_mass_flow(mdot, v_e)
- specific_impulse(v_e)
- thrust_efficiency(f, mdot, p_elec)
- thrust_to_power(f, p_elec)
- operating_band_verdict(isp, thruster_family) -> str
- electrothermal_performance(p_elec, t0, t_in, propellant,
  eta_heat=..., eta_nozzle=..., family='resistojet') -> summary dict
ValueError on: p_elec <= 0, t0 <= t_in, t_in <= 0, cp <= 0,
eta outside (0,1], gamma <= 1, unknown propellant, non-finite inputs.

## Worked example

Resistojet: P_elec = 1000 W, propellant NH3, T_0 = 1200 K, T_in = 300 K,
eta_heat = 0.85, eta_nozzle = 0.9. Anchors (compute exact from your
module):
- P_heat = 850 W; mdot = 850 / (2090 * 900) ~= 4.52e-4 kg/s.
- v_e = sqrt(2 * 2090 * 0.9 * 1200) ~= 2125 m/s.
- F ~= 0.96 N (960 mN); Isp ~= 217 s (in the 200-350 s resistojet band).
- eta_t = F^2/(2*mdot*P_elec) ~= 0.765 <= 0.85*0.9 = 0.765 (identity
  equality in the ideal model; assert within 1e-6).
Test identities: thrust efficiency equals eta_heat*eta_nozzle (ideal
model); Isp scales with sqrt(T_0) at fixed cp; F scales linearly with
mdot; higher T_0 gives higher Isp; eta bounds; ValueError rejections.

## Corpus tasks (2 tasks, ids w24r-electrothermal-thruster-1/2)

Distinctive tokens: electrothermal-thruster, resistojet, arcjet,
heated-propellant, power-to-thrust. Avoid: "ion thruster", "hall
thruster", "child-langmuir", "grid", "perveance" (siblings).

1. "analyze the resistojet operating point for the smallsat: with 1 kW
   input heating ammonia propellant from 300 K to 1200 K at 85 percent
   heating efficiency, compute the mass flow, exhaust velocity, thrust,
   specific impulse, and thrust-to-power ratio"
2. "compare the electrothermal-thruster family options for the station
   keeping burn: run the resistojet and arcjet performance models on the
   same 500 W input and report which gives the higher specific impulse
   and whether each point lies in its typical operating band"

## SKILL body notes

Pair with gridded-ion-thruster and hall-thruster (electrostatic
siblings: same electric-propulsion power train, different acceleration
mechanism) and the ECSS context. Worked example uses the values above.
Compliance: ECSS electric propulsion standards referenced by name only.
