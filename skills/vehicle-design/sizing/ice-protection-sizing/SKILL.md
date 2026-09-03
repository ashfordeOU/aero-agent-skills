---
name: ice-protection-sizing
description: "Use when you must size the thermal ice protection system for an aircraft surface in FAR/CS 25 Appendix C continuous maximum icing: choose evaporative anti-icing, running-wet anti-icing or cyclic de-icing, compute the protected area from the icing-critical geometry, estimate the droplet catch efficiency from MVD and airspeed, compute the evaporative heat flux and running-wet surface temperature with the freezing fraction, size the electrothermal power or bleed air mass flow, and return the protect verdict with the protection mode, required power or bleed flow and surface temperature. Trigger: ice protection, anti-ice, de-ice, evaporative anti-icing, running wet, catch efficiency, protected area, heat flux, bleed air mass flow, MVD."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-25
    reference-only: true
  - id: cs-25
    reference-only: true
gated: false
domain: vehicle-design
pack: sizing
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: vehicle-design
  subdomain: sizing
  tags: [ice-protection-sizing, thermal-anti-ice-sizing, evaporative-anti-icing, running-wet-anti-ice, cyclic-de-icing, catch-efficiency, freezing-fraction, electrothermal-power, bleed-air-mass-flow, protected-area, mvd-catch-efficiency]
  version: 0.1.0
  author: Aero Agent Skills
---

# Ice Protection Sizing (vehicle-design/sizing/ice-protection-sizing)

Use when the task is sizing the steady thermal ice protection system of an
aircraft surface: choosing evaporative anti-icing, running-wet anti-icing
or cyclic de-icing, computing the two-sided protected area of the band,
estimating the droplet catch efficiency from the median volume diameter
(MVD) and airspeed, computing the evaporative heat flux, the running-wet
surface temperature and the freezing fraction, and converting the heat
flux and area into the required electrothermal power or bleed air mass
flow, closed by a protect or not protect verdict against the available
power margin. This leaf implements the steady thermal sizing model in
pure Python, stdlib only, with the FAR/CS 25 Appendix C continuous maximum
icing condition as the reference context. It pairs with engine-sizing and
nacelle-sizing (surfaces that need the protection), fuselage-sizing for
the windshield area context, and vehicle-design/conceptual/constraint-analysis
for the power offtake margin around the verdict.

## Domain quick reference

- Free-stream total temperature: T_tot = T_inf * (1 + 0.2 * M^2). The
  adiabatic wall temperature equals T_tot under a turbulent recovery
  factor of about 1 (assumption stated in the module); the kinetic
  heating rise is T_kin = T_tot - T_inf.
- Catch efficiency, preliminary reference-only correlation (module
  constants ETA_K1 = 0.55, MVD_REF = 20 micron, V_REF = 100 m/s,
  CHORD_REF = 0.5 m): eta = min(1, 0.55 * (mvd / 20)^0.6 * (v / 100)^0.4
  * (0.5 / chord)^0.5). Eta rises with the MVD and airspeed and falls
  with the chord, capped at 1.
- Water catch rate per unit span: m_wdot = eta * LWC * v * chord (kg/s
  per m span), with LWC the liquid water content (kg/m3) and chord the
  surface chord (m). The total catch over the protected segment is
  m_wdot * span.
- Protected area: A = 2 * band_fraction * chord * span (m2), the two
  sides of the leading edge band, band length chord fraction times chord
  times span.
- Freezing fraction (simplified running-wet form, T_frz = 273.15 K,
  cp_water = 4186 J/(kg K), L_f = 3.34e5 J/kg): n = min(1, max(0,
  cp_water * (T_frz - T_surf) / L_f)). Evaporative anti-ice runs n = 0;
  running wet holds part frozen for 0 < n < 1 and n = 0 at or above the
  freeze temperature.
- Convective coefficient (flat plate turbulent, reference-only):
  h_c = 0.0296 * k * Re^0.8 * Pr^(1/3) / chord with Re = rho * v * chord
  / mu, Pr = 0.72, and k, mu power-law fits in temperature (k = 0.0244 *
  (T / 273.15)^0.85, mu = 1.716e-5 * (T / 273.15)^0.75 W/(m K), Pa s).
  Convective loss: q_conv = h_c * (T_surf - T_inf).
