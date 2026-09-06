# Wave-43 leaf spec: rotorcraft-forward-flight-climb-test (flight-test-operations, performance pack)

- Path: skills/flight-test-operations/performance/rotorcraft-forward-flight-climb-test/
- Pack: performance (verified present at prep with accelerate-stop-distance,
  climb-performance-flight-test, cruise-performance-flight-test,
  engine-failure-takeoff-flight-test, engine-flight-test,
  fuel-jettison-flight-test, glide-flight-test,
  in-flight-engine-relight-test, landing-distance-determination,
  level-acceleration-test, rotorcraft-autorotation-flight-test,
  rotorcraft-forward-flight-performance-test,
  rotorcraft-performance-flight-test, stall-speed-determination,
  takeoff-distance-determination).
- Claim fences (quoted from the sibling frontmatter and body at prep, none
  owns the rotorcraft forward-flight climb sweep reduction):
  - climb-performance-flight-test (this pack) is FIXED-WING ONLY: its
    description opens "Use when you must run a climb performance flight
    test on a fixed-wing aircraft" and its method is imperial: "rate of
    climb in feet per minute from the pressure altitude change over a
    timed steady climb segment, correct the measured rate of climb for
    the test weight and the density altitude ... determine the service
    ceiling and the absolute ceiling where the best rate of climb decays
    to the threshold, integrate the time to climb". Its best-rate scan
    is the fixed-wing excess-power model best_rate_of_climb_fpm and its
    ceilings use the 100 ft/min jet convention; its standards are
    far-25/cs-25. Nothing in it accepts rotorcraft measured data, and a
    whole-tree grep at prep for "Vy|best rate of climb|best-rate-of-
    climb" across skills/**/SKILL.md hits ONLY this fixed-wing leaf.
  - rotorcraft-forward-flight-performance-test (this pack) is the LEVEL
    sweep: its claim reads "convert measured main rotor torque and rotor
    speed samples into shaft power across a forward-flight speed sweep,
    correct the measured power-required polar ... read off the
    best-endurance speed at the minimum-power point, the best-range
    speed at the tangent from the origin, and the maximum level-flight
    speed Vh"; its body states "It does NOT reduce hover or climb
    measured data (rotorcraft-performance-flight-test owns that)" - and
    that climb reference points at the VERTICAL climb correction of the
    hover leaf, not at a forward-flight climb sweep with Vy.
  - rotorcraft-performance-flight-test (this pack) is the hover axis:
    its claim covers "convert measured main rotor torque and rotor speed
    into shaft power, compute the measured figure of merit ... correct
    measured hover power to a reference weight and density altitude ...
    correct a measured vertical rate of climb for the test weight,
    reduce hover power-required points measured across density altitudes
    to a hover ceiling". Its climb content is the single-value weight
    correction of a VERTICAL (hover-axis) rate of climb,
    corrected_vertical_rate_of_climb: ROC_corr = ROC_meas * W_meas /
    W_ref, with no airspeed sweep, no Vy, no forward-flight ceiling.
  - flight-mechanics/performance/rotorcraft-vertical-climb-performance
    is the hover-axis momentum-theory PREDICTION: its description reads
    "compute the vertical climb performance of a rotorcraft rotor with
    axial momentum theory: the climb induced velocity from the hover
    induced velocity and the climb rate ... and the maximum vertical
    rate of climb for an available shaft power", and its body adds
    "Axial momentum theory only: uniform inflow, no ground effect,
    vertical climb only". No measured data, no airspeed sweep, no Vy.
  - flight-mechanics/performance/climb-performance is the fixed-wing
    excess-power PREDICTION (far-25/cs-25): "derive the rate of climb
    from thrust, drag, speed, and weight, convert the excess thrust into
    a climb gradient in percent ... and locate the service ceiling where
    the rate of climb decays to 0.5 m/s (100 ft/min)".
  - level-acceleration-test (this pack) is FIXED-WING (far-25/cs-25)
    and owns the total-energy reduction of an accelerated level-flight
    airspeed trace, "P_s = dh/dt + V a / g", its trigger
    specific-excess-power/total-energy-method. Where a rotorcraft climb
    sweep is flown as level accelerations, the trace reduction follows
    that method and the runs enter this leaf as per-run measured rates
    of climb; this leaf never implements the airspeed-trace reduction
    itself.
  Whole-tree greps at prep: "Vy|best rate of climb|best-rate-of-climb"
  hits exactly one SKILL.md (climb-performance-flight-test, fixed wing);
  "rotorcraft-forward-flight-climb-test", "best-rate-of-climb",
  "forward-flight climb" and "rate-of-climb sweep" each have 0 hits in
  eval/hit1-corpus.yaml; the rotorcraft-adjacent corpus tasks route on
  hover power and figure of merit (w31-rotorcraft-performance-flight-
  test), axial momentum theory (w31-rotorcraft-vertical-climb-
  performance), the level polar (w30-rotorcraft-forward-flight-
  performance), fixed-wing climb in ft/min (w18-climb-performance-
  flight-test) and the autorotation descent (w42-rotorcraft-autorotation-
  flight-test). GENUINE FTO gap (fresh probe, receipt C1, GO 2): no leaf
  reduces a rotorcraft FORWARD-FLIGHT climb sweep to Vy, the maximum
  rate of climb and the climb ceilings.
