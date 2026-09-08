---
name: tropospheric-delay-correction
description: "Use when you must correct the GNSS range for the tropospheric delay: evaluate the saastamoinen-model delay from the surface pressure, temperature and water-vapour partial pressure, form the gravity and height factor from latitude and station height, form the zenith-hydrostatic-delay by dividing the pressure by that factor, form the zenith-wet-delay from the water-vapour partial pressure and the temperature term, sum both into the zenith total delay and map it to the slant-tropospheric-delay with cosecant elevation-mapping-function at the satellite elevation. Produces the gravity and height factor, the zenith hydrostatic delay, the zenith wet delay, the zenith total delay, the elevation mapping factor and the slant tropospheric delay in metres that gate the range correction before positioning. Trigger: saastamoinen model, tropospheric delay correction, zenith hydrostatic delay, zenith wet delay, slant tropospheric delay, elevation mapping function."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: rtca-do-229
    reference-only: true
gated: false
domain: gnc-autonomy
pack: navigation
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: gnc-autonomy
  subdomain: navigation
  tags: [tropospheric-delay-correction, saastamoinen-model, zenith-hydrostatic-delay, zenith-wet-delay, slant-tropospheric-delay, elevation-mapping-function]
  version: 0.1.0
  author: AeroSkills
---

# Tropospheric Delay Correction (gnc-autonomy/navigation/tropospheric-delay-correction)

Use when a GNSS navigation chain must correct a line-of-sight range for
the tropospheric delay before it is passed to a position fix. This leaf
implements the Saastamoinen (1973) summary-form surface-met tropospheric
delay model in pure Python, stdlib only: the gravity and height factor
from the station geodetic latitude and height, the zenith hydrostatic
delay from surface pressure, the zenith wet delay from the water-vapour
partial pressure and temperature, the zenith total delay, the cosecant
elevation-mapping-function, and the slant hydrostatic, wet and total
tropospheric delays. It pairs with
gnc-autonomy/navigation/gnss-pseudorange-positioning, which consumes the
corrected range in its iterated least squares fix, and
gnc-autonomy/navigation/ionospheric-delay-correction, which corrects the
same line of sight for the separate ionospheric member of the per-source
delay model.

## Domain quick reference

- Saturation vapour pressure (Magnus form): with t_c = T - 273.15,
  es(T) = 6.112 * exp(17.62 * t_c / (243.12 + t_c)) hPa.
- Water-vapour partial pressure from humidity: e = es(T) * RH / 100.
- Gravity/height factor: f(phi, H) = 1 - 0.00266*cos(2*phi_rad) -
  0.00028*H, phi_rad the geodetic latitude in radians, H in km. f lies
  in (0.99, 1.01) over the valid window and is always positive.
- Zenith hydrostatic (dry) delay: ZHD = 0.002277 * P / f, metres, P in
  hPa.
- Zenith wet delay: ZWD = 0.002277 * (1255/T + 0.05) * e / f, metres,
  T in kelvin, e in hPa.
- Zenith total delay: ZTD = ZHD + ZWD, metres.
- Elevation mapping factor (cosecant, plane-parallel): m(E) = 1/sin(E),
  E in degrees. m is strictly decreasing on (0, 90], m(90) = 1, and m
  grows without bound as E approaches 0.
- Slant delays: slant hydrostatic = ZHD * m(E), slant wet = ZWD * m(E),
  slant total = (ZHD + ZWD) * m(E), metres.
- Units: pressure P in hPa (1 hPa = 1 mbar), temperature T in kelvin,
  water-vapour partial pressure e in hPa, relative humidity RH in
  percent, geodetic latitude phi in degrees north in [-90, 90], station
  height H in km, satellite elevation E in degrees in (0, 90]. Valid
  surface-met window: P in [300, 1100] hPa, T in [200, 340] K, H in
  [-1, 10] km, RH in [0, 100] percent, e in [0, es(T)] hPa. Saastamoinen,
  "Contributions to the Theory of Atmospheric Refraction," Bulletin
  Geodesique 107:13-34, 1973 (and the 1972 AGU monograph chapter), and
  RTCA DO-229 frame the summary context; Hopfield 1969 is the standard
  alternative model, named only, not implemented; the relations above
  are the standard engineering method, summary-only.

## Workflow

1. Fix the surface met state: surface pressure P, temperature T and
   relative humidity RH (or the partial pressure e directly). Compute
   the saturation vapour pressure with saturation_vapor_pressure_hpa
   and the water-vapour partial pressure with water_vapor_pressure_hpa.
2. Compute the gravity and height factor with gravity_factor from the
   station geodetic latitude and height.
3. Compute the zenith-hydrostatic-delay with zenith_hydrostatic_delay_m
   from the surface pressure and the gravity/height factor.
