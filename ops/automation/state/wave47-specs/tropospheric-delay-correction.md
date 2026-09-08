# Wave-47 leaf spec: tropospheric-delay-correction (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/tropospheric-delay-correction/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-doppler-velocity-
  positioning, gnss-pseudorange-positioning, gnss-raim-fde,
  gnss-rtk-positioning, inertial-navigation, ins-gnss-integrated-filter,
  ionospheric-delay-correction, kalman-filter-design, navigation-frames,
  terrain-referenced-navigation, tightly-coupled-ins-gnss; the quoted
  fences below are the nearest owners this leaf must not duplicate:
  ionospheric-delay-correction owns the per-source ionospheric member of
  the delay-model seam, gnss-pseudorange-positioning owns the position
  fix, gnss-rtk-positioning owns the differential technique).
- Provenance: wave-47 probe receipt task-3 GO rank 1 (gates (a)-(f)
  verified FRESH at wave-47 HEAD), gates (a), (b), (d) verbatim: "(a)
  Zero-owner greps, whole skills/ tree, FRESH: `rg -i -l
  'saastamoinen|hopfield|zenith-delay' skills/ -g 'SKILL.md'` -> 0
  hit(s) (exit 1). Corpus scan `rg -ic 'tropospher|saastamoinen|
  hopfield' eval/hit1-corpus.yaml` -> 0 hits. The only 'tropospher'
  owners tree-wide are atmosphere-STATE leaves (cross-cutting/
  units-atmos/isa-atmosphere, density-altitude, propulsion/vehicle-
  sizing consumers of ISA tables) - none models radio-wave propagation
  delay; no gnc-autonomy SKILL.md contains the word at all." "(b)
  Sibling fences (FRESH reads, verbatim): ionospheric-delay-correction
  body lines 32-37: 'It pairs with gnc-autonomy/navigation/gnss-
  pseudorange-positioning, which consumes the corrected pseudorange in
  its iterated least squares fix, and gnc-autonomy/navigation/gnss-
  carrier-smoothing, whose ionospheric divergence monitor tracks the
  code-carrier growth rate rather than the per-source delay magnitude
  computed here.' - the per-source delay claim is scoped to the
  ionospheric member only; no leaf computes or even names a tropospheric
  term." "(d) Published deterministic anchor (summary-only):
  Saastamoinen zenith delays - hydrostatic zenith delay approx.
  0.002277 * p / cos(z) with the gravity/height correction term, wet
  zenith delay from the water-vapour partial pressure e and temperature
  T (1255/T + 0.05 form), mapped to slant by the cosecant elevation
  mapping function with the Black/height-correction extension. Equation
  family: zenith met-model polynomials plus elevation mapping. Source:
  Saastamoinen, 'Contributions to the Theory of Atmospheric Refraction,'
  Bulletin Geodesique 107:13-34, 1973 (and his 1972 AGU monograph
  chapter); Hopfield 1969 as the standard alternative. Deterministic
  offline closed form given surface pressure, temperature, vapour
  pressure and elevation." Corpus tokens of the leaf (gate f, all
  hyphenated compounds): tropospheric-delay-correction, saastamoinen-
  model, zenith-hydrostatic-delay, zenith-wet-delay, slant-tropospheric-
  delay, elevation-mapping-function.