- Standards id: far-29 (exists in standards-map.yaml; sibling convention:
  every FTO rotorcraft leaf carries far-29 reference-only). Ledger
  Standard: far-29.
- Family: flight-test-operations

## Claim

Reduce a FAR 29 rotorcraft forward-flight climb flight test (name and
convention frame only, no verbatim rule text) from measured data, from
level-accelerated or steady-climb runs across an airspeed sweep: reduce
each run's pressure-altitude-versus-time window by least squares to the
measured rate of climb, convert the recorded calibrated airspeeds to
true airspeed at the test-day density ratio, correct every measured
rate of climb to the reference weight and the standard day at the run
altitude with the rho/weight ratio law (the weight ratio applied
linearly, the day's density-ratio deviation to the half power),
determine the best-rate-of-climb speed Vy at the peak of the corrected
ROC-versus-TAS curve (discrete maximum with neighbour check, refined by
the vertex of the parabola through the peak triplet), report the maximum
corrected rate of climb, and reduce Vy-schedule climb runs flown across
density altitudes to the climb ceilings: the service ceiling where the
corrected best rate of climb decays to the 0.5 m/s rotorcraft convention
(about 100 ft/min, the FAR 29 climb-demonstration framing) and the
absolute ceiling where it decays to zero, interpolated on the measured
density-altitude band. Produces the measured rate of climb and fit
quality per run, the corrected rates of climb, Vy with its m/s
equivalent, the maximum corrected rate of climb, and the service and
absolute ceiling altitudes (None outside the tested band, flagged in the
report) that gate the rotorcraft climb flight test assessment. Does NOT
do: the level-flight polar reduction from torque and rotor speed with
Vh (rotorcraft-forward-flight-performance-test); the hover-axis
reduction with measured figure of merit, hover power corrections or
hover ceilings and the single-value vertical-rate weight correction
(rotorcraft-performance-flight-test); the fixed-wing climb reduction in
feet per minute with the geometric-rate conversion, climb gradient and
time to climb (climb-performance-flight-test); the momentum-theory
prediction of vertical climb induced velocity or power from rotor
geometry (flight-mechanics/performance/rotorcraft-vertical-climb-
performance) or the fixed-wing excess-power prediction
(flight-mechanics/performance/climb-performance); the total-energy
reduction of an accelerated level-flight airspeed trace
(level-acceleration-test). Deterministic stdlib least squares and
closed forms only; every input is a flight test measurement, no RNG
anywhere.

## Model (implement exactly)

The prep-verified anchor /tmp/w43spec/anchor_rfwdclimb.py (pure stdlib,
math only, exit 0, byte-identical outputs under /usr/bin/python3 3.9.6
and the pyenv 3.13.12 hook interpreter) defines the implementation.
Constants (pin exactly): T0 = 288.15 K, LAPSE = 0.0065 K/m,
G0 = 9.80665 m/s^2, R_AIR = 287.053 J/(kg K), TROPOPAUSE_M = 11000.0,
K_DELTA = G0/(R_AIR*LAPSE) = 5.25588..., K_SIGMA = K_DELTA - 1 =
4.25588..., ALT_INV = T0/LAPSE = 44330.77 m, KTAS_TO_MPS = 1852.0/3600.0,
ROC_DENS_EXP = 0.5 (the rho/weight ratio law exponent), SERVICE_ROC_MPS
= 0.5, MIN_SAMPLES = 2, SWEEP_MIN = 4, SWEEP_MAX = 40. Airspeeds in kt
(CAS recorded, TAS axis), altitudes in m, OAT in C, weights in N, rates
of climb in m/s, mirroring the rotorcraft FTO siblings; the airspeed
axis stays in kt because the sweep is flown and quoted in knots.

Defining relations (pin these exactly):
- ISA troposphere at pressure altitude h_p: theta = 1 - LAPSE*h_p/T0,
  delta = theta**K_DELTA, sigma_ISA = theta**K_SIGMA.
- Test-day density ratio from the recorded OAT:
  sigma_test = delta(h_p) * T0/(OAT + 273.15), the altitude AND
  temperature content of the day. sigma_ref = sigma_ISA(h_p) is the
  standard day at the same pressure altitude.
- Density altitude of the test day: invert sigma_ISA, theta_da =
  sigma_test**(1/K_SIGMA), h_da = ALT_INV*(1 - theta_da).
- True airspeed: V = CAS/sqrt(sigma_test).
- Measured rate of climb: least-squares slope of the pressure altitude
  window against time, slope = (n*sum(t*h) - sum(t)*sum(h)) /
  (n*sum(t^2) - (sum(t))^2) in m/s (positive while climbing),
  r_squared = 1 - ss_res/ss_tot, defined as 1.0 when ss_tot is 0.
- The rho/weight ratio law (the correction of the measured rate):
  ROC_corr = ROC_meas * (W_test/W_ref) * (sigma_ref/sigma_test)**0.5.
  The weight enters linearly through the excess specific power
  (ROC = P_ex/W), and the day's density deviation enters to the half
  power: near the best-rate speed the rotor induced power, the dominant
  term of the climb power at fixed weight and airspeed, scales with the
  inverse square root of the density ratio while the flat-rated
  turboshaft available power does not lapse within its rating band. On
  the standard day at the reference weight the correction is identity.
  A hot day (sigma_test below sigma_ref) corrects the measured rate UP.
- Vy: the discrete maximum of the corrected ROC over the TAS sweep with
  a neighbour check; when the peak is interior and above both
  neighbours, refine with the vertex of the parabola through the peak
  triplet (Newton form y = y0 + d1*(x - x0) + a*(x - x0)*(x - x1),
  d1 = (y1 - y0)/(x1 - x0), d2 = (y2 - y1)/(x2 - x1),
  a = (d2 - d1)/(x2 - x0), vertex at xv = (x0 + x1)/2 - d1/(2*a) when
  a < 0 and xv lies inside the triplet). An endpoint peak reports Vy at
  the band edge with peak_bracketed False (the report flags that the
  sweep did not bracket Vy).
- Climb ceilings: the corrected best-rate points across density
  altitudes interpolate linearly to the altitude where the corrected
  ROC crosses SERVICE_ROC_MPS (0.5 m/s, service ceiling) and where it
  crosses zero (absolute ceiling); no crossing inside the tested band
  returns None for that ceiling and the report flags it.

Functions (implement exactly):
- isa_sigma(press_alt_m) -> float: theta**K_SIGMA of the ISA day at the
  pressure altitude. ValueError when press_alt_m is outside [0.0,
  TROPOPAUSE_M].
- pressure_altitude_sigma(press_alt_m, oat_c) -> float: test-day sigma,
  delta*T0/(oat_c + 273.15). Same altitude ValueError plus one for
  oat_c outside [-60.0, 60.0].
- density_altitude_m(press_alt_m, oat_c) -> float: the ISA altitude
  whose sigma equals the test-day sigma. ValueErrors as
  pressure_altitude_sigma; ValueError when the test-day sigma falls
  below isa_sigma(TROPOPAUSE_M) (density altitude above the tropopause
  is outside the model domain).
- tas_from_cas(cas_kt, sigma) -> float: cas_kt/sqrt(sigma) in kt.
  ValueError when cas_kt <= 0 (a forward-flight run has positive
  airspeed) or sigma <= 0.
- roc_from_altitude_samples(press_alt_m_list, time_s_list) -> dict
  {"roc_mps", "r_squared"}: the least-squares slope of the window in
  m/s, positive while climbing. ValueErrors: unequal list lengths,
  fewer than MIN_SAMPLES points, a zero fit denominator (all time
  samples equal), and a fitted slope <= 0 (no climb in the window; a
  level or descending window is not a climb run).
- corrected_roc(roc_mps, w_test_n, w_ref_n, sigma_test, sigma_ref) ->
  float: the rho/weight ratio law above. A negative measured rate (a
  run that sank at full power near the limit) is a valid input and
  corrects through the same law. ValueErrors: w_test_n <= 0,
  w_ref_n <= 0, sigma_test <= 0, sigma_ref <= 0.
- vy_and_max_roc(tas_kt_list, roc_mps_list) -> dict {"vy_kt", "vy_mps",
  "max_roc_mps", "peak_bracketed", "vertex_used"}: discrete maximum
  with neighbour check plus the parabola refinement above; vy_mps =
  vy_kt*KTAS_TO_MPS; max_roc_mps is the curve value at Vy (the vertex
  value when the vertex was used, the discrete value otherwise).
  ValueErrors: unequal list lengths, fewer than 3 points, TAS not
  strictly increasing (sweep order), and a maximum corrected ROC <= 0
  (no positive climb capability anywhere in the tested band).
- climb_ceilings(roc_corr_mps_list, density_alt_m_list) -> dict
  {"service_ceiling_m", "absolute_ceiling_m"}: linear interpolation of
  the first crossing of the 0.5 m/s threshold and of the zero crossing
  on the strictly increasing density-altitude axis; each value is a
  float when crossed inside the band and None otherwise. ValueErrors:
  unequal list lengths, fewer than 2 points, density altitudes not
  strictly increasing, any negative density altitude.
- reduce_forward_flight_climb_sweep(sweep_cas_kt, roc_meas_mps,
  w_test_n, w_ref_n, press_alt_m, oat_c) -> dict with keys exactly
  {"sigma_test", "sigma_ref", "density_altitude_m", "tas_kt",
  "roc_corr_mps", "vy_kt", "vy_mps", "max_roc_corr_mps",
  "peak_bracketed", "vertex_used"}: the one-call reduction of the
  sweep, chaining the atmosphere, TAS conversion, correction and Vy
  identification in that order. The per-run measured rates come from
  roc_from_altitude_samples on the run windows (workflow steps 2-3),
  or directly from level-accelerated runs pre-reduced by the
  total-energy method. ValueErrors: unequal list lengths, fewer than
  SWEEP_MIN or more than SWEEP_MAX runs (the 4-40 sweep convention of
  the level-polar sibling), calibrated airspeeds not strictly
  increasing, any non-positive CAS, and every underlying guard.

Identities to test (deterministic):
- Regression identity: roc_from_altitude_samples on altitude generated
  as 1000.0 + 5.0*t recovers roc_mps exactly 5.0 and r_squared 1.0
  (anchor: 5.000000000000000, r2 1.000000000).
- Correction identities: corrected_roc returns the input unchanged when
  W_test == W_ref and sigma_test == sigma_ref (anchor 6.000000000);
  with only the weight ratio active it returns roc*W_test/W_ref exactly
  (anchor 6.0 at 21,800 N to 21,000 N = 6.228571429); a hot day
  (sigma_test below sigma_ref) corrects UP (anchor 6.068938790 for
  6.0 at sigma 0.8870 to sigma_ref 0.9075).
- Airspeed round trip: tas_from_cas(cas, sigma)*sqrt(sigma) == cas to
  float noise (anchor: 75.34 kt at sigma 0.886994 gives TAS
  79.995448 kt, round trip 75.340000).
- Uniform scaling of every measured rate leaves Vy unchanged (the
  correction is a pure ratio law and the peak location is scale-free).
- Vertex property: the corrected curve peak sits at an interior point
  with both neighbours below it, the vertex falls inside the peak
  triplet, and max_roc_mps exceeds the discrete value by less than
  0.01 m/s (anchor: discrete 6.576710 at 79.995492 kt, vertex Vy
  79.064126 kt at 6.579021 m/s).
- Ceiling interpolation: the worked density-altitude series crosses
  0.5 m/s inside the band at the anchor service ceiling 6150.4 m and
  never crosses zero (absolute_ceiling_m None); a series that stays
  above the threshold returns None (anchor: [3.0, 2.5] m/s over
  [0, 1000] m gives None); an endpoint peak reports peak_bracketed
  False.
- Determinism: two runs of the reducer on identical inputs return
  identical dicts (anchor True); no imports beyond math.
- ValueErrors across the module: pressure altitude outside [0, 11000]
  m; OAT outside [-60, 60] C; density altitude above the tropopause;
  cas <= 0; sigma <= 0; unequal-length or single-sample windows; all-
  equal time samples; flat or descending windows (no climb); weights
  or sigmas <= 0; fewer than 3 sweep points; non-increasing TAS;
  all-sink sweeps; mismatched, single-point or non-monotone ceiling
  lists; negative density altitudes; sweeps outside 4-40 runs;
  non-increasing CAS. All raise ValueError (anchor-verified).

## Worked example

Measured forward-flight climb sweep of a light single-rotor helicopter
at W_test 21,800 N, W_ref 21,000 N: nine steady-climb runs across the
airspeed band flown at a fixed maximum power setting near the test
pressure altitude h_p = 1000 m with recorded OAT 15.00 C (ISA there is
8.5 C, so a warm day). Every run is a window of five pressure-altitude
samples at t = [0, 2, 4, 6, 8] s (2 s recorder averages of the steady
segment). All values below are REAL outputs of the prep anchor
/tmp/w43spec/anchor_rfwdclimb.py (pure stdlib, exit 0, identical under
3.9.6 and 3.13.12).

Test day: sigma_test 0.886993020 (warm day, below sigma_ref
0.907463301), density altitude 1231.677263 m. The window inputs and the
measured and corrected rates (windows in m; CAS is the recorded
calibrated airspeed):

- Run 1 (CAS 56.51 kt): window 920.30 930.66 941.86 952.32 963.53,
  ROC_meas 5.406000 m/s (r2 0.999827847), ROC_corr 5.676331 m/s.
- Run 2 (CAS 65.93 kt): window 931.75 944.40 956.04 968.49 980.28,
  ROC_meas 6.057500 m/s (r2 0.999846024), ROC_corr 6.360409 m/s.
- Run 3 (CAS 75.34 kt): window 944.30 956.37 969.29 981.46 994.39,
  ROC_meas 6.263500 m/s (r2 0.999868624), ROC_corr 6.576710 m/s.
- Run 4 (CAS 84.76 kt): window 955.75 968.20 979.66 991.91 1003.52,
  ROC_meas 5.962500 m/s (r2 0.999848109), ROC_corr 6.260659 m/s.
- Run 5 (CAS 94.18 kt): window 968.30 978.28 989.10 999.18 1010.00,
  ROC_meas 5.215000 m/s (r2 0.999818133), ROC_corr 5.475779 m/s.
- Run 6 (CAS 103.60 kt): window 979.75 988.68 996.61 1005.34 1013.42,
  ROC_meas 4.200000 m/s (r2 0.999686889), ROC_corr 4.410024 m/s.
- Run 7 (CAS 113.02 kt): window 992.30 998.09 1004.72 1010.61 1017.24,
  ROC_meas 3.120000 m/s (r2 0.999492060), ROC_corr 3.276018 m/s.
- Run 8 (CAS 122.43 kt): window 1003.75 1008.68 1012.61 1017.34
  1021.42, ROC_meas 2.200000 m/s (r2 0.998859773), ROC_corr 2.310012
  m/s.
- Run 9 (CAS 131.85 kt): window 1016.30 1018.66 1021.86 1024.32
  1027.53, ROC_meas 1.406000 m/s (r2 0.997460981), ROC_corr 1.476308
  m/s.

True airspeed per run (TAS = CAS/sqrt(sigma_test)): 60.001928, 70.004019,
79.995492, 89.997583, 99.999674, 110.001765, 120.003856, 129.995329,
139.997420 kt, the 60 to 140 KTAS sweep band. The corrected curve rises
from 5.676331 m/s at 60 kt to a peak of 6.576710 m/s at 80 kt and decays
to 1.476308 m/s at 140 kt.

Vy identification: the discrete peak sits at run 3 (TAS 79.995492 kt,
ROC_corr 6.576710 m/s), interior with both neighbours lower; the vertex
of the parabola through the 70-80-90 kt triplet refines it to
vy_kt 79.064126 (vy_mps 40.674100) with max_roc_corr_mps 6.579021,
peak_bracketed True, vertex_used True. The maximum corrected rate of
climb is 6.58 m/s (about 1295 ft/min) at a best-rate-of-climb speed of
about 79 kt, a representative result for the 21,000 N class with about
1300 ft/min of climb capability. reduce_forward_flight_climb_sweep run
on the recorded CAS list and the nine measured rates returns exactly
the dict {sigma_test 0.886993020, sigma_ref 0.907463301,
density_altitude_m 1231.677263, tas_kt as listed, roc_corr_mps as
listed, vy_kt 79.064126, vy_mps 40.674100, max_roc_corr_mps 6.579021,
peak_bracketed True, vertex_used True}.

Ceiling series: six additional Vy-schedule climbs (the IAS of the
best-rate run, about 75 kt CAS) flown at h_p 0 to 6000 m on days about
5 C warmer than ISA, each a five-sample window at t = [0, 2, 4, 6, 8] s:

- C1 (h_p 0 m, OAT 20.00 C, sigma_test 0.982943885, sigma_ref
  1.000000000): window 60.30 72.60 85.75 98.14 111.29, DA 178.8336 m,
  ROC_meas 6.376000 (r2 0.999874639), ROC_corr 6.676074041 m/s.
- C2 (h_p 1500 m, OAT 10.25 C, sigma_test 0.848489751, sigma_ref
  0.863728432): window 1559.75 1572.71 1584.67 1597.44 1609.55, DA
  1678.7675 m, ROC_meas 6.216500 (r2 0.999856515), ROC_corr
  6.511011229 m/s.
- C3 (h_p 3000 m, OAT 0.50 C, sigma_test 0.728580378, sigma_ref
  0.742140408): window 3060.30 3069.15 3078.86 3087.81 3097.51, DA
  3178.6967 m, ROC_meas 4.654000 (r2 0.999764272), ROC_corr
  4.876046983 m/s.
- C4 (h_p 4500 m, OAT -9.25 C, sigma_test 0.622087538, sigma_ref
  0.634101588): window 4559.75 4566.22 4571.68 4577.95 4583.56, DA
  4678.6206 m, ROC_meas 2.967500 (r2 0.999358722), ROC_corr
  3.110151870 m/s.
- C5 (h_p 5500 m, OAT -15.75 C, sigma_test 0.558011657, sigma_ref
  0.569065771): window 5560.30 5563.04 5566.64 5569.48 5573.07, DA
  5678.5667 m, ROC_meas 1.599000 (r2 0.998006564), ROC_corr
  1.676274964 m/s.
- C6 (h_p 6000 m, OAT -19.00 C, sigma_test 0.527933486, sigma_ref
  0.538528178): window 6059.75 6061.10 6061.45 6062.60 6063.10, DA
  6178.5387 m, ROC_meas 0.410000 (r2 0.968178546), ROC_corr
  0.429868544 m/s.

The corrected best-rate curve over the density-altitude band decays
from 6.676 m/s at DA 179 m to 0.430 m/s at DA 6179 m, bracketing the
0.5 m/s threshold. climb_ceilings on the six (ROC_corr, DA) points
returns service_ceiling_m = 6150.406816 m (about 20,180 ft, in the
plausible band for the 21,000 N class) and absolute_ceiling_m = None
(the zero crossing lies above the highest tested density altitude, so
the report flags the absolute ceiling as outside the tested band, the
same None-and-flag convention as the hover-ceiling sibling). Anchor
checks reproduced: the least-squares window on a perfect 1000 + 5.0*t
line recovers roc 5.000000000000000 with r2 1.000000000; the correction
is identity at the reference weight and day (6.000000000) and returns
exactly roc*W_test/W_ref when only the weight ratio acts
(6.228571429); tas_from_cas(75.34, 0.886994) = 79.995448 kt (round trip
exact); flat and descending windows, all-sink sweeps, non-monotone
density-altitude lists and 3-run sweeps all raise ValueError; the
reducer is deterministic across reruns. Run the anchor yourself and
take the real outputs as assert targets; the values above are its
actual output, recaptured by running python3
/tmp/w43spec/anchor_rfwdclimb.py (exit 0).

## Validation list (contract test must include)

- Atmosphere: pressure_altitude_sigma(1000.0, 15.0) = 0.886993020 within
  1e-6 and isa_sigma(1000.0) = 0.907463301 within 1e-6;
  density_altitude_m(1000.0, 15.0) = 1231.677263 within 0.01.
- Per-run anchors: the nine window reductions return the measured rates
  5.406000, 6.057500, 6.263500, 5.962500, 5.215000, 4.200000, 3.120000,
  2.200000, 1.406000 m/s within 1e-3 each, with r_squared in
  [0.997, 1.0]; the corrections return 5.676331, 6.360409, 6.576710,
  6.260659, 5.475779, 4.410024, 3.276018, 2.310012, 1.476308 m/s within
  1e-3.
- TAS: tas_from_cas on the recorded CAS list at sigma_test returns the
  listed TAS values within 1e-3 kt; round trip tas*sqrt(sigma) == CAS
  within 1e-6.
- Vy: vy_and_max_roc (and the reducer) return vy_kt 79.064126 within
  0.05, vy_mps 40.674100 within 0.03, max_roc_corr_mps 6.579021 within
  1e-3, peak_bracketed True, vertex_used True; the discrete max sits at
  the 80 kt run; both TAS neighbours of the peak sit below it.
- Reducer dict: all 10 keys exactly as documented with the worked
  values; vy_kt and vy_mps consistent through KTAS_TO_MPS.
- Ceiling series: the six corrections return 6.676074041, 6.511011229,
  4.876046983, 3.110151870, 1.676274964, 0.429868544 m/s within 1e-3;
  climb_ceilings returns service_ceiling_m 6150.406816 within 1.0 and
  absolute_ceiling_m None; a series above the threshold returns None
  for the service ceiling.
- Identities: regression recovery on a perfect line (5.0, r2 1.0);
  correction identity at reference weight and day; weight-ratio-only
  correction exactly roc*W_test/W_ref (6.228571429 at 21800/21000);
  hot-day up-correction 6.068938790 within 1e-6; uniform scaling of all
  measured rates leaves vy_kt unchanged to 1e-9; endpoint peak gives
  peak_bracketed False.
- ValueErrors: pressure altitude 12000 m and -1 m; OAT -70 C and 70 C;
  a test-day sigma below the tropopause sigma (density altitude above
  the model domain); cas 0; sigma 0; unequal-length and single-sample
  windows; all-equal time samples; flat and descending windows;
  w_test or w_ref at 0 and -1; sigma_test or sigma_ref at 0 and -1;
  a 2-point and a 41-point sweep; non-increasing CAS; a 3-point speed
  list; non-increasing TAS; an all-negative ROC sweep; mismatched
  ceiling lists; a single ceiling point; non-monotone density
  altitudes; a negative density altitude.
- Determinism: identical reducer dicts across repeated calls; no
  imports beyond math; module constants match the pinned values.

## Corpus fragment (eval/hit1-wave43-rotorcraft-forward-flight-climb-test.yaml)

Query 1 (copy verbatim):
  "reduce the rotorcraft-forward-flight-climb-test sweep from measured data: least-squares rate of climb from the steady climb pressure-altitude windows, corrected to the reference weight and standard day, to find the best-rate-of-climb speed and the maximum rate of climb"
  intent: "flight-test-operations; rotorcraft forward-flight climb sweep reduction to Vy and the maximum corrected rate of climb"
  expected_skill: "flight-test-operations/performance/rotorcraft-forward-flight-climb-test"
Query 2 (copy verbatim):
  "determine the forward-flight climb ceilings of the rotorcraft climb flight test: reduce the Vy-schedule climb runs measured across density altitudes to the service ceiling where the corrected rate of climb decays to the 0.5 m/s rotorcraft convention"
  intent: "flight-test-operations; rotorcraft climb ceilings from corrected best-rate points across density altitudes"
  expected_skill: "flight-test-operations/performance/rotorcraft-forward-flight-climb-test"
Task ids: w43-rotorcraft-forward-flight-climb-test-1 and -2. Prep greps:
"rotorcraft-forward-flight-climb-test", "best-rate-of-climb",
"forward-flight climb" and "rate-of-climb sweep" each appear in NO
existing eval/hit1-corpus.yaml task, and the rotorcraft-adjacent tasks
route on hover power and figure of merit (w31-rotorcraft-performance-
flight-test), axial momentum theory (w31-rotorcraft-vertical-climb-
performance), the analytic level polar (w30-rotorcraft-forward-flight-
performance), fixed-wing climb in feet per minute with the 100 ft/min
ceiling (w18-climb-performance-flight-test) and the autorotation
descent (w42-rotorcraft-autorotation-flight-test), so the queries above
are collision-free. The 0.5 m/s service-ceiling phrasing must always
carry the rotorcraft forward-flight context and the Vy-schedule basis;
never phrase a query as a fixed-wing feet-per-minute or climb-gradient
or time-to-climb task (those route to climb-performance-flight-test or
flight-mechanics/performance/climb-performance).

## Description/tag guidance (gate 1/2 and tag-steal rules)

Description must open "Use when you must reduce a rotorcraft forward-
flight climb flight test from measured data:" and include the outputs
in the Claim. First tag: rotorcraft-forward-flight-climb-test.
Additional tags ONLY: rotorcraft-climb-flight-test,
forward-flight-climb-sweep, measured-rate-of-climb,
best-rate-of-climb-speed, vy-determination, corrected-climb-rate,
rotorcraft-service-ceiling. NEVER single generic words (rotorcraft,
climb, rate, speed, ceiling, altitude, density, weight, correction,
flight, test, sweep, service) and NEVER the sibling tags
rate-of-climb, service-ceiling, climb-flight-test, pressure-altitude,
steady-climb, ceiling-determination (climb-performance-flight-test,
fixed wing), vertical-rate-of-climb (rotorcraft-performance-flight-test
and the FM vertical-climb leaf), level-flight-speed-sweep,
power-required-polar, vh-determination (rotorcraft-forward-flight-
performance-test). 50-150 words, <=1000 chars, no em dash, no
"classified", action verb present. Recommended wording (outputs in
Claim order): "Use when you must reduce a rotorcraft forward-flight
climb flight test from measured data: reduce the measured rate of climb
from the least-squares pressure-altitude windows of the steady climb
runs across the airspeed sweep, convert the calibrated airspeeds to
true airspeed at the test density, correct the measured rate of climb
to the reference weight and the standard day with the rho/weight ratio
law, identify the best-rate-of-climb speed Vy at the peak of the
corrected rate-of-climb curve, and reduce the Vy-schedule climb runs
across density altitudes to the service ceiling at the 0.5 m/s
rotorcraft convention. Produces the corrected rates of climb, Vy, the
maximum rate of climb and the climb ceilings that gate the rotorcraft
climb flight test assessment. Trigger: rotorcraft-forward-flight-climb-
test, rotorcraft climb flight test, best-rate-of-climb speed, measured
rate of climb, climb ceiling determination."

FORBIDDEN TOKENS (belong to siblings): rate-of-climb-in-feet-per-
minute, geometric-rate-conversion, climb-gradient, time-to-climb,
100-ft-min-ceiling, best-rate-of-climb-fpm (climb-performance-flight-
test, fixed wing); measured-figure-of-merit, torque-to-power,
hover-power-required, hover-ceiling, hover-ceiling-determination,
weight-density-power-correction, corrected-vertical-rate-of-climb
(rotorcraft-performance-flight-test, hover axis); power-required-polar,
torque-to-shaft-power, level-flight-speed-sweep, best-endurance-speed,
best-range-speed, vh-determination, max-continuous-power
(rotorcraft-forward-flight-performance-test); climb-induced-velocity,
axial-momentum-theory, momentum-theory, induced-power-factor,
available-shaft-power (flight-mechanics/performance/rotorcraft-
vertical-climb-performance); excess-thrust, excess-power,
thrust-available, specific-excess-power, total-energy-method,
level-acceleration-run (climb-performance, level-acceleration-test).
"Vy" in this leaf always means the best-rate-of-climb speed of the
rotorcraft forward-flight climb sweep; never quote the vertical
(hover-axis) climb, the fixed-wing feet-per-minute reduction or the
momentum-theory prediction, and never use the "estimate" or "predict"
phrasing of the flight-mechanics leaves: every input is a flight test
measurement and the corpus queries lead with the rotorcraft flight test
context.