4. Compute the zenith-wet-delay with zenith_wet_delay_m from the
   water-vapour partial pressure, temperature and the gravity/height
   factor.
5. Sum both into the zenith total delay with zenith_total_delay_m.
6. Compute the cosecant elevation-mapping-function with
   slant_mapping_factor at the satellite elevation.
7. Map the zenith terms to the slant-tropospheric-delay with
   slant_hydrostatic_delay_m, slant_wet_delay_m and slant_delay_m, the
   full saastamoinen-model pipeline from surface met state and elevation
   to the slant tropospheric delay that a consuming navigation chain
   subtracts from the GNSS range before positioning.
8. Confirm the deterministic checks with the contract test
   scripts/test_tropospheric_delay_correction.py.

## Worked example

Mid-latitude station at 40.0 deg N geodetic latitude and 0.0 km height
above sea level, standard sea-level pressure 1013.25 hPa, air
temperature 288.15 K (15 C) and relative humidity 50.0 percent,
observing a satellite at 30.0 deg elevation.

- Saturation vapour pressure: saturation_vapor_pressure_hpa(288.15) =
  17.01672024059306 hPa.
- Water-vapour partial pressure: water_vapor_pressure_hpa(288.15, 50.0)
  = 8.5083601202965298 hPa (half of es at 15 C).
- Gravity/height factor: gravity_factor(40.0, 0.0) =
  0.99953809584740594 (the cos(80 deg) = 0.173648 latitude term lowers
  f by 0.0004619 below 1).
- Zenith hydrostatic delay: zenith_hydrostatic_delay_m(1013.25, 40.0,
  0.0) = 2.3082364339940309 m (0.002277 * 1013.25 = 2.30717025 m
  divided by f 0.999538096; the classic ~2.3 m sea-level dry zenith
  delay).
- Zenith wet delay: zenith_wet_delay_m(8.5083601202965298, 288.15,
  40.0, 0.0) = 0.085387043934685852 m (the wet factor 1255/288.15 +
  0.05 = 4.4053704667707789 times e 8.5083601202965298 times 0.002277
  divided by f).
- Zenith total delay: zenith_total_delay_m(1013.25, 8.5083601202965298,
  288.15, 40.0, 0.0) = 2.3936234779287169 m.
- Elevation mapping factor: slant_mapping_factor(30.0) =
  2.0000000000000004 (= 1/sin(30 deg) = 2).
- Slant hydrostatic delay at 30 deg: slant_hydrostatic_delay_m(1013.25,
  40.0, 0.0, 30.0) = 4.6164728679880627 m.
- Slant wet delay at 30 deg: slant_wet_delay_m(8.5083601202965298,
  288.15, 40.0, 0.0, 30.0) = 0.17077408786937173 m.
- Slant total delay at 30 deg: slant_delay_m(1013.25,
  8.5083601202965298, 288.15, 40.0, 0.0, 30.0) = 4.7872469558574346 m
  (= m(30) * ZTD = 2.0000000000000004 * 2.3936234779287169).

Elevation sweep at the same met scenario (each row reports the slant
total delay and the mapping factor; the zenith delays stay fixed
because the met state does not move with elevation): 10 deg gives
13.784328232455502 m (m 5.7587704831436337, the low-elevation regime
where the correction is largest); 15 deg gives 9.2482509429728381 m (m
3.8637033051562737); 20 deg gives 6.9984868571016552 m (m
2.9238044001630876); 30 deg gives 4.7872469558574346 m (m
2.0000000000000004); 45 deg gives 3.3850947857014484 m (m
1.4142135623730951); 60 deg gives 2.7639183186415059 m (m
1.1547005383792517); 90 deg gives 2.3936234779287169 m (m 1.0, the
zenith: the slant delay collapses exactly onto ZTD).

Latitude and height variation of the gravity factor and the zenith
hydrostatic delay at P = 1013.25 hPa: phi 0.0 deg, H 0.0 km gives f
0.997340000000 and ZHD 2.313323691018 m; phi 40.0 deg, H 0.0 km gives f
0.999538095847 and ZHD 2.308236433994 m; phi 45.0 deg, H 0.0 km gives f
1.000000000000 and ZHD 2.307170250000 m (the f = 1 collapse); phi 90.0
deg, H 0.0 km gives f 1.002660000000 and ZHD 2.301049458441 m; phi 45.0
deg, H 1.0 km gives f 0.999720000000 and ZHD 2.307816438603 m; phi 45.0
deg, H 5.0 km gives f 0.998600000000 and ZHD 2.310404816743 m. The
gravity/height factor moves the dry zenith delay by only about a
centimeter across the whole latitude range and about a millimeter per
kilometer of height.

## Verification