- Claim fences (quoted from the sibling SKILL.md files at prep; the
  receipt's gate (b) quotes, confirmed by fresh reads at wave-47 HEAD):
  - gnc-autonomy/navigation/ionospheric-delay-correction covers ONLY
    the ionospheric member of the per-source delay model. Its body
    reads "Use when a GNSS single-frequency navigation chain must
    correct an L1 pseudorange for the broadcast ionospheric delay
    before it is passed to a position fix. This leaf implements the
    Klobuchar broadcast ionospheric delay algorithm in pure Python,
    stdlib only: the earth-centred angle to the ionospheric pierce
    point, the subionospheric point and its geomagnetic latitude, the
    local time of day, the amplitude and period quartic polynomials in
    the broadcast alpha and beta coefficients, the day-curve shape
    about the 14:00 local-time peak, the vertical delay with its 5 ns
    night floor, and the elevation obliquity factor mapping the
    vertical delay to the slant delay. It pairs with gnc-autonomy/
    navigation/gnss-pseudorange-positioning, which consumes the
    corrected pseudorange in its iterated least squares fix, and
    gnc-autonomy/navigation/gnss-carrier-smoothing, whose ionospheric
    divergence monitor tracks the code-carrier growth rate rather than
    the per-source delay magnitude computed here." (SKILL.md lines
    23-37). The per-source delay claim is scoped to the ionospheric
    member: the sibling names no tropospheric term anywhere, and its
    Related leaves row for gnss-rtk-positioning says "the differential
    technique that cancels most of the ionospheric delay through
    double differences instead of modeling it per source" (lines
    168-170), never a tropospheric model. Ionospheric vocab owned by
    that sibling and forbidden here: klobuchar, pierce point, alpha
    and beta broadcast coefficients, ionospheric delay, ionosphere.
  - gnc-autonomy/navigation/gnss-pseudorange-positioning consumes
    pseudoranges as given. Its description reads "given satellite
    positions in ECEF and their pseudoranges (geometric range plus
    receiver clock bias), solve the four-unknown navigation equations
    for x, y, z and clock bias with an iterated least-squares
    adjustment", its body reads "Post-fit position error: pos_1sigma =
    uere_equiv * pdop with uere_equiv = residual RMS" (SKILL.md lines
    53-54) and "The leaf is a snapshot solution: no smoothing, no
    dynamics model" (lines 35-36): the fix leaf owns the iterated
    least-squares solution and the residual statistics and lumps all
    unmodeled error into a post-fit scalar, never a per-source delay
    model.
  - gnc-autonomy/navigation/gnss-rtk-positioning owns the differential
    technique. Its description reads "compute the position of a GNSS
    rover relative to a fixed base station from double-difference
    carrier-phase observables ... Resolve the integer ambiguities by
    rounding candidate sets around the float solution with a ratio
    test" and its body pairs it with gnss-pseudorange-positioning,
    gnss-carrier-smoothing and gnss-doppler-velocity-positioning as
    "the fences ... described under Related leaves".
  Whole-tree greps at prep (receipt gate (a), re-verified FRESH at HEAD
  a4ae6d1e then 8af8bce8): 'saastamoinen|hopfield|zenith-delay'
  returns ZERO hits across all SKILL.md files (exit 1), and no
  gnc-autonomy SKILL.md contains 'tropospher' at all; the only
  troposphere-word owners tree-wide are the cross-cutting atmosphere-
  STATE leaves (isa-atmosphere uses the word for the ISA temperature-
  lapse layer, tag troposphere, never a radio propagation delay). All
  six corpus tokens of this leaf appear in ZERO of the 1286
  eval/hit1-corpus.yaml tasks, and the receipt's theft audit reports 0
  of 1286 tasks rerouting to the candidate.
- Standards id: rtca-do-229 (reference-only, present in
  standards-map.yaml at line 303, the GNSS-navigation sibling
  convention, same reference-only use as the ionospheric leaf).
  Saastamoinen, "Contributions to the Theory of Atmospheric
  Refraction," Bulletin Geodesique 107:13-34, 1973 is cited by name
  only as the summary-form source of the relations; Hopfield 1969 is
  named as the standard alternative, not implemented. Both RTCA DO-229
  and the cited papers are referenced, never reproduced. Ledger
  Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Compute the tropospheric delay correction of a GNSS line of sight under
the Saastamoinen surface-met model (1973 summary form): given the
surface pressure P in hPa, the temperature T in K, the water-vapour
partial pressure e in hPa (or the relative humidity from which e is
derived through the pinned Magnus saturation form), the station geodetic
latitude phi in degrees and height H in km, and the satellite elevation
E in degrees, evaluate the gravity/height factor f = 1 -
0.00266*cos(2*phi) - 0.00028*H, the zenith hydrostatic delay ZHD =
0.002277*P/f, the zenith wet delay ZWD = 0.002277*(1255/T + 0.05)*e/f,
the zenith total delay ZTD = ZHD + ZWD, the cosecant elevation mapping
factor m = 1/sin(E), and the slant hydrostatic, wet and total
tropospheric delays in metres obtained by multiplying each zenith term
by m. Produces the gravity/height factor, the zenith hydrostatic delay,
the zenith wet delay, the zenith total delay, the elevation mapping
factor and the slant tropospheric delay in metres that a consuming
navigation chain subtracts from the GNSS range before positioning.
Does NOT do: the Klobuchar broadcast model, the pierce-point geometry,
the broadcast alpha and beta coefficient polynomials, the ionospheric
vertical or slant delay, the ionosphere or any ionospheric term of the
per-source delay seam (ionospheric-delay-correction owns the ionospheric
member); any position fix, iterated least squares, receiver clock bias,
residual, uere or snapshot navigation solution (gnss-pseudorange-
positioning owns the fix and consumes ranges as given); double
differences, integer ambiguity resolution, float or fixed baseline,
rover/base differential processing (gnss-rtk-positioning); the Hatch
recursion, carrier smoothing or the ionospheric divergence monitor of a
smoothed range (gnss-carrier-smoothing); RAIM/RTK fault detection,
protection levels, DOP values, doppler velocity, clock-drift estimation
or ephemeris propagation (gnss-raim-fde, dilution-of-precision,
gnss-doppler-velocity-positioning); the Hopfield 1969 alternative model
(named only); reproducing any RTCA DO-229 or Saastamoinen/Hopfield text
(all reference-only, paraphrased summary). Deterministic, offline,
stdlib math only: explicit scalar arithmetic, no numpy, no scipy, no
RNG, no external processes, no external solvers.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes. Deterministic: plain explicit scalar arithmetic in the pinned
order below. Module name tropospheric_delay_correction.

