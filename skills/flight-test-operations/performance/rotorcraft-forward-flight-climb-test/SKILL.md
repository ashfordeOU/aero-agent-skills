---
name: rotorcraft-forward-flight-climb-test
description: "Use when you must reduce a rotorcraft forward-flight climb flight test from measured data: reduce the measured rate of climb from the least-squares pressure-altitude windows of the steady climb runs across the airspeed sweep, convert the calibrated airspeeds to true airspeed at the test density, correct the measured rate of climb to the reference weight and the standard day with the rho/weight ratio law, identify the best-rate-of-climb speed Vy at the peak of the corrected rate-of-climb curve, and reduce the Vy-schedule climb runs across density altitudes to the service ceiling at the 0.5 m/s rotorcraft convention. Produces the corrected rates of climb, Vy, the maximum rate of climb and the climb ceilings that gate the rotorcraft climb flight test assessment. Trigger: rotorcraft-forward-flight-climb-test, rotorcraft climb flight test, best-rate-of-climb speed, measured rate of climb, climb ceiling determination."
license: Apache-2.0
compliance: STANDARDS-REF
standards:
  - id: far-29
    reference-only: true
gated: false
domain: flight-test-operations
pack: performance
compatibility: "agentskills.io SKILL.md; any SKILL.md host (Claude Code, Hermes, OpenClaw)"
metadata:
  domain: flight-test-operations
  subdomain: performance
  tags: [rotorcraft-forward-flight-climb-test, rotorcraft-climb-flight-test, forward-flight-climb-sweep, measured-rate-of-climb, best-rate-of-climb-speed, vy-determination, corrected-climb-rate, rotorcraft-service-ceiling]
  version: 0.1.0
  author: AeroSkills
---

# Rotorcraft Forward-Flight Climb Test (flight-test-operations/performance/rotorcraft-forward-flight-climb-test)

Use when the task is reducing a FAR 29 rotorcraft forward-flight climb
flight test from MEASURED data: steady-climb or level-accelerated runs
across an airspeed sweep, each run a window of recorded pressure
altitude against time, reduced to the measured rate of climb by least
squares, corrected to the reference weight and the standard day with
the rho/weight ratio law, and read for the best-rate-of-climb speed Vy
and the maximum corrected rate of climb. Vy-schedule runs flown across
density altitudes reduce further to the climb ceilings. Every input is
a flight test measurement: recorder altitude and time samples,
calibrated airspeed, test and reference gross weights, pressure
altitude and outside air temperature; no RNG anywhere. It is the
rotorcraft forward-flight axis of the measured climb reduction trio in
this pack: the level-flight polar reduction from torque and rotor
speed (rotorcraft-forward-flight-performance-test) and the hover-axis
reduction with the vertical rate correction
(rotorcraft-performance-flight-test) are separate leaves, as are the
fixed-wing climb reduction in feet per minute
(climb-performance-flight-test), the analytic flight-mechanics
predictions of the vertical climb and of the climb ceilings, and the
airspeed-trace total-energy reduction (level-acceleration-test), whose
per-run measured rates enter this leaf as inputs when a sweep is flown
as level accelerations.

## Domain quick reference

- ISA troposphere at pressure altitude h_p: theta = 1 - LAPSE*h_p/T0,
  delta = theta**K_DELTA, sigma_ISA = theta**K_SIGMA. Module constants
  T0 = 288.15 K, LAPSE = 0.0065 K/m, G0 = 9.80665 m/s^2,
  R_AIR = 287.053 J/(kg K), tropopause 11000 m, K_DELTA = 5.25588...,
  K_SIGMA = 4.25588..., ALT_INV = 44330.77 m.
- Test-day density ratio from the recorded OAT:
  sigma_test = delta(h_p) * T0/(OAT + 273.15), the altitude AND
  temperature content of the day; sigma_ref = sigma_ISA(h_p) is the
  standard day at the same pressure altitude.
- Density altitude of the test day: invert sigma_ISA, theta_da =
  sigma_test**(1/K_SIGMA), h_da = ALT_INV*(1 - theta_da).
- True airspeed: V = CAS/sqrt(sigma_test). The airspeed axis stays in
  kt because the sweep is flown and quoted in knots; altitudes in m,
  OAT in C, weights in N, rates of climb in m/s.
- Measured rate of climb: least-squares slope of the pressure altitude
  window against time, slope = (n*sum(t*h) - sum(t)*sum(h)) /
  (n*sum(t^2) - (sum(t))^2) in m/s (positive while climbing), with
  r_squared = 1 - ss_res/ss_tot (1.0 when ss_tot is 0).