- Confirm the worked-example chain (saturation and partial vapour
  pressure, gravity/height factor, zenith hydrostatic delay, zenith wet
  delay, zenith total delay, elevation mapping factor, slant
  hydrostatic, wet and total delays) matches the anchors above within
  1e-6 relative.
- Confirm the mapping identities: slant_mapping_factor(90.0) = 1.0
  within 1e-12, the cosecant identity m(E) * sin(E) = 1.0, m strictly
  decreasing on (0, 90], and the zenith row of the elevation sweep
  equals zenith_total_delay_m within 1e-12.
- Confirm the gravity/height identities: gravity_factor(45, 0) = 1.0
  within 1e-12, the equator and pole values 0.99734 and 1.00266, the
  linear height slope -0.00028 per km, and f stays inside (0.99, 1.01)
  over the whole valid window.
- Confirm the closed-form and scaling identities: ZHD collapses to
  0.002277 * P exactly at f = 1, ZHD scales linearly in P, ZWD scales
  linearly in e and is exactly 0 at e = 0, and ZTD equals the sum of
  its two zenith components.
- Confirm the physical sanity windows at the worked scenario (ZHD, ZWD,
  ZTD and the two slant totals within their magnitude bounds, the
  hydrostatic dominance of the dry over the wet term) and that every
  slant delay below zenith exceeds its zenith total.
- Confirm every non-physical input (elevation outside (0, 90], latitude
  or height out of window, pressure out of window, a water-vapour
  partial pressure negative or above saturation, temperature out of
  window, relative humidity out of window) raises ValueError, including
  through the full slant_delay_m pipeline, with elevation validated
  first so no ZeroDivisionError ever escapes.
- Run the contract test offline: python3
  scripts/test_tropospheric_delay_correction.py (42 tests,
  deterministic).

## Related leaves

- gnc-autonomy/navigation/ionospheric-delay-correction: owns the
  ionospheric member of the per-source delay model (the Klobuchar
  broadcast algorithm, pierce-point geometry, broadcast alpha and beta
  coefficients), never the tropospheric term computed here.
- gnc-autonomy/navigation/gnss-pseudorange-positioning: consumes the
  corrected pseudorange in its iterated least squares fix and residual
  statistics, never a per-source delay model.
- gnc-autonomy/navigation/gnss-rtk-positioning: the differential
  technique that cancels most atmospheric delay through double
  differences instead of modeling it per source.

## Pitfalls

- Feeding the zenith delay straight into the range correction: the
  model corrects a slant line of sight, so ZHD, ZWD and ZTD must always
  be mapped through slant_mapping_factor before they are subtracted
  from a real range (4.787247 m slant total against 2.393623 m zenith
  total in the worked example at 30 deg).
- Choosing an arbitrary water-vapour partial pressure instead of
  deriving it from humidity: e must come from
  water_vapor_pressure_hpa(T, RH) or be validated against the
  saturation ceiling es(T); a partial pressure above saturation is
  non-physical and rejected by zenith_wet_delay_m.
- Ignoring the gravity/height factor: it only moves the dry zenith
  delay by about a centimeter across latitude and a millimeter per
  kilometer of height, but omitting it (using P/1 instead of P/f)
  introduces a scoped, deterministic bias into the metre-level slant
  budget.
- Evaluating the model near the horizon without accounting for the
  cosecant mapping factor's rapid growth: the correction grows from
  2.394 m at zenith to 13.784 m at 10 deg elevation, the low-elevation
  regime where the summary form's plane-parallel assumption is at the
  edge of its engineering accuracy.
- Confusing this leaf with ionospheric-delay-correction: that sibling
  computes the Klobuchar broadcast pierce-point geometry for the
  ionospheric member of the per-source delay, never the Saastamoinen
  surface-met troposphere model computed here.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 scripts/test_tropospheric_delay_correction.py

The test covers the worked-example chain through every step of the
Workflow above (saturation and water-vapour partial pressure, gravity
and height factor, zenith hydrostatic delay, zenith wet delay, zenith
total delay, elevation mapping factor, slant hydrostatic, wet and total
delays), the elevation sweep with its per-row mapping factors and
monotone slant metres, the mapping and gravity/height closed-form
identities, the latitude/height variation table, the zenith scaling
identities, physical sanity bounds, determinism, and ValueError
rejection of every non-physical input including through the full
pipeline.

## Compliance

- Standards referenced, not reproduced: RTCA DO-229 frames the GNSS
  navigation context; Saastamoinen, "Contributions to the Theory of
  Atmospheric Refraction," Bulletin Geodesique 107:13-34, 1973, is
  cited by name only as the summary-form source of the relations, and
  Hopfield 1969 is named as the standard alternative, not implemented.
  Both are referenced per standards-map.yaml, never reproduced
  verbatim.
- compliance: STANDARDS-REF, gated: false.