Unit conventions (pin exactly): surface pressure P in hPa (1 hPa = 1
mbar); temperature T in kelvin; water-vapour partial pressure e in hPa;
relative humidity RH in percent; station geodetic latitude phi in
degrees north in [-90, 90]; station height H above sea level in km;
satellite elevation E in degrees in (0, 90]; all delays in metres. The
surface-met window of the model (pin exactly): P in [300.0, 1100.0]
hPa, T in [200.0, 340.0] K, H in [-1.0, 10.0] km, RH in [0.0, 100.0]
percent, and e in [0.0, es(T)] hPa where es(T) is the saturation vapour
pressure at T (relative humidity cannot exceed 100 percent, so the
partial pressure cannot exceed saturation; this is a model validation,
not a clamp).

Module constants (pin exactly):
- K_TROP = 0.002277 (zenith delay coefficient, m per hPa).
- WET_T_NUM = 1255.0 and WET_T_C = 0.05 (Saastamoinen wet zenith term
  (1255/T + 0.05), T in kelvin).
- G_COS2 = 0.00266 (gravity/height factor cos(2*phi) coefficient,
  phi in radians in the cosine).
- G_H_KM = 0.00028 (gravity/height factor height coefficient, per km).
- ES_0 = 6.112 (Magnus saturation vapour pressure at 0 C, hPa),
  MAGNUS_A = 17.62, MAGNUS_B = 243.12 (Magnus exponent constants,
  MAGNUS_B in deg C), KELVIN_OFFSET = 273.15.
- P_MIN_HPA = 300.0, P_MAX_HPA = 1100.0, T_MIN_K = 200.0,
  T_MAX_K = 340.0, H_MIN_KM = -1.0, H_MAX_KM = 10.0.
- Worked-example scenario (pin exactly): P_EX = 1013.25 hPa,
  T_EX = 288.15 K (15 C), RH_EX = 50.0 percent, PHI_EX = 40.0 deg N,
  H_EX = 0.0 km, EL_EX = 30.0 deg. The scenario water-vapour partial
  pressure e_EX = water_vapor_pressure_hpa(T_EX, RH_EX) is a REAL
  anchor output, not an input constant (see Worked example).

Defining relations (pin exactly; every function derives from these):
- Saturation vapour pressure (standard meteorological Magnus form,
  pinned constants): with t_c = T - 273.15, es(T) = 6.112 *
  exp(17.62 * t_c / (243.12 + t_c)) hPa.
- Water-vapour partial pressure from humidity: e = es(T) * RH / 100.
- Gravity/height factor (Saastamoinen): f(phi, H) = 1 - 0.00266 *
  cos(2 * phi_rad) - 0.00028 * H, with phi_rad the geodetic latitude
  in radians. Over the valid window f lies in (0.99, 1.01) and is
  always positive (no division hazard).
- Zenith hydrostatic (dry) delay: ZHD = 0.002277 * P / f, metres.
- Zenith wet delay: ZWD = 0.002277 * (1255/T + 0.05) * e / f, metres.
- Zenith total delay: ZTD = ZHD + ZWD, metres.
- Elevation mapping factor (cosecant, plane-parallel): m(E) =
  1/sin(E) with E in degrees. m is strictly decreasing on (0, 90],
  m(90) = 1, and m grows without bound as E approaches 0 (a real
  satellite below 10 deg elevation is where the correction is largest;
  the worked sweep stays at or above 10 deg where the summary form is
  within its engineering accuracy).
- Slant delays: slant hydrostatic = ZHD * m(E), slant wet = ZWD *
  m(E), slant total = (ZHD + ZWD) * m(E), metres.