- The rho/weight ratio law: ROC_corr = ROC_meas * (W_test/W_ref) *
  (sigma_ref/sigma_test)**0.5. The weight enters linearly through the
  excess specific power (ROC = P_ex/W); the day's density deviation
  enters to the half power because near the best-rate speed the rotor
  induced power, the dominant term of the climb power at fixed weight
  and airspeed, scales with the inverse square root of the density
  ratio while the flat-rated turboshaft available power does not lapse
  within its rating band. Identity on the standard day at the reference
  weight; a hot day (sigma_test below sigma_ref) corrects the measured
  rate UP.
- Vy: the discrete maximum of the corrected ROC over the TAS sweep with
  a neighbour check; an interior peak above both neighbours refines
  with the vertex of the parabola through the peak triplet (Newton
  form, vertex at xv = (x0 + x1)/2 - d1/(2*a) when the curvature a < 0
  and xv lies inside the triplet). An endpoint peak reports Vy at the
  band edge with peak_bracketed False.
- Climb ceilings: the corrected best-rate points across density
  altitudes interpolate linearly to the altitude where the corrected
  ROC crosses 0.5 m/s (service ceiling, the FAR 29 climb-demonstration
  framing, about 100 ft/min) and where it crosses zero (absolute
  ceiling); no crossing inside the tested band returns None and the
  report flags it.
- FAR 29 frames the rotorcraft climb demonstration; the relations above
  are standard engineering methodology, name and convention only.

## Workflow

1. Fix the test configuration and the test-day atmosphere: the test
   gross weight W_test, the reference weight W_ref, the test pressure
   altitude h_p and the recorded OAT. pressure_altitude_sigma gives the
   test-day sigma_test, isa_sigma the standard-day sigma_ref, and
   density_altitude_m the density altitude of the day.
2. Reduce every run window to the measured rate of climb:
   roc_from_altitude_samples on the pressure-altitude-versus-time
   window of each steady climb run returns the measured rate of climb
   in m/s with the fit quality r_squared.
3. Convert the recorded airspeeds to true airspeed: tas_from_cas at
   sigma_test turns each recorded calibrated airspeed into the TAS of
   the run on the sweep axis.
4. Correct the measured rates of climb to the reference condition:
   corrected_roc applies the rho/weight ratio law to every measured
   rate, weight ratio linearly and the day's density-ratio deviation to
   the half power.
5. Identify the best-rate-of-climb speed Vy: vy_and_max_roc takes the
   corrected ROC-versus-TAS curve, locates the discrete maximum with
   the neighbour check, refines an interior peak with the parabola
   vertex, and returns vy_kt, vy_mps (through KTAS_TO_MPS), the maximum
   corrected rate of climb, peak_bracketed and vertex_used.
6. Run the one-call sweep reduction:
   reduce_forward_flight_climb_sweep chains steps 1, 3, 4 and 5 into
   the report dict with the keys sigma_test, sigma_ref,
   density_altitude_m, tas_kt, roc_corr_mps, vy_kt, vy_mps,
   max_roc_corr_mps, peak_bracketed, vertex_used. The per-run measured
   rates come from step 2 on the run windows, or directly from
   level-accelerated runs pre-reduced by the total-energy method of the
   level-acceleration-test leaf.
7. Reduce the Vy-schedule runs to the climb ceilings: repeat steps 2
   and 4 for the Vy-schedule climbs flown across density altitudes,
   then climb_ceilings interpolates the corrected best-rate curve to
   the service ceiling at 0.5 m/s and the absolute ceiling at zero
   (None outside the tested band, flagged in the report).
8. Confirm the deterministic checks with the contract test
   scripts/test_rotorcraft_forward_flight_climb_test.py.

## Worked example

Measured forward-flight climb sweep of a light single-rotor helicopter
at W_test 21,800 N, W_ref 21,000 N: nine steady-climb runs across the
airspeed band at a fixed maximum power setting near h_p = 1000 m with
recorded OAT 15.00 C (ISA there is 8.5 C, so a warm day). Every run is
a window of five pressure-altitude samples at t = [0, 2, 4, 6, 8] s.
Values below are the module's real outputs, identical under the system
python3 and the pyenv 3.13.12 hook interpreter.

- Test day: sigma_test 0.886993020 (warm day, below sigma_ref
  0.907463301), density altitude 1231.677263 m.
