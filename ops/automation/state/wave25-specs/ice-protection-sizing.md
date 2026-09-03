# Wave-25 leaf spec: ice-protection-sizing (vehicle-design, priority small family)

- Path: skills/vehicle-design/sizing/ice-protection-sizing/
- Pack: sizing (existing siblings: control-surface-sizing, engine-sizing,
  fuel-tank-sizing, fuselage-sizing, landing-gear-sizing, nacelle-sizing,
  propeller-sizing, tail-sizing, tire-sizing, weight-estimation,
  wing-planform-sizing, ws-tw-trade)
- Standards ids: far-25, cs-25  (Ledger Standard: far-25, cs-25)
- Family: vehicle-design

## Claim

Size the thermal ice protection system for an aircraft surface at the
conceptual level: decide anti-ice (running wet or evaporative) versus
de-ice (cyclic shedding) operation, compute the protected area from the
icing-critical surface geometry, estimate the catch efficiency from the
droplet median volume diameter and airspeed, compute the required heat
flux for evaporative anti-icing and the running-wet surface temperature
for a given flux, size the electrical power or bleed air mass flow from
the heat flux and area, and check the anti-ice running-wet limits
against the freeze fraction. Produces the protection mode, the required
power (or bleed flow), the surface temperature, and a protect or not
protect verdict for the surface.

Does NOT do: ice accretion shape growth over time (no Messinger ice-shape
integration), de-ice boot pneumatic cycle timing beyond a simple on-off
verdict, DO-160 environmental icing test section mapping (avionics
do160/environmental-qualification owns equipment test categories), or
certification flight-test ice shapes (flight-test family). The leaf is
the steady thermal anti-ice/de-ice system sizing calculation.

## Model (implement exactly)

Steady heat balance on a protected surface in icing conditions
(FAR/CS 25 Appendix C continuous maximum icing reference; values are
reference-only typicals, paraphrase, never reproduce tables verbatim):

- Free-stream total temperature: T_tot = T_inf * (1 + 0.2 M^2).
- Adiabatic wall temperature ~ total temperature (recovery factor ~1 for
  turbulent; state assumption).
- Kinetic heating rise: T_kin = T_tot - T_inf.
- Catch efficiency: use a simplified droplet trajectory model. Provide
  eta_catch(mvd, v, chord, rho_lwc) as a monotone correlation: eta rises
  with mvd and v, falls with chord. Implement a documented simple curve
  (e.g. eta = min(1, k1 * (mvd/20)^0.6 * (v/100)^0.4 * (chord_ref/chord)^0.5))
  with module constants; label it a preliminary correlation, reference-only.
  State exact constants you use; tests assert the trend not the absolute
  value.
- Water catch rate per unit span: m_wdot = eta_catch * LWC * v * c
  (kg/s per m span), with LWC liquid water content (kg/m3) and c the
  surface chord (m).
- Freezing fraction: n = cp_w * (T_frz - T_surf) / (L_f * ... ) per the
  standard running-wet formulation. For evaporative anti-ice, n = 0 and
  all catch evaporates; for running wet, 0 < n < 1 means part freezes.
  Use n = min(1, max(0, cp_water * (T_frz - T_surf) / L_f)) as the
  simplified freezing fraction with T_surf the running-wet surface
  temperature, T_frz = 273.15 K, L_f latent heat of fusion.
- Convective heat loss: q_conv = h_c * (T_surf - T_inf) with h_c from a
  flat-plate turbulent correlation h_c = 0.0296 * k * Re^0.8 * Pr^(1/3) / c
  (reference-only standard form).
- Evaporative heat loss (evaporative anti-ice): q_evap = m_evap_dot * L_e
  / A (W/m2) with m_evap_dot the evaporated water rate and L_e latent
  heat of vaporization.