Functions (public API, 10):
- saturation_vapor_pressure_hpa(t_k) -> es in hPa by the Magnus form.
  ValueError if T is non-finite or outside [200.0, 340.0] K.
- water_vapor_pressure_hpa(t_k, rh_pct) -> e = es(T) * RH/100 in hPa.
  ValueError as for saturation_vapor_pressure_hpa plus RH non-finite or
  outside [0.0, 100.0].
- gravity_factor(phi_deg, h_km) -> f(phi, H) dimensionless. ValueError
  if phi non-finite or outside [-90.0, 90.0] deg, or H non-finite or
  outside [-1.0, 10.0] km.
- zenith_hydrostatic_delay_m(p_hpa, phi_deg, h_km) -> ZHD in metres.
  ValueError if P non-finite or outside [300.0, 1100.0] hPa, or as for
  gravity_factor.
- zenith_wet_delay_m(e_hpa, t_k, phi_deg, h_km) -> ZWD in metres.
  ValueError if e non-finite or outside [0.0, es(T)] hPa (es(T) from
  the Magnus form at T), or T non-finite or outside [200.0, 340.0] K
  (raised through the es(T) call), or as for gravity_factor.
- zenith_total_delay_m(p_hpa, e_hpa, t_k, phi_deg, h_km) -> ZTD =
  ZHD + ZWD in metres. Same ValueErrors as the two helpers it composes.
- slant_mapping_factor(el_deg) -> m(E) = 1/sin(E). ValueError if E
  non-finite or outside (0.0, 90.0] deg.
- slant_hydrostatic_delay_m(p_hpa, phi_deg, h_km, el_deg) -> ZHD * m(E)
  in metres. Elevation validated FIRST (ValueError as for
  slant_mapping_factor), then as for zenith_hydrostatic_delay_m.
- slant_wet_delay_m(e_hpa, t_k, phi_deg, h_km, el_deg) -> ZWD * m(E) in
  metres. Elevation validated FIRST, then as for zenith_wet_delay_m.
- slant_delay_m(p_hpa, e_hpa, t_k, phi_deg, h_km, el_deg) -> full
  pipeline slant tropospheric delay ZTD * m(E) in metres. Elevation
  validated FIRST, then every input through the helpers, so an invalid
  elevation raises ValueError and never a ZeroDivisionError.

Private helpers (module-internal): _check_finite, _check_t, _check_rh,
_check_lat, _check_h, _check_p, _check_e and _check_el shared by the
public functions. Every public function validates its own inputs and
raises ValueError before computing. Explicit scalar arithmetic
throughout; no matrix library. Determinism: no RNG anywhere,
bitwise-identical repeat calls.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- Mapping identities: m(90) * sin(90 deg) = 1 and m(E) * sin(E) = 1
  for every valid E (cosecant by definition); m is strictly decreasing
  on (0, 90] with m(90) = 1 exactly and m(E) > 1 for E < 90; at the
  zenith the slant total delay equals ZTD within 1e-12 (the mapping
  factor is the only slanting factor, and m(90) = 1).
- Gravity/height identities: f(45, 0) = 1 within 1e-12 (cos(90 deg) =
  0, so the latitude term vanishes exactly at 45 deg); f(0, 0) =
  1 - 0.00266 = 0.99734 and f(90, 0) = 1 + 0.00266 = 1.00266 within
  1e-15 relative (cos(0) = 1 and cos(180 deg) = -1); f is linear in
  height with slope -0.00028 per km, so f(45, 1) - f(45, 0) = -0.00028
  within 1e-12 relative and 1e-15 absolute; f stays positive over the
  whole valid window (closed-form minimum 0.99454 at phi = 0 deg, H =
  10 km and maximum 1.00294 at phi = 90 deg, H = -1 km, both inside
  (0.99, 1.01)).
- Zenith closed forms: at phi = 45 deg and H = 0 (f = 1) the zenith
  hydrostatic delay collapses to ZHD = 0.002277 * P exactly within
  1e-12 relative (real anchor: 2.277 m at P = 1000 hPa); ZHD scales
  linearly in P (ZHD(2P) = 2 * ZHD(P) within 1e-12); ZWD scales
  linearly in e (ZWD(e/2) = ZWD(e)/2 within 1e-12); ZWD(e = 0) = 0
  exactly (isclose with abs_tol 1e-15); ZTD = ZHD + ZWD within 1e-15
  relative.
- Wet term shape: the wet factor (1255/T + 0.05) is strictly
  decreasing in T over [200, 340] K (real anchor value 4.40537046677
  at T_EX = 288.15 K), and the wet term vanishes with e.
