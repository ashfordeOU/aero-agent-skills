# Wave-46 leaf spec: ionospheric-delay-correction (gnc-autonomy, navigation pack)

- Path: skills/gnc-autonomy/navigation/ionospheric-delay-correction/
- Pack: navigation (present siblings bearing-only-localization,
  dilution-of-precision, gnss-carrier-smoothing, gnss-doppler-velocity-
  positioning, gnss-pseudorange-positioning, gnss-raim-fde,
  gnss-rtk-positioning, inertial-navigation, ins-gnss-integrated-filter,
  kalman-filter-design, navigation-frames, terrain-referenced-navigation,
  tightly-coupled-ins-gnss; the two quoted fences below are the nearest
  owners this leaf must not duplicate).
- Provenance: wave-46 probe receipt task-7 GO rank 1 (the wave-45 GO4
  that cleared every gate a-f and was dropped only on pool size, re-
  issued at wave-46 HEAD with gates re-verified FRESH), gates (a)-(f)
  verbatim anchor: "(d) Published deterministic anchor (summary-only):
  Klobuchar broadcast ionospheric delay algorithm, pierce-point
  geomagnetic latitude from user and satellite geometry, amplitude and
  period as quartic polynomials in the broadcast alpha and beta
  coefficients, vertical delay 5e-9 + sum A_n phi_m^n seconds, elevation
  obliquity factor applied for the slant correction. Equation family:
  spherical pierce-point geometry plus quartic-in-latitude polynomials
  plus obliquity. Source: Klobuchar, 'Ionospheric Time-Delay Algorithm
  for Single-Frequency GPS Users,' IEEE TAES AES-23(3):325-331, 1987;
  IS-GPS-200. Deterministic offline closed form given the broadcast
  coefficients." Corpus tokens of the leaf (gate f, all hyphenated
  compounds): klobuchar-broadcast-model, ionospheric-delay-correction,
  slant-delay-correction, pierce-point-geometry,
  broadcast-alpha-beta-coefficients.