- Run windows (m) with the measured and corrected rates: run 1 CAS
  56.51 kt window 920.30 930.66 941.86 952.32 963.53 gives ROC_meas
  5.406000 m/s (r2 0.999827847) and ROC_corr 5.676331; run 2 CAS
  65.93 kt window 931.75 944.40 956.04 968.49 980.28 gives 6.057500
  and 6.360409; run 3 CAS 75.34 kt window 944.30 956.37 969.29 981.46
  994.39 gives 6.263500 and 6.576710; run 4 CAS 84.76 kt window 955.75
  968.20 979.66 991.91 1003.52 gives 5.962500 and 6.260659; run 5 CAS
  94.18 kt window 968.30 978.28 989.10 999.18 1010.00 gives 5.215000
  and 5.475779; run 6 CAS 103.60 kt window 979.75 988.68 996.61
  1005.34 1013.42 gives 4.200000 and 4.410024; run 7 CAS 113.02 kt
  window 992.30 998.09 1004.72 1010.61 1017.24 gives 3.120000 and
  3.276018; run 8 CAS 122.43 kt window 1003.75 1008.68 1012.61 1017.34
  1021.42 gives 2.200000 and 2.310012; run 9 CAS 131.85 kt window
  1016.30 1018.66 1021.86 1024.32 1027.53 gives 1.406000 and 1.476308.
  The r_squared values sit in [0.997460981, 0.999868624].
- True airspeed per run (CAS/sqrt(sigma_test)): 60.001928 to
  139.997420 kt, the 60 to 140 KTAS sweep band. The corrected curve
  rises from 5.676331 m/s at 60 kt to a peak of 6.576710 m/s at 80 kt
  and decays to 1.476308 m/s at 140 kt.
- Vy identification: the discrete peak sits at run 3 (TAS 79.995492
  kt, interior with both neighbours lower); the vertex of the parabola
  through the 70-80-90 kt triplet refines it to vy_kt 79.064126
  (vy_mps 40.674100) with max_roc_corr_mps 6.579021, peak_bracketed
  True, vertex_used True. The maximum corrected rate of climb is about
  6.58 m/s (about 1295 ft/min) at about 79 kt, representative for the
  21,000 N class.
- One-call reducer: reduce_forward_flight_climb_sweep on the recorded
  CAS list and the nine measured rates returns exactly the dict
  {sigma_test 0.886993020, sigma_ref 0.907463301, density_altitude_m
  1231.677263, tas_kt as listed, roc_corr_mps as listed, vy_kt
  79.064126, vy_mps 40.674100, max_roc_corr_mps 6.579021,
  peak_bracketed True, vertex_used True}.
- Ceiling series: six Vy-schedule climbs (the IAS of the best-rate run,
  about 75 kt CAS) flown at h_p 0 to 6000 m on days about 5 C warmer
  than ISA reduce to corrected best-rate points 6.676074041 (DA
  178.8336 m), 6.511011229 (DA 1678.7675 m), 4.876046983 (DA 3178.6967
  m), 3.110151870 (DA 4678.6206 m), 1.676274964 (DA 5678.5667 m) and
  0.429868544 m/s (DA 6178.5387 m), bracketing the 0.5 m/s threshold.
  climb_ceilings returns service_ceiling_m 6150.406816 m (about 20,180
  ft, in the plausible band for the 21,000 N class) and
  absolute_ceiling_m None: the zero crossing lies above the highest
  tested density altitude, so the report flags the absolute ceiling as
  outside the tested band.

## Verification

- Confirm pressure_altitude_sigma(1000.0, 15.0) returns 0.886993020,
  isa_sigma(1000.0) 0.907463301 and density_altitude_m(1000.0, 15.0)
  1231.677263 m.
- Confirm the nine window reductions return the measured rates above
  with r_squared in [0.997, 1.0], and the regression identity: a window
  on a perfect 1000 + 5.0*t line recovers 5.0 m/s with r_squared 1.0.
- Confirm the rho/weight law identities: corrected_roc returns the
  input unchanged at the reference weight and equal sigmas
  (6.000000000), exactly roc*W_test/W_ref when only the weight ratio
  acts (6.228571429 at 21,800 to 21,000 N), and a hot day corrects UP
  (6.068938790 for 6.0 m/s at sigma 0.8870 against 0.9075).
- Confirm the airspeed round trip: tas_from_cas(75.34, 0.886994) gives
  79.995448 kt and tas*sqrt(sigma) recovers the calibrated airspeed.
- Confirm Vy: vy_and_max_roc returns vy_kt 79.064126 within 0.05,
  vy_mps 40.674100 within 0.03 and max_roc_mps 6.579021 within 1e-3;
  uniform scaling of every rate leaves vy_kt unchanged (scale-free
  peak); an endpoint peak reports peak_bracketed False.
- Confirm the ceiling interpolation: the worked density-altitude series
  crosses 0.5 m/s at service_ceiling_m 6150.406816 m and never crosses
  zero (absolute_ceiling_m None); a series that stays above the
  threshold returns None for the service ceiling.