- Dry/wet share: at the worked scenario ZWD is roughly 3.7 percent of
  ZHD (0.085 m wet against 2.308 m dry), the classic hydrostatic
  dominance of the tropospheric delay.
- Physical sanity windows (worked scenario): ZHD in [2.0, 2.6] m, ZWD
  in [0.03, 0.20] m, ZTD in [2.2, 2.6] m, slant total at 30 deg in
  [4.0, 5.5] m, slant total at 10 deg in [8.0, 15.0] m, and the slant
  delay is monotone decreasing in elevation across the sweep.
- Determinism: two identical calls are bitwise identical in every
  return value.

## Worked example

Scenario: mid-latitude station at 40.0 deg N geodetic latitude and 0.0
km height above sea level with the standard sea-level pressure 1013.25
hPa, air temperature 288.15 K (15 C) and relative humidity 50.0
percent, observing a satellite at 30.0 deg elevation. The scenario
water-vapour partial pressure is derived from the humidity, not chosen:
e = water_vapor_pressure_hpa(288.15, 50.0). All values below are REAL
outputs of the prep anchor /tmp/w47spec/anchor_tropospheric_delay_
correction.py (stdlib math only, exit 0, output bitwise identical under
/usr/bin/python3 3.9.6, the pyenv 3.13.12 interpreter and the pyenv
3.12.9 interpreter); the contract test asserts these within 1e-6
relative.

- Saturation vapour pressure: saturation_vapor_pressure_hpa(288.15) =
  17.01672024059306 hPa.
- Water-vapour partial pressure: water_vapor_pressure_hpa(288.15,
  50.0) = 8.5083601202965298 hPa (half of es at 15 C).
- Gravity/height factor: gravity_factor(40.0, 0.0) =
  0.99953809584740594 (the cos(2*40 deg) = cos(80 deg) = 0.173648
  latitude term lowers f by 0.0004619 below 1).
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
total delay in metres and the mapping factor; the zenith delays stay
fixed because the met state does not move with elevation):

- E 10.0 deg: slant total 13.784328232455502 m (m 5.7587704831436337,
  the low-elevation regime where the correction is largest).
- E 15.0 deg: slant total 9.2482509429728381 m (m 3.8637033051562737).
- E 20.0 deg: slant total 6.9984868571016552 m (m 2.9238044001630876).
- E 30.0 deg: slant total 4.7872469558574346 m (m 2.0000000000000004).
- E 45.0 deg: slant total 3.3850947857014484 m (m 1.4142135623730951).
- E 60.0 deg: slant total 2.7639183186415059 m (m 1.1547005383792517).
- E 90.0 deg: slant total 2.3936234779287169 m (m 1.0, the zenith:
  the slant delay collapses exactly onto ZTD).

Latitude and height variation of the gravity factor and the zenith
hydrostatic delay at P = 1013.25 hPa (real anchor rows): phi 0.0 deg,
H 0.0 km gives f 0.997340000000 and ZHD 2.313323691018 m; phi 40.0 deg,
H 0.0 km gives f 0.999538095847 and ZHD 2.308236433994 m; phi 45.0 deg,
H 0.0 km gives f 1.000000000000 and ZHD 2.307170250000 m (the f = 1
collapse); phi 90.0 deg, H 0.0 km gives f 1.002660000000 and ZHD
2.301049458441 m; phi 45.0 deg, H 1.0 km gives f 0.999720000000 and ZHD
2.307816438603 m; phi 45.0 deg, H 5.0 km gives f 0.998600000000 and ZHD
2.310404816743 m. The gravity/height factor moves the dry zenith delay
by only about a centimeter across the whole latitude range and about a
millimeter per kilometer of height, which is why the f divisor matters
at the metre-level slant budget but never dominates it.

The sweep shows the physical signature of the model: the slant delay
grows steeply toward the horizon (13.784 m at 10 deg against 2.394 m at
zenith) through the cosecant mapping factor while the zenith delays stay
fixed, and the zenith slant delay equals the zenith total delay exactly
(m(90) = 1). The wet delay contributes 0.085 m of the 2.394 m zenith
total (about 3.6 percent) at this mild 15 C / 50 percent RH state and
scales linearly with the water-vapour partial pressure.

Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
/tmp/w47spec/anchor_tropospheric_delay_correction.py (stdlib math, exit
0, bitwise identical under /usr/bin/python3 3.9.6, pyenv 3.13.12 and
pyenv 3.12.9).

## Validation list (contract test must include)