- Claim fences (quoted from the sibling SKILL.md files at prep; the
  receipt's gate (b) quotes, confirmed by fresh reads):
  - gnc-autonomy/navigation/gnss-carrier-smoothing owns the
    carrier-smoothing recursion and the ionospheric divergence MONITOR
    only. Its body reads "Ionospheric divergence: the code is delayed
    by +I while the carrier is advanced by -I, so the smoothed range
    carries a growing code-minus-carrier divergence error whose tau >>
    T form is -2*(dI/dt)*tau" (SKILL.md lines 68-73), and its scope
    line reads "Continuous carrier phase between epochs is assumed;
    cycle-slip repair and integer ambiguity resolution are out of
    scope" (line 39). No per-source delay model: the sibling evaluates
    the code-carrier difference and its growth rate, never the
    ionospheric delay magnitude itself.
  - gnc-autonomy/navigation/gnss-pseudorange-positioning consumes
    pseudoranges as given. Its body reads "Post-fit position error:
    pos_1sigma = uere_equiv * pdop with uere_equiv = residual RMS"
    (SKILL.md lines 53-54): the fix leaf owns the iterated-least-
    squares solution and the residual statistics, and no leaf computes
    a per-source ionospheric delay correction. The family router rows
    for both siblings carry the same claims.
  Whole-tree greps at prep: 'klobuchar' returns ZERO hits across all
  SKILL.md files (receipt gate (a), exit 1); the only 'ionospheric'
  owners are gnss-carrier-smoothing (divergence-monitor context) and
  the family router row for it; all five corpus tokens of this leaf
  appear in ZERO of the 1266 eval/hit1-corpus.yaml tasks, and the
  receipt's theft audit reports 0 of 1266 tasks rerouting to the
  candidate.
- Standards id: rtca-do-229 (reference-only, present in standards-map.yaml
  at line 303; the broadcast algorithm text sits in IS-GPS-200 section
  20.3.3.5.1, cited by name only; both RTCA DO-229 and IS-GPS-200 are
  referenced, never reproduced, per the GNSS sibling convention).
  Ledger Standard: rtca-do-229.
- Family: gnc-autonomy

## Claim

Compute the broadcast ionospheric delay correction of a GPS L1 line of
sight under the Klobuchar broadcast model: given the user geodetic
latitude and longitude, the satellite elevation and azimuth, the GPS
time of week and the eight broadcast coefficients (alpha_0..alpha_3 for
the amplitude polynomial, beta_0..beta_3 for the period polynomial),
evaluate the earth-centred angle to the ionospheric pierce point, the
subionospheric latitude and longitude, the pierce-point geomagnetic
latitude phi_m, the local time of day at the pierce point, the clamped
amplitude A = sum alpha_n phi_m^n and period P = sum beta_n phi_m^n
(phi_m in semicircles), the day-curve shape about the 14:00 local-time
peak, the vertical delay T_vert = 5e-9 + A*c seconds with the 5e-9 s
night floor, the elevation obliquity factor F = 1 + 2*((96 - el)/90)^3,
and the slant delay T_slant = F * T_vert. Produces the pierce-point
geomagnetic latitude, the amplitude and period coefficients, the
vertical delay in seconds and the slant ionospheric delay in seconds and
metres (delay in seconds times the vacuum speed of light c =
299792458.0 m/s) that a consuming navigation chain subtracts from the L1
pseudorange before positioning. Does NOT do: the Hatch recursion,
carrier-phase smoothing, the code-carrier difference, the divergence
rate or the divergence alarm of a smoothed range
(gnss-carrier-smoothing owns that monitor and quotes "cycle-slip repair
and integer ambiguity resolution are out of scope" for itself); any
position fix, iterated least squares, receiver clock bias, residual or
snapshot navigation solution (gnss-pseudorange-positioning owns the
fix and consumes pseudoranges as given); RAIM/RTK fault detection,
protection levels, double differences, integer ambiguity resolution,
doppler velocity or clock-drift estimation, DOP values, elevation-mask
selection or ephemeris propagation (gnss-raim-fde, gnss-rtk-positioning,
gnss-doppler-velocity-positioning, dilution-of-precision); reproducing
any RTCA DO-229 or IS-GPS-200 text (both are reference-only, paraphrased
summary). Deterministic, offline, stdlib math only: explicit scalar
arithmetic, no numpy, no scipy, no RNG, no external processes, no
external solvers.

## Model (implement exactly)

Pure stdlib, math only. No numpy, no scipy, no RNG, no external
processes. Deterministic: plain explicit scalar arithmetic in the pinned
order below. Module name ionospheric_delay_correction.

Unit conventions (pin exactly): user latitude, subionospheric latitude
and pierce-point geomagnetic latitude in degrees north; user longitude
and subionospheric longitude in degrees east, negative west, both in
[-180, 180]; elevation and azimuth in degrees (azimuth from north,
clockwise, in [0, 360)); GPS time of week and local times in seconds;
delays in seconds; metres are seconds times c. One semicircle (SC) =
180 degrees. The amplitude and period polynomials are evaluated at the
geomagnetic latitude expressed in semicircles (phi_m_SC = phi_m_deg/180).

Module constants (pin exactly):
- C_LIGHT = 299792458.0 (vacuum speed of light, m/s).
- T_BASE = 5.0e-9 (night floor and day minimum vertical delay, s).
- P_MIN = 72000.0 (minimum broadcast period clamp, s).
- T_PEAK = 50400.0 (14:00 local time day-curve peak, s).
- DAY_SECONDS = 86400.0, WEEK_SECONDS = 604800.0.
- SEC_PER_SC = 43200.0 (seconds per semicircle of longitude),
  DEG_PER_SC = 180.0.
- PHI_CLAMP_SC = 0.416 (subionospheric latitude clamp, semicircles).
- POLE_LAT_SC = 0.064 (geomagnetic pole colatitude offset,
  semicircles).
- POLE_LON_SC = 1.617 (geomagnetic pole longitude, semicircles).
- Worked-example scenario (pin exactly):
  ALPHA_EX = [0.8382e-08, -0.7451e-08, -0.5960e-07, 0.1192e-06],
  BETA_EX = [0.1306e+06, -0.3277e+05, -0.6554e+05, 0.1311e+06] (the
  documented example broadcast set of the Klobuchar literature),
  LAT_EX = 40.0, LON_EX = -105.0, EL_EX = 40.0, AZ_EX = 160.0,
  TOW_EX = 0.0.

Defining relations (pin exactly; every function derives from these):
- Earth-centred angle (standard empirical broadcast form): with
  E_SC = el/180, psi_SC = 0.0137/(E_SC + 0.11) - 0.022 (semicircles);
  the leaf works in degrees, psi_deg = 180 * psi_SC.
- Subionospheric point: lat_i_SC = clamp(lat_SC + psi_SC*cos(A_rad),
  -0.416, 0.416) and lon_i_SC = lon_SC + psi_SC*sin(A_rad)/
  cos(pi*lat_i_SC), with A_rad the azimuth in radians; the returned
  subionospheric longitude is normalized into [-180, 180) degrees
  ((lon + 180) mod 360 - 180), because a low-elevation pierce point
  near the antimeridian may wrap past it and the pole-offset and local
  time relations are periodic.
- Pierce-point geomagnetic latitude: phi_m_SC = lat_i_SC + 0.064 *
  cos(pi*(lon_i_SC - 1.617)).
- Local time of day at the pierce point: t_local = (43200 * lon_i_SC +
  tow) mod 86400, in [0, 86400).
- Amplitude polynomial: A = sum_{n=0..3} alpha_n * phi_m_SC^n; a
  negative A is clamped to 0.0 (model behavior, not an error).
- Period polynomial: P = sum_{n=0..3} beta_n * phi_m_SC^n; a P below
  72000 s is clamped to 72000.0 (model behavior, not an error).
- Day-curve shape: x = 2*pi*(t_local - 50400)/P. For |x| < pi/2 the
  day branch holds and c = 1 - x^2/2 + x^4/24; otherwise the night
  branch holds and c = 0.0.
- Vertical delay: T_vert = 5e-9 + A*c seconds (the delay is never
  below the 5e-9 s base).
- Obliquity factor: F = 1 + 2*((96 - el)/90)^3 with el in degrees
  (Klobuchar 1987 practical form).
- Slant delay: T_slant = F * T_vert.
- Metre conversion: delay_m = delay_s * 299792458.0.

Functions (public API, 12):
- earth_center_angle_deg(el_deg) -> earth-centred angle in degrees.
  ValueError if el non-finite or outside (0, 90].
- subionospheric_point_deg(lat_deg, lon_deg, el_deg, az_deg) ->
  (lat_i_deg, lon_i_deg) with lon normalized into [-180, 180).
  ValueErrors as for earth_center_angle_deg plus user latitude outside
  [-90, 90], user longitude outside [-180, 180], azimuth outside
  [0, 360), any non-finite.
- geomagnetic_latitude_deg(lat_i_deg, lon_i_deg) -> phi_m in degrees.
  ValueError if the subionospheric latitude is outside [-90, 90] or the
  subionospheric longitude outside [-180, 180], or non-finite.
- local_time_seconds(lon_i_deg, tow_sec) -> t_local in [0, 86400).
  ValueError if the subionospheric longitude is outside [-180, 180] or
  tow outside [0, 604800), or non-finite.
- amplitude_seconds(alpha, phi_m_deg) -> A >= 0.0 (clamped). ValueError
  if alpha is not a sequence of exactly 4 finite numbers, if alpha[0] <
  0 (a negative constant coefficient is non-physical: the polynomial
  collapses to alpha0 at the geomagnetic equator; higher-order signed
  coefficients are legitimate fit terms and may be negative), or if
  phi_m_deg is outside [-90, 90] or non-finite.
- period_seconds(beta, phi_m_deg) -> P >= 72000.0 (clamped). ValueError
  if beta is not a sequence of exactly 4 finite numbers, if beta[0] < 0
  (non-physical constant period coefficient), or phi_m_deg outside
  [-90, 90] or non-finite.
- day_shape_factor(t_local_sec, period_sec) -> c in [0, 1]. ValueError
  if t_local outside [0, 86400), period non-finite or not positive.
- vertical_delay_seconds(alpha, beta, phi_m_deg, t_local_sec) ->
  T_vert >= 5e-9. Same ValueErrors as the three helpers it composes.
- slant_factor(el_deg) -> F. ValueError if el non-finite or outside
  (0, 90].
- slant_delay_seconds(alpha, beta, lat_deg, lon_deg, el_deg, az_deg,
  tow_sec) -> T_slant = F * T_vert through the full geometry pipeline.
  Validates every input through the helpers.
- delay_meters(delay_seconds) -> delay * 299792458.0. ValueError if the
  delay is non-finite or negative.
- slant_delay_meters(alpha, beta, lat_deg, lon_deg, el_deg, az_deg,
  tow_sec) -> slant delay in metres (convenience wrapper).

Private helpers (module-internal): _check_el, _check_coords, _check_tow,
_check_coeff, _check_phi_m and _check_t_local shared by the public
functions. Every public function validates its own inputs and raises
ValueError before computing. Explicit scalar arithmetic throughout; no
matrix library. Determinism: no RNG anywhere, bitwise-identical repeat
calls.

Identities to test (tolerance-based asserts only, no exact float
equality on computed sums):
- Obliquity bounds: F(90) = 1.00059259259259 exactly (closed form
 1 + 2*(6/90)^3); F is strictly decreasing in el on (0, 90] with
 supremum 3.4272592592592593 (= 1 + 2*(96/90)^3) approached as el -> 0+;
 F is in (1.00059259259259, 3.4272592592592593] for el in (0, 90].
- Zenith limit: at el = 90 the slant-to-vertical ratio equals F(90) to
  1e-12 (the obliquity is the only factor left, and a high-elevation
  slant delay approaches the vertical delay).
- Peak identity: at t_local = 50400 the day shape is exactly 1.0, so
  T_vert = 5e-9 + A to 1e-12 relative (real anchor: the primary-scenario
  amplitude 4.55630181644608e-09 s plus the 5e-9 s base).
- Night floor: at t_local = 3600 the shape is 0.0 and T_vert equals
  exactly 5e-9 s (real anchor; night branch returns the base alone).
- Geomagnetic equator: A(phi_m = 0) = alpha0 and P(phi_m = 0) = beta0
  exactly, to 1e-15 relative (the polynomials collapse to their constant
  coefficients).
- Model clamps: a negative raw amplitude clamps to 0.0
  (amplitude_seconds([1.0e-9, -1.0e-8, 0.0, 0.0], 60.0) = 0.0) and a
  raw period below 72000 s clamps to 72000.0
  (period_seconds([70000.0, 0.0, 0.0, 0.0], 10.0) = 72000.0).
- Shape bounds: day_shape_factor(50400, P) = 1.0 exactly and c is in
  [0, 1] over the whole local-time range.
- Longitude normalization: subionospheric_point_deg(0.0, 179.0, 5.0,
  90.0) returns a longitude inside [-180, 180) (real anchor -167.0616
  deg) equal to the unwrapped value minus 360 to 1e-12, and never
  raises.
- Determinism: two identical calls are bitwise identical in every return
  value.
- Physical sanity windows: vertical delay in [5, 20] ns and slant delay
  in [10, 40] ns and [2, 8] m at the primary worked scenario.

## Worked example

Scenario: mid-latitude user at 40.0 deg N, -105.0 deg (105 deg W), GPS
time of week 0.0 s, satellite at 40.0 deg elevation and 160.0 deg
azimuth, with the documented example broadcast set
alpha = [0.8382e-08, -0.7451e-08, -0.5960e-07, 0.1192e-06] s per
semicircle power and
beta = [0.1306e+06, -0.3277e+05, -0.6554e+05, 0.1311e+06] s per
semicircle power. All values below are REAL outputs of the prep anchor
anchor_klobuchar_delay.py (stdlib math only, exit 0, output identical
under /usr/bin/python3 3.9.6 and the pyenv 3.13.12 interpreter); the
contract test asserts these within 1e-6 relative.

- Earth-centred angle: earth_center_angle_deg(40.0) = 3.46274247491639
  deg.
- Subionospheric point: subionospheric_point_deg(40.0, -105.0, 40.0,
  160.0) = (36.7460864486391 deg N, -103.521982351049 deg), no latitude
  clamp engaged (36.75 deg inside the 0.416 SC band).
- Pierce-point geomagnetic latitude: geomagnetic_latitude_deg(36.74608,
  -103.52198) = 46.2306740519375 deg (phi_m = 0.256837078066319 SC).
- Local time of day at the pierce point: local_time_seconds(-103.52198,
  0.0) = 61554.7242357482 s (17:06 local, afternoon).
- Amplitude: amplitude_seconds(ALPHA_EX, 46.2306740519375) =
  4.55630181644608e-09 s (4.556302 ns).
- Period: period_seconds(BETA_EX, 46.2306740519375) =
  120081.223784471 s (33.355895 h), above the 72000 s clamp.
- Day curve: x = 2*pi*(61554.7242357482 - 50400)/120081.223784471 =
  0.583664932908164 rad, inside the day branch |x| < pi/2, so
  day_shape_factor(61554.7242357482, 120081.223784471) =
  0.834503142819751.
- Vertical delay: vertical_delay_seconds(ALPHA_EX, BETA_EX,
  46.2306740519375, 61554.7242357482) = 8.80224818545959e-09 s
  (= 8.802248 ns = 2.638848 m): the 5e-9 s base plus
  4.556302 ns * 0.834503.
- Obliquity factor: slant_factor(40.0) = 1.48179972565158
  (= 1 + 2*((96 - 40)/90)^3).
- Slant delay: slant_delay_seconds(ALPHA_EX, BETA_EX, 40.0, -105.0,
  40.0, 160.0, 0.0) = 1.30431689463311e-08 s (= 13.043169 ns), and
  slant_delay_meters gives 3.910244 m. The metre value equals the
  second value times c within 1e-12 relative.

Elevation sweep at the same user, azimuth 160.0 deg and tow 0.0 s
(each slant line reports T_slant in s, ns and m with its own vertical
delay and obliquity, because the pierce-point geometry and local time
shift with elevation):

- el 10.0 deg: T_slant = 2.52683707319819e-08 s = 25.268371 ns =
  7.575267 m (T_vert 9.205203 ns, F 2.745010).
- el 30.0 deg: T_slant = 1.58796414198594e-08 s = 15.879641 ns =
  4.760597 m (T_vert 8.877553 ns, F 1.788741).
- el 40.0 deg: T_slant = 1.30431689463311e-08 s = 13.043169 ns =
  3.910244 m (T_vert 8.802248 ns, F 1.481800).
- el 60.0 deg: T_slant = 9.82787591714463e-09 s = 9.827876 ns =
  2.946323 m (T_vert 8.712656 ns, F 1.128000).
- el 90.0 deg: T_slant = 8.64857899766712e-09 s = 8.648579 ns =
  2.592779 m (T_vert 8.643457 ns, F 1.000593).

The sweep shows the physical signature of the model: the slant delay
grows steeply toward the horizon (7.6 m at 10 deg against 2.6 m at
zenith) through the obliquity factor while the vertical delay stays
nearly flat (8.6 to 9.2 ns) across the same span, and the zenith slant
delay approaches the vertical delay of its own pierce point within the
F(90) ratio 1.00059259259259.

Run your module and take the real outputs as assert targets
(tolerance-based); the anchors above are real prep outputs of
anchor_klobuchar_delay.py (stdlib math, exit 0, identical under both
interpreters).

## Validation list (contract test must include)

1. Worked example anchors within 1e-6 relative: earth_center_angle_deg
   (40.0) = 3.46274247491639; subionospheric_point_deg(40.0, -105.0,
   40.0, 160.0) = (36.7460864486391, -103.521982351049);
   geomagnetic_latitude_deg(36.7460864486391, -103.521982351049) =
   46.2306740519375; local_time_seconds(-103.521982351049, 0.0) =
   61554.7242357482; amplitude_seconds(ALPHA_EX, 46.2306740519375) =
   4.55630181644608e-09; period_seconds(BETA_EX, 46.2306740519375) =
   120081.223784471; day_shape_factor(61554.7242357482,
   120081.223784471) = 0.834503142819751.
2. Vertical and slant contract anchors within 1e-6 relative:
   vertical_delay_seconds(ALPHA_EX, BETA_EX, 46.2306740519375,
   61554.7242357482) = 8.80224818545959e-09 s;
   slant_delay_seconds(ALPHA_EX, BETA_EX, 40.0, -105.0, 40.0, 160.0,
   0.0) = 1.30431689463311e-08 s; slant_factor(40.0) =
   1.48179972565158; slant_delay_meters(...) = 3.910244 m and equals
   C_LIGHT * slant_delay_seconds(...) within 1e-12 relative
   (delay_meters identity: metres = seconds * c).
3. Elevation sweep anchors within 1e-6 relative: the five T_slant
   values of the sweep (2.52683707319819e-08, 1.58796414198594e-08,
   1.30431689463311e-08, 9.82787591714463e-09, 8.64857899766712e-09 s)
   with the per-row F factors 2.745010, 1.788741, 1.481800, 1.128000,
   1.000593, and monotone decreasing slant metres 7.575267, 4.760597,
   3.910244, 2.946323, 2.592779.
4. Obliquity identities: slant_factor(90.0) = 1.00059259259259 = 1 +
   2*(6/90)^3 within 1e-12; slant_factor(10.0) > slant_factor(90.0);
 slant_factor approaches 3.4272592592592593 as el -> 0+ (assert
 slant_factor(0.0001) within 1e-4 of 1 + 2*(96/90)^3); the el = 90
   slant-to-vertical ratio of the worked geometry equals F(90) within
   1e-12.
5. Peak identity: vertical_delay_seconds(ALPHA_EX, BETA_EX,
   46.2306740519375, 50400.0) = 5e-9 + amplitude_seconds(ALPHA_EX,
   46.2306740519375) within 1e-12 relative; day_shape_factor(50400.0,
   120081.223784471) = 1.0.
6. Night floor: vertical_delay_seconds(ALPHA_EX, BETA_EX,
   46.2306740519375, 3600.0) = 5e-9 exactly (night branch returns the
   base alone; isclose with rel_tol 0 and abs_tol 1e-20).
7. Polynomial collapse and clamps: amplitude_seconds(ALPHA_EX, 0.0) =
   alpha0 = 8.382e-09 and period_seconds(BETA_EX, 0.0) = beta0 =
   130600.0 within 1e-15 relative; amplitude_seconds([1.0e-9, -1.0e-8,
   0.0, 0.0], 60.0) = 0.0 (raw -2.333e-09 clamps to zero);
   period_seconds([70000.0, 0.0, 0.0, 0.0], 10.0) = 72000.0.
8. Longitude normalization: subionospheric_point_deg(0.0, 179.0, 5.0,
   90.0) returns (-0.0-ish latitude inside the clamp, -167.061612903226
   deg) with the longitude inside [-180, 180) and equal to the unwrapped
   value minus 360 within 1e-12; local_time_seconds accepts the wrapped
   longitude without raising.
9. Determinism: two identical calls to slant_delay_seconds and to
   vertical_delay_seconds are bitwise identical in every return value;
   no RNG anywhere; no imports beyond math.
10. ValueErrors (deterministic): elevation at 0.0, -5.0, 90.1 and nan on
    earth_center_angle_deg and slant_factor; user latitude at 90.5 and
    -91.0, longitude at 181.0, azimuth at 360.0 and -1.0 on
    subionospheric_point_deg; tow at 604800.0 and -1.0 on
    local_time_seconds; subionospheric latitude at 95.0 and longitude at
    181.0 on geomagnetic_latitude_deg; alpha of length 3, alpha with a
    nan entry, alpha0 at -0.5e-08 on amplitude_seconds; beta0 at
    -1000.0 on period_seconds; phi_m at 91.0 and -91.0 on both
    polynomial functions; t_local at 86400.0 and -1.0 and period at 0.0
    on day_shape_factor; a -1.0 s delay on delay_meters. Every case
    raises ValueError.
11. Full-pipeline rejection: slant_delay_seconds with an elevation of 0
    deg, a latitude of 90.5 deg, an azimuth of 360.0 deg, a tow of
    604800.0 s, a negative alpha0 or a 3-entry beta raises ValueError
    (every invalid input propagates through the pipeline).
12. Physical sanity: at the primary scenario, 5e-9 <= T_vert <= 2e-8 s,
    1e-8 <= T_slant <= 4e-8 s and 2.0 <= T_slant_m <= 8.0 m; every
    vertical delay at any valid input is >= 5e-9 s.
13. Run the contract test under BOTH interpreters, /usr/bin/python3 3.9.6
    and ~/.pyenv/versions/3.13.12/bin/python3 (the prep anchor exits 0
    with identical output on both). All asserts are tolerance-based with
    assertAlmostEqual or math.isclose, NEVER exact float equality on
    computed sums.

## Corpus fragment (eval/hit1-wave46-ionospheric-delay-correction.yaml)

Query 1 (copy verbatim from the receipt gate (e)):
  "apply the klobuchar-broadcast-model to the L1 pseudorange with the
  alpha and beta coefficients: compute the pierce-point geometry and
  the slant ionospheric delay correction"
  intent: "gnc-autonomy; klobuchar-broadcast-model on the L1
  pseudorange with the alpha and beta coefficients: compute the
  pierce-point geometry and the slant ionospheric delay correction"
  expected_skill: "gnc-autonomy/navigation/ionospheric-delay-correction"
Query 2 (copy verbatim from the receipt gate (e)):
  "compute the klobuchar broadcast model slant delay: evaluate the
  broadcast alpha and beta coefficient polynomials at the pierce point
  elevation and subtract the ionospheric delay correction from the L1
  pseudorange"
  intent: "gnc-autonomy; klobuchar-broadcast-model slant delay:
  evaluate the broadcast alpha and beta coefficient polynomials at the
  pierce point and subtract the ionospheric delay correction from the
  L1 pseudorange"
  expected_skill: "gnc-autonomy/navigation/ionospheric-delay-correction"
Task ids: w46-ionospheric-delay-correction-1 and -2. Prep grep:
klobuchar-broadcast-model, ionospheric-delay-correction,
slant-delay-correction, pierce-point-geometry and
broadcast-alpha-beta-coefficients appear in NO existing
eval/hit1-corpus.yaml task (whole-tree grep count of klobuchar 0 over
all 1266 tasks) and in NO SKILL.md file (receipt gate (a): the only
'ionospheric' frontmatter owners are gnss-carrier-smoothing, whose
tasks route on the Hatch recursion, carrier-phase delta ranges and the
code-carrier divergence alarm, and the family router row for it; the
gnss-pseudorange-positioning tasks route on the iterated least squares
fix and receiver clock bias, the dilution-of-precision tasks on DOP
values and the elevation mask, the gnss-raim-fde tasks on chi-square
fault detection and protection levels and the gnss-rtk-positioning
tasks on double differences and integer ambiguities), so the queries
above are collision-free (receipt sim: Hit@1 at 19.5 vs 7.0 and 24.0
vs 7.5, theft audit 0 of 1266 tasks reroute).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must correct the L1 pseudorange for
the broadcast ionospheric delay:" and include the outputs in the Claim
(pierce-point geomagnetic latitude, amplitude and period coefficients,
vertical delay, slant delay in seconds and metres). First tag:
ionospheric-delay-correction (the leaf name). Additional tags ONLY, the
exact gate (f) set, all hyphenated compounds:
klobuchar-broadcast-model, slant-delay-correction, pierce-point-
geometry, broadcast-alpha-beta-coefficients (frontmatter metadata.tags
order: ionospheric-delay-correction, klobuchar-broadcast-model,
slant-delay-correction, pierce-point-geometry,
broadcast-alpha-beta-coefficients). NEVER single generic words
(delay, ionosphere, ionospheric, correction, model, broadcast,
elevation, azimuth, latitude, longitude, satellite, coefficient,
polynomial, amplitude, period alone) and NEVER the sibling-owned
compounds: gnss-carrier-smoothing, carrier-phase-smoothing,
hatch-filter-recursion, code-carrier-divergence-monitor,
ionospheric-divergence-check, smoothed-range-noise-reduction,
hatch recursion, carrier phase smoothing, smoothed range, code-carrier
difference, divergence monitor, divergence alarm, cycle-slip repair,
integer ambiguity resolution (gnss-carrier-smoothing, which owns the
plain ionospheric-divergence-check tag and the divergence MONITOR
claim); gnss-pseudorange-positioning, pseudorange-positioning,
gnss-position-fix, receiver-clock-bias, iterated-least-squares-fix,
ecef-position-solution, satellite-pseudorange-residual,
snapshot-navigation-solution, position fix, iterated least squares,
post-fit residual (gnss-pseudorange-positioning); gnss-raim-fde,
protection level, fault detection, chi-square threshold,
normalized residual (gnss-raim-fde); gnss-rtk-positioning, double
difference, integer ambiguity, baseline (gnss-rtk-positioning);
gnss-doppler-velocity-positioning, delta range rate, clock drift,
broadcast ephemeris propagation (gnss-doppler-velocity-positioning);
dilution-of-precision, gdop, pdop, elevation mask, subset selection
(dilution-of-precision). 50-150 words, <=1000 chars, no em dash, no
content-policy sweep term, action verb present. Recommended wording
(outputs in Claim order, measured 142 words and 977 chars, no em dash):
"Use when you must correct the L1 pseudorange for the broadcast
ionospheric delay: apply the klobuchar-broadcast-model to the user
position and the satellite line of sight, compute the geomagnetic
latitude of the ionospheric pierce point from the earth-centred angle
and the azimuth, evaluate the amplitude and period quartic polynomials
in the broadcast alpha and beta coefficients at that geomagnetic
latitude, form the vertical delay from the 5 ns base and the day-curve
shape about the 14:00 local-time peak, and map the vertical delay to
the slant delay with the elevation obliquity factor. Produces the
pierce-point geomagnetic latitude, the amplitude and period
coefficients, the vertical delay in seconds and the slant ionospheric
delay in seconds and metres that gate the L1 pseudorange correction
before positioning. Trigger: klobuchar broadcast model, ionospheric
delay correction, slant delay correction, pierce point geometry,
broadcast alpha and beta coefficients." The sibling phrase triggers
"Hatch recursion", "carrier phase smoothing", "code-carrier
divergence", "divergence monitor", "smoothed range", "cycle slip",
"integer ambiguity", "position fix", "iterated least squares",
"receiver clock bias", "snapshot solution", "RAIM", "RTK", "double
difference", "delta range rate", "clock drift", "elevation mask",
"DOP", "protection level" and "ephemeris propagation" must not appear
as routing keywords; "Klobuchar", "broadcast ionospheric delay",
"pierce point" and "slant delay" are the leaf's own identity and must
stay, referring only to the per-source delay model of a single L1
line of sight, never to carrier smoothing, a divergence monitor, a
position fix or a differential or integrity technique.