- Evaporative loss: q_evap = m_evap_dot * L_e / A (W/m2), L_e = 2.501e6
  J/kg. Evaporative anti-icing required flux: q_req = q_conv + q_evap +
  sensible heating of the catch to T_surf, evaluated at the module
  operating skin temperature T_EVAP = 303.15 K (about 30 C).
- Running-wet anti-icing required flux at the protected limit:
  q_req = q_conv - kinetic heating contribution = h_c * (T_surf - T_inf
  - T_kin), with T_surf = T_frz (273.15 K) at the limit where the freeze
  fraction reaches zero; the sustained surface temperature for a flux q
  is T_surf = T_inf + T_kin + q / h_c.
- Cyclic de-icing: q_req = q_conv at the shed temperature T_SHED = 276.15
  K (273.15 K plus 3 K margin); no shedding dynamics.
- Required power: P_req = q_req * A (W), electrical for electrothermal;
  bleed mass flow m_dot = P_req / (cp_air * (T_bleed - T_inf)) for a
  pneumatic system, cp_air = 1005 J/(kg K).
- Verdict: protect the surface when it is on the icing-critical list and
  P_req sits within the available power margin; otherwise flag.
- Units are SI throughout: K, m, m/s, kg/m3, micron for MVD, W, W/m2,
  kg/s.

## Workflow

1. Fix the icing design point: T_inf, Mach, airspeed v, density rho,
   liquid water content LWC and median volume diameter MVD; get the total
   and kinetic temperatures with total_temperature and
   kinetic_temperature_rise.
2. Decide the surface: if it is icing critical, set the protected band
   geometry (chord, span, band fraction) and compute the two-sided area
   with protected_area.
3. Compute the catch efficiency with catch_efficiency (mvd, v, chord)
   and the catch rate per unit span with water_catch_rate; multiply by
   the span for the total catch over the segment.
4. Evaluate the running-wet limit: convective_heat_transfer_coefficient
   at the film temperature, convective_heat_loss at T_frz, then
   running_wet_heat_flux at T_frz; confirm running_wet_surface_temperature
   returns T_frz and freezing_fraction is zero at the limit.
5. For evaporative anti-icing, sum the convective, evaporative and
   sensible terms with anti_ice_evaporative_heat_flux (all catch
   evaporates, surface above freezing); for cyclic de-icing use
   de_ice_heat_flux at the shed temperature.
6. Convert to the system demand: required_power for the electrothermal
   case, bleed_mass_flow for the bleed air case at the bleed supply
   temperature.
7. Close with protect_verdict against the available power; if the
   evaporative mode exceeds the margin, rerun the running-wet and de-ice
   modes at the lower flux and re-check the freeze fraction.
8. Confirm the deterministic checks with the contract test
   scripts/test_ice_protection_sizing.py.

## Worked example

Transport wing leading edge protected band: chord c = 0.45 m, protected
segment span 12 m, band chord fraction 0.08, so A_protected = 2 * 0.08 *
0.45 * 12 = 0.864 m2. Flight M = 0.78 at T_inf = 218 K (v ~ 235 m/s,
rho ~ 0.365 kg/m3), LWC = 0.44 g/m3 (0.44e-3 kg/m3), MVD = 20 micron.

- Total temperature 218 * (1 + 0.2 * 0.78^2) = 244.53 K; kinetic rise
  26.53 K.
- Catch efficiency: eta = 0.55 * (20/20)^0.6 * (235/100)^0.4 *
  (0.5/0.45)^0.5 = 0.816, in the expected 0.5 to 0.9 band.
- Water catch rate: 0.816 * 0.44e-3 * 235 * 0.45 = 0.03797 kg/s per m
  span, 0.4556 kg/s over the 12 m segment.
- Film temperature (T_frz + T_inf) / 2 = 245.6 K gives h_c = 169.0 W/m2K
  from the flat plate correlation; q_conv at 273.15 K is 169.0 * 55.15
  = 9322.9 W/m2.