1. Worked example anchors within 1e-6 relative:
   saturation_vapor_pressure_hpa(288.15) = 17.01672024059306;
   water_vapor_pressure_hpa(288.15, 50.0) = 8.5083601202965298;
   gravity_factor(40.0, 0.0) = 0.99953809584740594;
   zenith_hydrostatic_delay_m(1013.25, 40.0, 0.0) =
   2.3082364339940309; zenith_wet_delay_m(8.5083601202965298, 288.15,
   40.0, 0.0) = 0.085387043934685852;
   zenith_total_delay_m(1013.25, 8.5083601202965298, 288.15, 40.0,
   0.0) = 2.3936234779287169; slant_mapping_factor(30.0) =
   2.0000000000000004.
2. Slant contract anchors within 1e-6 relative:
   slant_hydrostatic_delay_m(1013.25, 40.0, 0.0, 30.0) =
   4.6164728679880627; slant_wet_delay_m(8.5083601202965298, 288.15,
   40.0, 0.0, 30.0) = 0.17077408786937173; slant_delay_m(1013.25,
   8.5083601202965298, 288.15, 40.0, 0.0, 30.0) = 4.7872469558574346;
   slant_delay_m(...) equals slant_mapping_factor(30.0) *
   zenith_total_delay_m(...) within 1e-12 relative (the mapping
   identity slant = m * ZTD).
3. Elevation sweep anchors within 1e-6 relative: the seven slant total
   values of the sweep (13.784328232455502, 9.2482509429728381,
   6.9984868571016552, 4.7872469558574346, 3.3850947857014484,
   2.7639183186415059, 2.3936234779287169 m) with the per-row mapping
   factors (5.7587704831436337, 3.8637033051562737, 2.9238044001630876,
   2.0000000000000004, 1.4142135623730951, 1.1547005383792517, 1.0),
   and slant delay monotone decreasing across the sweep rows; the
   90 deg row equals zenith_total_delay_m(...) within 1e-12 relative.
4. Mapping identities: slant_mapping_factor(90.0) = 1.0 within 1e-12;
   slant_mapping_factor(30.0) * math.sin(math.radians(30.0)) = 1.0
   within 1e-12 (cosecant identity); slant_mapping_factor(60.0) <
   slant_mapping_factor(30.0) < slant_mapping_factor(10.0) (strictly
   decreasing); slant_mapping_factor(90.0) is the minimum over (0, 90].
5. Gravity/height identities: gravity_factor(45.0, 0.0) = 1.0 within
   1e-12; gravity_factor(0.0, 0.0) = 0.99734 = 1 - 0.00266 within
   1e-15 relative; gravity_factor(90.0, 0.0) = 1.00266 = 1 + 0.00266
   within 1e-15 relative; gravity_factor(45.0, 1.0) -
   gravity_factor(45.0, 0.0) = -0.00028 within 1e-12 relative and
   1e-15 absolute; gravity_factor stays positive over the whole valid
   window.
6. Latitude/height variation anchors within 1e-6 relative: the six f
   and ZHD rows of the variation table (f 0.997340000000, 0.999538095847,
   1.000000000000, 1.002660000000, 0.999720000000, 0.998600000000; ZHD
   2.313323691018, 2.308236433994, 2.307170250000, 2.301049458441,
   2.307816438603, 2.310404816743 m at P = 1013.25 hPa).
7. Closed-form and scaling identities: zenith_hydrostatic_delay_m(
   1000.0, 45.0, 0.0) = 0.002277 * 1000.0 = 2.277 m within 1e-12
   relative (the f = 1 collapse); zenith_hydrostatic_delay_m(1000.0,
   40.0, 0.5) = 2 * zenith_hydrostatic_delay_m(500.0, 40.0, 0.5)
   within 1e-12 relative (linear in P); zenith_wet_delay_m(
   water_vapor_pressure_hpa(288.15, 25.0), 288.15, 40.0, 0.0) =
   0.5 * zenith_wet_delay_m(8.5083601202965298, 288.15, 40.0, 0.0)
   within 1e-12 relative (linear in e); zenith_wet_delay_m(0.0,
   288.15, 40.0, 0.0) = 0.0 (isclose with abs_tol 1e-15);
   zenith_total_delay_m equals the sum of its two zenith components
   within 1e-15 relative; the wet factor 1255/T + 0.05 at T = 288.15
   equals 4.4053704667707789 within 1e-12 relative and is strictly
   decreasing in T across [200, 340] K.