- Confirm ValueError rejection of every non-physical input: pressure
  altitude outside [0, 11000] m, OAT outside [-60, 60] C, a density
  altitude above the tropopause, non-positive CAS or sigma, unequal or
  single-sample windows, all-equal time samples, flat or descending
  windows, non-positive weights or sigmas, fewer than 3 speed points,
  non-increasing TAS, all-sink sweeps, sweeps outside 4-40 runs,
  non-increasing CAS, mismatched or single-point or non-monotone
  ceiling lists, and negative density altitudes.
- Confirm the reducer is deterministic across reruns and imports
  nothing beyond math.

## Related leaves

- skills/flight-test-operations/performance/rotorcraft-forward-flight-
  performance-test: the level-flight polar reduction from torque and
  rotor speed with the best-endurance, best-range and Vh read-offs,
  the sibling measured reduction of this pack.
- skills/flight-test-operations/performance/rotorcraft-performance-
  flight-test: the hover-axis measured reduction with figure of merit,
  hover power corrections and hover ceilings, and the vertical-rate
  weight correction of the hover climb.
- skills/flight-test-operations/performance/climb-performance-flight-
  test: the fixed-wing climb flight test in feet per minute with the
  100 ft/min ceiling convention.
- skills/flight-test-operations/performance/level-acceleration-test:
  the total-energy airspeed-trace reduction whose per-run measured
  rates enter this leaf when the climb sweep is flown as level
  accelerations.
- skills/flight-test-operations/performance/rotorcraft-autorotation-
  flight-test: the rotorcraft descent-axis flight test of this pack.
- skills/flight-mechanics/performance/rotorcraft-vertical-climb-
  performance: the hover-axis axial momentum theory prediction of
  vertical climb, the analytic counterpart of the measured hover climb.
- skills/flight-mechanics/performance/climb-performance: the fixed-wing
  climb prediction leaf for the rate of climb and ceilings.

## Pitfalls

- Quoting the corrected maximum rate as if it were measured: the
  corrected curve peak 6.579021 m/s is the standard-day value at the
  reference weight; the measured sweep peaked at 6.263500 m/s on the
  test day at the heavier weight, and reporting the measured peak
  without the correction understates the climb capability.
- Applying a linear density correction: the day's density-ratio
  deviation enters to the HALF power in the rho/weight ratio law
  ((sigma_ref/sigma_test)**0.5), not linearly; the weight ratio is the
  only linear factor.
- Treating an endpoint peak as the best-rate speed: an endpoint peak
  reports Vy at the band edge with peak_bracketed False, which means
  the sweep did not bracket Vy; extend the sweep before quoting the
  best-rate speed.
- Extrapolating a ceiling outside the tested band: climb_ceilings
  returns None when the corrected best-rate curve does not cross the
  threshold or zero inside the measured density-altitude band; the
  report must flag the ceiling as outside the tested band rather than
  guessing an extrapolation.
- Mixing this leaf with the fixed-wing climb reduction: this leaf is in
  m/s with the 0.5 m/s rotorcraft service-ceiling convention and the
  Vy-schedule basis; the fixed-wing leaf works in feet per minute with
  climb gradient and time to climb, and the level-acceleration leaf
  owns the airspeed-trace reduction itself.
- Feeding hover or vertical climb data: this leaf reduces the
  forward-flight climb sweep only; hover-axis data with the vertical
  rate correction belongs to the rotorcraft-performance-flight-test
  leaf.

## Behavior contract (gate 3)

Run the deterministic contract test (stdlib unittest, offline):

    python3 skills/flight-test-operations/performance/\
rotorcraft-forward-flight-climb-test/scripts/\
test_rotorcraft_forward_flight_climb_test.py

The test covers the worked-example contract with the module's real
outputs as targets: the step-1 atmosphere reduction of the test day,
the step-2 measured rate of climb of each least-squares
pressure-altitude window with fit quality, the step-3 true airspeed
conversion of the recorded calibrated airspeeds, the step-4 corrected
rates of climb through the rho/weight ratio law, the step-5 Vy
identification with the parabola vertex refinement, the step-6 one-call
sweep reduction dict with all ten keys and its determinism, the step-7
Vy-schedule climb ceilings over the density-altitude band, the
closed-form identities (regression recovery, correction identity,
weight-ratio-only scaling, airspeed round trip, uniform-scale Vy
invariance), the pinned module constants, and ValueError rejection of
every non-physical input in the spec validation list. It also passes
under the pyenv 3.13.12 hook interpreter.

## Compliance

- Standards referenced, not reproduced: FAR 29 frames the rotorcraft
  climb demonstration; this leaf implements standard flight-test
  reduction methodology, summary-only per standards-map.yaml, no
  verbatim rule text.
- compliance: STANDARDS-REF, gated: false.