- Evaporative anti-icing at the 303.15 K operating skin: evaporating the
  full catch over the band costs q_evap = 0.4556 * 2.501e6 / 0.864 =
  1.319e6 W/m2, so q_req = q_conv + q_evap + sensible heating = 1.521e6
  W/m2 and P_req = 1.314e6 W (about 1.31 MW) for the segment. This is
  the physics of full-catch evaporation: evaporative anti-icing is only
  practical on small, high-flux surfaces such as inlet lips, and the mode
  decision below lands on running wet for the wing band.
- Running-wet limit: q_req = h_c * (273.15 - 218 - 26.53) = 4838.7 W/m2,
  P_req = 4.18 kW for the segment, T_surf = 273.15 K exactly and the
  freezing fraction is zero at the protected limit.
- Cyclic de-ice at the shed temperature 276.15 K: q_req = 9830.0 W/m2,
  P_req = 8.49 kW.
- Verdict: against a 100 kW anti-ice power budget the evaporative mode is
  flagged (1.31 MW exceeds the margin), while the running-wet mode at
  4.18 kW protects the surface; the freeze-fraction check at the limit is
  zero. The running-wet bleed demand is 4180.7 / (1005 * (450 - 218)) =
  0.0179 kg/s at a 450 K bleed supply.

All of these numbers are reproduced exactly by the contract test.

## Verification

- Confirm total_temperature(218, 0.78) = 244.53 K and the kinetic rise
  is 26.53 K.
- Confirm catch_efficiency(20, 235, 0.45) = 0.816, inside the 0.5 to 0.9
  band, rising with MVD and airspeed and falling with chord, capped at 1.
- Confirm water_catch_rate returns 0.03797 kg/s per m span and scales
  linearly in eta, LWC, v and chord.
- Confirm freezing_fraction is 0 at and above 273.15 K, between 0 and 1
  just below freezing, and 1 for a very cold surface.
- Confirm the running-wet round trip: running_wet_surface_temperature of
  running_wet_heat_flux at any surface temperature returns that
  temperature, and at the protected limit it returns 273.15 K with zero
  freeze fraction.
- Confirm required_power reproduces 4.18 kW (running wet) and 1.314 MW
  (evaporative) for the worked example band, and bleed_mass_flow the
  0.0179 kg/s running-wet bleed demand.
- Confirm every non-physical input raises ValueError: negative airspeed,
  non-positive chord, negative LWC, non-positive MVD, non-positive
  temperatures, negative heat flux, non-positive area, out-of-range
  band fraction or catch efficiency, bleed supply at or below the free
  stream temperature, and negative available power.
- Run the contract test offline: python3
  scripts/test_ice_protection_sizing.py (35 tests, deterministic).

## Related leaves

- vehicle-design/sizing/engine-sizing: the engine is the bleed source for
  a pneumatic anti-ice system; the bleed mass flow demand feeds back into
  the engine sizing offtake.
- vehicle-design/sizing/nacelle-sizing: the nacelle lip is a protected
  surface; its geometry sets the protected area for the inlet anti-ice
  calculation.
- vehicle-design/sizing/fuselage-sizing: fuselage windshield area context
  for the surfaces that need protection against ice.
- vehicle-design/conceptual/constraint-analysis: the power offtake margin
  against which the protect verdict is drawn.

## Contract test

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_ice_protection_sizing.py

The test covers the worked example values (total and kinetic temperature,
catch efficiency in the 0.5 to 0.9 band, catch rate, protected area,
convective coefficient and loss, evaporative loss and flux decomposition,
the running-wet limit flux and the round-trip identity of the surface
temperature, de-ice flux, required power for both modes and the bleed
mass flow), the correlation trends, the freezing fraction limits, and
ValueError rejection of non-physical inputs, 35 test methods in total.

## Compliance

- Standards referenced, not reproduced: far-25 and cs-25 resolve in
  standards-map.yaml, both reference-only; the FAR/CS 25 Appendix C
  continuous maximum icing condition is named and paraphrased (typical
  LWC and MVD orders), with no reproduced tables or text.
- compliance: STANDARDS-REF, gated: false.