8. Physical sanity: at the worked scenario, ZHD in [2.0, 2.6] m, ZWD
   in [0.03, 0.20] m, ZTD in [2.2, 2.6] m, slant total at 30 deg in
   [4.0, 5.5] m and slant total at 10 deg in [8.0, 15.0] m; ZWD is
   between 2 and 6 percent of ZHD at the scenario (hydrostatic
   dominance); every slant delay at any valid input exceeds its zenith
   total.
9. Determinism: two identical calls to slant_delay_m and to
   zenith_total_delay_m are bitwise identical in every return value; no
   RNG anywhere; no imports beyond math.
10. ValueErrors (deterministic): elevation at 0.0, -5.0, 90.1 and nan
    on slant_mapping_factor and on each slant_* function (the elevation
    is validated first, so no ZeroDivisionError ever escapes); geodetic
    latitude at 90.5 and -91.0 and height at 10.5 and -1.5 on
    gravity_factor; pressure at 200.0 and 1200.0 on
    zenith_hydrostatic_delay_m; a negative water-vapour partial
    pressure, a partial pressure above es(T) (e.g. es(288.15) + 1.0)
    and temperatures at 180.0 and 350.0 on zenith_wet_delay_m; relative
    humidity at -1.0 and 101.0 on water_vapor_pressure_hpa; temperature
    at 150.0 on saturation_vapor_pressure_hpa. Every case raises
    ValueError.
11. Full-pipeline rejection: slant_delay_m with an elevation of 0 deg
    raises ValueError (never ZeroDivisionError), and each of a pressure
    of 200.0 hPa, a latitude of 90.5 deg, a height of 10.5 km, a
    negative partial pressure, a partial pressure above es(T), a
    temperature of 180.0 K propagates ValueError through the full
    slant_delay_m pipeline.
12. Physical-sanity bounds across the window: ZHD(P = 1100 hPa,
    phi = 90, H = 0) < 2.6 m and ZHD(P = 300 hPa, phi = 0, H = 10) >
    0.65 m; every zenith delay is positive at any valid input; the
    gravity factor never leaves (0.99, 1.01) over the valid window.
13. Run the contract test under BOTH interpreters, /usr/bin/python3
    3.9.6 and ~/.pyenv/versions/3.13.12/bin/python3 (the prep anchor
    exits 0 with bitwise-identical output on 3.9.6, 3.13.12 and
    3.12.9). All asserts are tolerance-based with assertAlmostEqual or
    math.isclose, NEVER exact float equality on computed sums.

## Corpus fragment (eval/hit1-wave47-tropospheric-delay-correction.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "compute the saastamoinen zenith hydrostatic delay and the zenith wet
  delay from the surface pressure, temperature and water-vapour partial
  pressure and map them to the slant tropospheric delay at the
  satellite elevation to correct the GNSS range"
  intent: "gnc-autonomy; compute the saastamoinen zenith hydrostatic
  delay and the zenith wet delay from the surface pressure, temperature
  and water-vapour partial pressure and map them to the slant
  tropospheric delay at the satellite elevation to correct the GNSS
  range"
  expected_skill: "gnc-autonomy/navigation/tropospheric-delay-correction"
Query 2 (copy verbatim from the receipt gate (e)):
  "apply the tropospheric-delay-correction to the pseudorange: evaluate
  the saastamoinen model zenith delay with the elevation mapping
  function and subtract the slant tropospheric delay in metres before
  the position fix"
  intent: "gnc-autonomy; apply the tropospheric-delay-correction to the
  pseudorange: evaluate the saastamoinen model zenith delay with the
  elevation mapping function and subtract the slant tropospheric delay
  in metres before the position fix"
  expected_skill: "gnc-autonomy/navigation/tropospheric-delay-correction"