- Required heat flux: anti-ice evaporative: q_req = q_conv + q_evap
  (+ sensible heating of catch to T_surf), so the surface stays above
  freezing and the catch evaporates. Anti-ice running wet:
  q_req = q_conv - kinetic heating contribution, with T_surf >= 273.15 K
  and freeze fraction zero at the protected limit. De-ice cyclic: heat
  flux enough to shed ice in the run-back zone once a time interval has
  passed (simple: q_req = q_conv at T_surf = T_shed with a module
  constant T_shed, e.g. ~275 K + margin; no shedding dynamics).
- Required power: P_req = q_req * A_protected (W) where A_protected is
  the two-sided protected area for the surface (wing leading edge band
  length x chord fraction x span, or inlet lip area); electric power for
  electrothermal, bleed mass flow m_dot_bleed = P_req / (cp_air * (T_bleed
  - T_inf)) for bleed air with T_bleed the bleed supply temperature.
- Verdict: protect if the surface is on the icing-critical list and
  P_req is within the available power margin; else flag.

Functions:
- total_temperature(t_inf_k, mach) -> T_tot
- kinetic_temperature_rise(t_inf_k, mach) -> K
- catch_efficiency(mvd, v, chord) -> eta (dimensionless, 0..1)
- water_catch_rate(eta, lwc, v, chord) -> kg/s per m span
- freezing_fraction(t_surf_k) -> n (0..1)
- convective_heat_transfer_coefficient(v, rho, c, t_film) -> h_c (W/m2K)
- convective_heat_loss(h_c, t_surf_k, t_inf_k) -> W/m2
- evaporative_heat_loss(m_evap_dot, area) -> W/m2
- anti_ice_evaporative_heat_flux(...) -> W/m2
- running_wet_surface_temperature(q_flux, ...) -> T_surf (K)
- required_power(heat_flux, area) -> W
- bleed_mass_flow(power, cp_air, t_bleed_k, t_inf_k) -> kg/s
- protect_verdict(area, power_req, power_avail, icing_critical) -> dict
ValueError on: negative v, chord <= 0, LWC < 0, mvd <= 0, T <= 0 K,
power_avail < 0.

## Worked example

Transport wing leading edge: chord c = 0.45 m protected band, span of
protected segment 12 m, band chord fraction 0.08 -> A_protected =
2 * 0.08 * 0.45 * 12 (two sides) m2. Flight M = 0.78 at T_inf = 218 K,
v ~ 235 m/s, LWC 0.44 g/m3 (0.44e-3 kg/m3), MVD 20 micron. Compute with
your module: catch efficiency (expect ~0.5-0.9 band; assert your exact
value), water catch rate, evaporative heat flux (expect thousands of
W/m2), total required power (expect tens of kW for the segment), and
the evaporative anti-ice verdict. State real numbers from your module.

## Corpus tasks (ids w25-ice-protection-sizing-1/2)

Distinctive tokens: ice protection, anti-ice, de-ice, evaporative
anti-icing, running wet, catch efficiency, protected area, heat flux,
bleed air mass flow, electrothermal power, freezing fraction, MVD,
liquid water content, Appendix C. Avoid: icing wind tunnel test, ice
shape, DO-160 equipment category, pneumatic boot cycle timing (no other
leaf claims these, but keep the wording inside the thermal sizing claim).

1. "size the electrothermal anti-ice system for the wing leading edge
   protected band in FAR 25 Appendix C continuous icing: compute the
   droplet catch efficiency from the MVD and airspeed, the evaporative
   heat flux, and the total electrical power for the protected area"
2. "compare running wet versus evaporative anti-ice for the nacelle lip
   at the design icing point: compute the freeze fraction and the bleed
   air mass flow needed to keep the surface above freezing"

## SKILL body notes

Pair with engine-sizing/nacelle-sizing (surfaces needing protection),
fuselage-sizing (windshield area context), constraint-analysis (power
offtake margin). Worked example uses the module constants and real
outputs. Compliance: FAR/CS 25 Appendix C icing conditions referenced by
name and paraphrase, no reproduced tables or text.