Task ids: w47-tropospheric-delay-correction-1 and -2. Prep grep:
tropospheric-delay-correction, saastamoinen-model, zenith-hydrostatic-
delay, zenith-wet-delay, slant-tropospheric-delay and elevation-mapping-
function appear in NO existing eval/hit1-corpus.yaml task (whole-tree
grep count of saastamoinen and tropospheric 0 over all 1286 tasks,
receipt gate (a)) and in NO SKILL.md file (receipt gate (a): the only
troposphere-word owners are the cross-cutting atmosphere-STATE leaves
using the ISA temperature-lapse vocabulary, and the ionospheric sibling
tasks w46-ionospheric-delay-correction-1/-2 route on klobuchar-broadcast-
model, pierce-point and alpha/beta-coefficient wording; the gnss-
pseudorange-positioning tasks route on the iterated least squares fix
and receiver clock bias, the dilution-of-precision tasks on DOP values
and the elevation mask, the gnss-raim-fde tasks on chi-square fault
detection and protection levels and the gnss-rtk-positioning tasks on
double differences and integer ambiguities), so the queries above are
collision-free (receipt sim: Hit@1 at 19.0 vs 12.0 and 22.5 vs 16.0
against gnc-autonomy/navigation/ionospheric-delay-correction, theft
audit 0 of 1286 tasks reroute).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must correct the GNSS range for the
tropospheric delay:" and include the outputs in the Claim (gravity and
height factor, zenith hydrostatic delay, zenith wet delay, zenith total
delay, elevation mapping factor, slant tropospheric delay in metres).
First tag: tropospheric-delay-correction (the leaf name). Additional
tags ONLY, the exact gate (f) set, all hyphenated compounds:
saastamoinen-model, zenith-hydrostatic-delay, zenith-wet-delay,
slant-tropospheric-delay, elevation-mapping-function (frontmatter
metadata.tags order: tropospheric-delay-correction, saastamoinen-model,
zenith-hydrostatic-delay, zenith-wet-delay, slant-tropospheric-delay,
elevation-mapping-function). NEVER single generic words (troposphere,
delay, correction, model, mapping, elevation, zenith, slant, pressure,
temperature, humidity, satellite, range, metre alone) and NEVER the
sibling-owned compounds: ionospheric-delay-correction, klobuchar-
broadcast-model, slant-delay-correction, pierce-point-geometry,
broadcast-alpha-beta-coefficients, ionosphere, klobuchar, ionospheric
delay, pierce point (ionospheric-delay-correction, which owns the
ionospheric member of the per-source delay seam); gnss-pseudorange-
positioning, pseudorange-positioning, gnss-position-fix, receiver-clock-
bias, iterated-least-squares-fix, ecef-position-solution, satellite-
pseudorange-residual, snapshot-navigation-solution, position fix,
iterated least squares, post-fit residual (gnss-pseudorange-positioning,
which owns the fix); gnss-rtk-positioning, double difference, integer
ambiguity, float baseline, fixed baseline, rover, base station (gnss-
rtk-positioning); gnss-carrier-smoothing, hatch-filter-recursion,
carrier-phase-smoothing, code-carrier-divergence-monitor, smoothed
range, divergence monitor (gnss-carrier-smoothing); gnss-raim-fde,
protection level, fault detection (gnss-raim-fde); gnss-doppler-
velocity-positioning, delta range rate, clock drift, broadcast
ephemeris propagation (gnss-doppler-velocity-positioning);
dilution-of-precision, gdop, pdop, elevation mask (dilution-of-
precision). 50-150 words, <=1000 chars, no em dash, no content-policy
sweep term, action verb present. Recommended wording (outputs in Claim
order, measured 132 words and 961 chars, no em dash):
"Use when you must correct the GNSS range for the tropospheric delay:
evaluate the saastamoinen-model delay from the surface pressure,
temperature and water-vapour partial pressure, form the gravity and
height factor from latitude and station height, form the zenith-
hydrostatic-delay by dividing the pressure by that factor, form the
zenith-wet-delay from the water-vapour partial pressure and the
temperature term, sum both into the zenith total delay and map it to
the slant-tropospheric-delay with cosecant elevation-mapping-function
at the satellite elevation. Produces the gravity and height factor, the
zenith hydrostatic delay, the zenith wet delay, the zenith total delay,
the elevation mapping factor and the slant tropospheric delay in metres
that gate the range correction before positioning. Trigger:
saastamoinen model, tropospheric delay correction, zenith hydrostatic
delay, zenith wet delay, slant tropospheric delay, elevation mapping
function."
The sibling phrase triggers "Klobuchar", "ionospheric delay", "pierce
point", "broadcast coefficients", "Hatch recursion", "carrier phase
smoothing", "divergence monitor", "smoothed range", "position fix",
"iterated least squares", "receiver clock bias", "snapshot solution",
"RAIM", "RTK", "double difference", "integer ambiguity", "delta range
rate", "clock drift", "elevation mask", "DOP", "protection level" and
"ephemeris propagation" must not appear as routing keywords;
"Saastamoinen", "tropospheric delay", "zenith hydrostatic delay",
"zenith wet delay", "slant tropospheric delay" and "elevation mapping
function" are the leaf's own identity and must stay, referring only to
the per-source tropospheric delay model of a single line of sight,
never to the ionosphere, the Klobuchar model, a position fix, a
differential or integrity technique, or a dual-frequency observable.
