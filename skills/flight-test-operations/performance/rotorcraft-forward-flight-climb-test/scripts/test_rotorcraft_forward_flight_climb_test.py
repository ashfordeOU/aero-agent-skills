"""Contract test for the rotorcraft-forward-flight-climb-test logic module.

Deterministic stdlib unittest, offline, no RNG. Run from the repo root
(or the leaf directory):

    python3 skills/flight-test-operations/performance/\\
rotorcraft-forward-flight-climb-test/scripts/\\
test_rotorcraft_forward_flight_climb_test.py

Covers the wave-43 spec worked example with the module's REAL outputs as
assert targets: the step-1 atmosphere reduction of the test day
(sigma_test about 0.886993020, sigma_ref about 0.907463301, density
altitude about 1231.677263 m), the step-2 measured rate of climb of each
least-squares pressure-altitude window (5.406000 down to 1.406000 m/s
with fit quality above 0.997), the step-3 true airspeed conversion of
the recorded calibrated airspeeds (60.001928 to 139.997420 KTAS), the
step-4 corrected rates of climb through the rho/weight ratio law
(5.676331 to 1.476308 m/s at the reference weight on the standard day),
the step-5 best-rate-of-climb speed Vy identification at about
79.064126 kt with the parabola vertex refinement, the step-6 one-call
sweep reduction dict with all ten keys, the step-7 Vy-schedule climb
ceilings over the density-altitude band (service ceiling about
6150.406816 m, absolute ceiling None outside the tested band), the
closed-form identities (regression recovery, correction identity,
weight-ratio-only scaling, airspeed round trip, uniform-scale Vy
invariance), determinism, the pinned module constants, and the
ValueError rejection of every non-physical input listed in the spec.
"""

import math
import os
import sys
import types
import unittest

sys.path.insert(
    0, os.path.dirname(os.path.abspath(__file__)))
import rotorcraft_forward_flight_climb_test_logic as rfc

# --- worked-example data (wave-43 spec, real module outputs as targets) ---
TIME_S = [0.0, 2.0, 4.0, 6.0, 8.0]
W_TEST = 21800.0
W_REF = 21000.0
H_P = 1000.0
OAT = 15.0

SWEEP_CAS = [56.51, 65.93, 75.34, 84.76, 94.18,
             103.60, 113.02, 122.43, 131.85]
SWEEP_WINDOWS = [
    [920.30, 930.66, 941.86, 952.32, 963.53],
    [931.75, 944.40, 956.04, 968.49, 980.28],
    [944.30, 956.37, 969.29, 981.46, 994.39],
    [955.75, 968.20, 979.66, 991.91, 1003.52],
    [968.30, 978.28, 989.10, 999.18, 1010.00],
    [979.75, 988.68, 996.61, 1005.34, 1013.42],
    [992.30, 998.09, 1004.72, 1010.61, 1017.24],
    [1003.75, 1008.68, 1012.61, 1017.34, 1021.42],
    [1016.30, 1018.66, 1021.86, 1024.32, 1027.53],
]
ROC_MEAS = [5.406000, 6.057500, 6.263500, 5.962500, 5.215000,
            4.200000, 3.120000, 2.200000, 1.406000]
TAS_KT = [60.001928, 70.004019, 79.995492, 89.997583, 99.999674,
          110.001765, 120.003856, 129.995329, 139.997420]
ROC_CORR = [5.676331, 6.360409, 6.576710, 6.260659, 5.475779,
            4.410024, 3.276018, 2.310012, 1.476308]

CEILING_PRESS_ALT = [0.0, 1500.0, 3000.0, 4500.0, 5500.0, 6000.0]
CEILING_OAT = [20.0, 10.25, 0.5, -9.25, -15.75, -19.0]
CEILING_WINDOWS = [
    [60.30, 72.60, 85.75, 98.14, 111.29],
    [1559.75, 1572.71, 1584.67, 1597.44, 1609.55],
    [3060.30, 3069.15, 3078.86, 3087.81, 3097.51],
    [4559.75, 4566.22, 4571.68, 4577.95, 4583.56],
    [5560.30, 5563.04, 5566.64, 5569.48, 5573.07],
    [6059.75, 6061.10, 6061.45, 6062.60, 6063.10],
]
CEILING_ROC_MEAS = [6.376000, 6.216500, 4.654000, 2.967500,
                    1.599000, 0.410000]
CEILING_ROC_CORR = [6.676074041, 6.511011229, 4.876046983, 3.110151870,
                    1.676274964, 0.429868544]
CEILING_DA = [178.8336, 1678.7675, 3178.6967, 4678.6206,
              5678.5667, 6178.5387]


class AtmosphereTests(unittest.TestCase):
    """Workflow step 1 (fix the test configuration and the test-day
    atmosphere) exercised by the atmosphere tests."""

    def test_test_day_density_ratio_of_the_worked_sweep_day(self):
        """Step 1: pressure_altitude_sigma at h_p 1000 m and OAT 15 C
        returns the warm-day density ratio 0.886993020 (within 1e-6),
        below the ISA reference day, and density_altitude_m returns the
        day's density altitude 1231.677263 m (within 0.01)."""
        sigma_test = rfc.pressure_altitude_sigma(H_P, OAT)
        self.assertAlmostEqual(sigma_test, 0.886993020, delta=1e-6)
        self.assertLess(sigma_test, rfc.isa_sigma(H_P))
        self.assertAlmostEqual(
            rfc.density_altitude_m(H_P, OAT), 1231.677263, delta=0.01)

    def test_isa_density_ratio_profile_over_the_troposphere(self):
        """Step 1: isa_sigma is 1.0 at sea level, returns 0.907463301 at
        1000 m (within 1e-6, the reference-day density ratio), and is
        strictly decreasing to about 0.2971 at the tropopause."""
        self.assertAlmostEqual(rfc.isa_sigma(0.0), 1.0, delta=1e-12)
        self.assertAlmostEqual(rfc.isa_sigma(H_P), 0.907463301, delta=1e-6)
        self.assertLess(rfc.isa_sigma(5000.0), rfc.isa_sigma(0.0))
        self.assertLess(rfc.isa_sigma(rfc.TROPOPAUSE_M), rfc.isa_sigma(5000.0))
        self.assertAlmostEqual(rfc.isa_sigma(rfc.TROPOPAUSE_M),
                               0.2971, delta=0.001)

    def test_atmosphere_valueerrors_for_out_of_domain_altitude_and_oat(self):
        """Step 1: a pressure altitude of 12000 m or -1 m and an OAT of
        -70 C or 70 C all raise ValueError."""
        for bad_alt in (12000.0, -1.0):
            with self.assertRaises(ValueError):
                rfc.isa_sigma(bad_alt)
            with self.assertRaises(ValueError):
                rfc.pressure_altitude_sigma(bad_alt, 15.0)
        for bad_oat in (-70.0, 70.0):
            with self.assertRaises(ValueError):
                rfc.pressure_altitude_sigma(1000.0, bad_oat)

    def test_density_altitude_above_the_tropopause_is_rejected(self):
        """Step 1: a very hot day whose test-day sigma falls below the
        tropopause sigma raises ValueError (density altitude above the
        model domain)."""
        with self.assertRaises(ValueError):
            rfc.density_altitude_m(10000.0, 60.0)


class MeasuredRocTests(unittest.TestCase):
    """Workflow step 2 (reduce every run window to the measured rate of
    climb) exercised by the window reduction tests."""

    def test_measured_rates_of_climb_of_the_nine_sweep_windows(self):
        """Step 2: the least-squares pressure-altitude window of every
        steady climb run reduces to the measured rate of climb
        5.406000 down to 1.406000 m/s (each within 1e-3)."""
        for window, expected in zip(SWEEP_WINDOWS, ROC_MEAS):
            result = rfc.roc_from_altitude_samples(window, TIME_S)
            self.assertAlmostEqual(result["roc_mps"], expected, delta=1e-3)

    def test_fit_quality_of_the_nine_windows_is_high(self):
        """Step 2: the r_squared fit quality of every run window lies in
        [0.997, 1.0], the recorder-grade scatter band."""
        for window in SWEEP_WINDOWS:
            result = rfc.roc_from_altitude_samples(window, TIME_S)
            self.assertGreaterEqual(result["r_squared"], 0.997)
            self.assertLessEqual(result["r_squared"], 1.0)

    def test_regression_identity_recovers_the_exact_slope(self):
        """Step 2: a window generated as a perfect 1000 + 5.0*t line
        recovers the measured rate of climb 5.0 m/s with r_squared 1.0,
        the regression identity of the least-squares slope."""
        perfect = [1000.0 + 5.0 * t for t in TIME_S]
        result = rfc.roc_from_altitude_samples(perfect, TIME_S)
        self.assertAlmostEqual(result["roc_mps"], 5.0, delta=1e-9)
        self.assertAlmostEqual(result["r_squared"], 1.0, delta=1e-9)

    def test_window_valueerrors_reject_non_climb_inputs(self):
        """Step 2: unequal-length and single-sample windows, all-equal
        time samples, and flat or descending (no-climb) windows all
        raise ValueError."""
        with self.assertRaises(ValueError):
            rfc.roc_from_altitude_samples([1000.0, 1010.0], [0.0])
        with self.assertRaises(ValueError):
            rfc.roc_from_altitude_samples([1000.0], [0.0])
        with self.assertRaises(ValueError):
            rfc.roc_from_altitude_samples([1000.0, 1010.0, 1020.0],
                                          [5.0, 5.0, 5.0])
        with self.assertRaises(ValueError):
            rfc.roc_from_altitude_samples([1000.0, 1000.0, 1000.0],
                                          [0.0, 1.0, 2.0])
        with self.assertRaises(ValueError):
            rfc.roc_from_altitude_samples([1000.0, 995.0, 990.0],
                                          [0.0, 1.0, 2.0])


class TrueAirspeedTests(unittest.TestCase):
    """Workflow step 3 (convert the recorded airspeeds to true airspeed)
    exercised by the airspeed conversion tests."""

    def test_true_airspeed_of_the_nine_runs(self):
        """Step 3: tas_from_cas at the test-day density ratio converts
        the recorded calibrated airspeeds to the 60.001928 to
        139.997420 KTAS sweep (each within 1e-3 kt)."""
        sigma_test = rfc.pressure_altitude_sigma(H_P, OAT)
        for cas, expected in zip(SWEEP_CAS, TAS_KT):
            self.assertAlmostEqual(
                rfc.tas_from_cas(cas, sigma_test), expected, delta=1e-3)

    def test_airspeed_round_trip_recovers_calibrated_airspeed(self):
        """Step 3: the TAS round trip tas*sqrt(sigma) recovers the
        calibrated airspeed exactly; tas_from_cas(75.34, 0.886994) gives
        79.995448 kt, the round-trip check holding to 1e-6 kt."""
        tas = rfc.tas_from_cas(75.34, 0.886994)
        self.assertAlmostEqual(tas, 79.995448, delta=1e-3)
        self.assertAlmostEqual(tas * math.sqrt(0.886994), 75.34, delta=1e-6)

    def test_true_airspeed_valueerrors(self):
        """Step 3: a non-positive calibrated airspeed and a non-positive
        density ratio both raise ValueError."""
        for bad_cas in (0.0, -10.0):
            with self.assertRaises(ValueError):
                rfc.tas_from_cas(bad_cas, 0.9)
        for bad_sigma in (0.0, -0.1):
            with self.assertRaises(ValueError):
                rfc.tas_from_cas(100.0, bad_sigma)


class CorrectionTests(unittest.TestCase):
    """Workflow step 4 (correct the measured rates of climb to the
    reference condition) exercised by the rho/weight ratio law tests."""

    def test_corrected_rates_of_climb_of_the_nine_runs(self):
        """Step 4: corrected_roc on the nine measured rates at W_test
        21800 N, W_ref 21000 N on the warm test day returns 5.676331 to
        1.476308 m/s (each within 1e-3), all above the measured values
        because the warm day and the overweight test both cost climb."""
        sigma_test = rfc.pressure_altitude_sigma(H_P, OAT)
        sigma_ref = rfc.isa_sigma(H_P)
        for meas, expected in zip(ROC_MEAS, ROC_CORR):
            corr = rfc.corrected_roc(meas, W_TEST, W_REF,
                                     sigma_test, sigma_ref)
            self.assertAlmostEqual(corr, expected, delta=1e-3)

    def test_correction_is_identity_at_reference_weight_and_day(self):
        """Step 4: corrected_roc at the reference weight and an equal
        sigma pair returns the measured rate unchanged (identity anchor
        6.000000000), the standard-day reference-condition check."""
        self.assertAlmostEqual(
            rfc.corrected_roc(6.0, 21000.0, 21000.0, 0.9, 0.9),
            6.0, delta=1e-12)

    def test_weight_ratio_only_correction_scales_linearly(self):
        """Step 4: with only the weight ratio active the correction is
        exactly roc*W_test/W_ref, 6.228571429 at 21800 to 21000 N (the
        weight enters linearly through the excess specific power)."""
        result = rfc.corrected_roc(6.0, W_TEST, W_REF,
                                   0.907473865, 0.907473865)
        self.assertAlmostEqual(result, 6.228571429, delta=1e-9)
        self.assertAlmostEqual(result, 6.0 * W_TEST / W_REF, delta=1e-9)

    def test_hot_day_corrects_the_measured_rate_up(self):
        """Step 4: a hot day (sigma_test below sigma_ref) corrects the
        measured rate UP through the half-power density term:
        6.068938790 for 6.0 m/s at sigma 0.8870 against 0.9075, and a
        cold day corrects down."""
        hot = rfc.corrected_roc(6.0, 21000.0, 21000.0, 0.8870, 0.9075)
        self.assertAlmostEqual(hot, 6.068938790, delta=1e-6)
        self.assertGreater(hot, 6.0)
        cold = rfc.corrected_roc(6.0, 21000.0, 21000.0, 0.9200, 0.9075)
        self.assertLess(cold, 6.0)

    def test_negative_measured_rate_corrects_through_the_same_law(self):
        """Step 4: a run that sank at full power (negative measured
        rate) is a valid input and corrects through the same rho/weight
        ratio law, staying negative."""
        result = rfc.corrected_roc(-1.5, W_TEST, W_REF, 0.8870, 0.9075)
        self.assertLess(result, 0.0)
        self.assertAlmostEqual(result, -1.5 * (W_TEST / W_REF) *
                               (0.9075 / 0.8870) ** 0.5, delta=1e-9)

    def test_correction_valueerrors_reject_non_physical_inputs(self):
        """Step 4: non-positive test or reference weights and
        non-positive density ratios all raise ValueError."""
        for bad_w in (0.0, -1.0):
            with self.assertRaises(ValueError):
                rfc.corrected_roc(5.0, bad_w, W_REF, 0.9, 0.9)
            with self.assertRaises(ValueError):
                rfc.corrected_roc(5.0, W_TEST, bad_w, 0.9, 0.9)
        for bad_sigma in (0.0, -0.5):
            with self.assertRaises(ValueError):
                rfc.corrected_roc(5.0, W_TEST, W_REF, bad_sigma, 0.9)
            with self.assertRaises(ValueError):
                rfc.corrected_roc(5.0, W_TEST, W_REF, 0.9, bad_sigma)


class VyIdentificationTests(unittest.TestCase):
    """Workflow step 5 (identify the best-rate-of-climb speed Vy)
    exercised by the peak and vertex refinement tests."""

    def test_vy_and_maximum_roc_of_the_worked_sweep(self):
        """Step 5: vy_and_max_roc on the corrected curve returns
        vy_kt 79.064126 (within 0.05), vy_mps 40.674100 (within 0.03,
        the m/s equivalent), max_roc_mps 6.579021 (within 1e-3), with
        peak_bracketed True and vertex_used True."""
        result = rfc.vy_and_max_roc(TAS_KT, ROC_CORR)
        self.assertAlmostEqual(result["vy_kt"], 79.064126, delta=0.05)
        self.assertAlmostEqual(result["vy_mps"], 40.674100, delta=0.03)
        self.assertAlmostEqual(result["max_roc_mps"], 6.579021, delta=1e-3)
        self.assertTrue(result["peak_bracketed"])
        self.assertTrue(result["vertex_used"])

    def test_discrete_peak_sits_at_the_80_kt_run_with_both_neighbours_lower(self):
        """Step 5: the discrete maximum of the corrected curve sits at
        the 80 KTAS run (index 2, value 6.576710 m/s) and both TAS
        neighbours of the peak lie below it."""
        peak = ROC_CORR.index(max(ROC_CORR))
        self.assertEqual(peak, 2)
        self.assertAlmostEqual(TAS_KT[peak], 79.995492, delta=1e-3)
        self.assertLess(ROC_CORR[1], ROC_CORR[2])
        self.assertLess(ROC_CORR[3], ROC_CORR[2])

    def test_vertex_refinement_stays_inside_the_peak_triplet(self):
        """Step 5: the parabola vertex through the 70-80-90 kt peak
        triplet falls inside the triplet and max_roc_mps exceeds the
        discrete value by less than 0.01 m/s (the vertex property)."""
        result = rfc.vy_and_max_roc(TAS_KT, ROC_CORR)
        self.assertGreater(result["vy_kt"], TAS_KT[1])
        self.assertLess(result["vy_kt"], TAS_KT[3])
        self.assertLess(result["max_roc_mps"] - ROC_CORR[2], 0.01)

    def test_uniform_scaling_of_the_rates_leaves_vy_unchanged(self):
        """Step 5: uniform scaling of every measured rate leaves vy_kt
        unchanged to 1e-9 because the correction is a pure ratio law and
        the peak location is scale-free (the scaled maximum rate is
        exactly double the original)."""
        baseline = rfc.vy_and_max_roc(TAS_KT, ROC_CORR)
        scaled = [2.0 * r for r in ROC_CORR]
        result = rfc.vy_and_max_roc(TAS_KT, scaled)
        self.assertAlmostEqual(result["vy_kt"], baseline["vy_kt"],
                               delta=1e-9)
        self.assertAlmostEqual(result["vy_kt"], 79.064126, delta=0.05)
        self.assertAlmostEqual(result["max_roc_mps"],
                               2.0 * baseline["max_roc_mps"], delta=1e-9)

    def test_endpoint_peak_reports_the_band_edge_unbracketed(self):
        """Step 5: a monotone rising curve peaks at the band edge and
        reports vy_kt at the last point with peak_bracketed False, the
        flag that the sweep did not bracket the best-rate speed."""
        result = rfc.vy_and_max_roc([60.0, 70.0, 80.0], [1.0, 2.0, 3.0])
        self.assertEqual(result["vy_kt"], 80.0)
        self.assertFalse(result["peak_bracketed"])
        self.assertFalse(result["vertex_used"])

    def test_vy_valueerrors_reject_malformed_sweeps(self):
        """Step 5: unequal speed and ROC lists, fewer than 3 points,
        non-increasing TAS (sweep order) and an all-negative ROC sweep
        (no positive climb capability in the band) all raise
        ValueError."""
        with self.assertRaises(ValueError):
            rfc.vy_and_max_roc([60.0, 70.0], [5.0, 6.0, 5.0])
        with self.assertRaises(ValueError):
            rfc.vy_and_max_roc([60.0, 70.0], [5.0, 6.0])
        with self.assertRaises(ValueError):
            rfc.vy_and_max_roc([80.0, 70.0, 60.0], [5.0, 6.0, 5.0])
        with self.assertRaises(ValueError):
            rfc.vy_and_max_roc([60.0, 70.0, 80.0], [-1.0, -2.0, -3.0])


class SweepReducerTests(unittest.TestCase):
    """Workflow step 6 (run the one-call sweep reduction) exercised by
    the reducer tests."""

    def test_reducer_returns_the_worked_dict_with_all_ten_keys(self):
        """Step 6: reduce_forward_flight_climb_sweep on the recorded CAS
        list and the nine measured rates returns exactly the ten
        documented keys sigma_test, sigma_ref, density_altitude_m,
        tas_kt, roc_corr_mps, vy_kt, vy_mps, max_roc_corr_mps,
        peak_bracketed and vertex_used with the worked values."""
        red = rfc.reduce_forward_flight_climb_sweep(
            SWEEP_CAS, ROC_MEAS, W_TEST, W_REF, H_P, OAT)
        self.assertEqual(
            set(red.keys()),
            {"sigma_test", "sigma_ref", "density_altitude_m", "tas_kt",
             "roc_corr_mps", "vy_kt", "vy_mps", "max_roc_corr_mps",
             "peak_bracketed", "vertex_used"})
        self.assertAlmostEqual(red["sigma_test"], 0.886993020, delta=1e-6)
        self.assertAlmostEqual(red["sigma_ref"], 0.907463301, delta=1e-6)
        self.assertAlmostEqual(red["density_altitude_m"], 1231.677263,
                               delta=0.01)
        self.assertEqual(len(red["tas_kt"]), 9)
        self.assertEqual(len(red["roc_corr_mps"]), 9)
        self.assertTrue(red["peak_bracketed"])
        self.assertTrue(red["vertex_used"])

    def test_reducer_vy_is_consistent_with_ktas_to_mps(self):
        """Step 6: the reducer's vy_mps equals vy_kt through the
        KTAS_TO_MPS factor and the corrected curve peaks at the same
        best-rate-of-climb speed as the direct step-5 call."""
        red = rfc.reduce_forward_flight_climb_sweep(
            SWEEP_CAS, ROC_MEAS, W_TEST, W_REF, H_P, OAT)
        self.assertAlmostEqual(red["vy_mps"],
                               red["vy_kt"] * rfc.KTAS_TO_MPS, delta=1e-9)
        direct = rfc.vy_and_max_roc(red["tas_kt"], red["roc_corr_mps"])
        self.assertAlmostEqual(red["vy_kt"], direct["vy_kt"], delta=1e-9)
        self.assertAlmostEqual(red["max_roc_corr_mps"],
                               direct["max_roc_mps"], delta=1e-9)

    def test_reducer_is_deterministic_and_stdlib_only(self):
        """Step 6: repeated calls of the one-call sweep reduction on
        identical inputs return identical dicts and the module imports
        nothing beyond math."""
        red1 = rfc.reduce_forward_flight_climb_sweep(
            SWEEP_CAS, ROC_MEAS, W_TEST, W_REF, H_P, OAT)
        red2 = rfc.reduce_forward_flight_climb_sweep(
            SWEEP_CAS, ROC_MEAS, W_TEST, W_REF, H_P, OAT)
        self.assertEqual(red1, red2)
        modules = [name for name, value in vars(rfc).items()
                   if isinstance(value, types.ModuleType)]
        self.assertEqual(modules, ["math"])

    def test_reducer_valueerrors_reject_malformed_sweeps(self):
        """Step 6: a 3-run sweep (outside the 4-40 convention), a
        41-run sweep, non-increasing CAS, mismatched CAS and ROC lists
        and a non-positive CAS element all raise ValueError."""
        three = rfc.reduce_forward_flight_climb_sweep
        with self.assertRaises(ValueError):
            three([60.0, 70.0, 80.0], [5.0, 6.0, 5.0],
                  W_TEST, W_REF, H_P, OAT)
        big_cas = list(range(56, 96))
        big_roc = [5.0 + i * 0.01 for i in range(40)]
        with self.assertRaises(ValueError):
            three(big_cas + [200.0], big_roc + [6.0],
                  W_TEST, W_REF, H_P, OAT)
        with self.assertRaises(ValueError):
            three(list(reversed(SWEEP_CAS)), ROC_MEAS,
                  W_TEST, W_REF, H_P, OAT)
        with self.assertRaises(ValueError):
            three(SWEEP_CAS, ROC_MEAS[:5], W_TEST, W_REF, H_P, OAT)
        with self.assertRaises(ValueError):
            three([0.0] + SWEEP_CAS[1:], ROC_MEAS,
                  W_TEST, W_REF, H_P, OAT)


class ClimbCeilingTests(unittest.TestCase):
    """Workflow step 7 (reduce the Vy-schedule runs to the climb
    ceilings) exercised by the ceiling interpolation tests."""

    def test_ceiling_series_windows_reduce_to_the_measured_rates(self):
        """Step 7: the six Vy-schedule pressure-altitude windows reduce
        to the measured rates 6.376000 down to 0.410000 m/s (each within
        1e-3) with the r_squared fit quality in [0.968, 1.0]."""
        for window, expected in zip(CEILING_WINDOWS, CEILING_ROC_MEAS):
            result = rfc.roc_from_altitude_samples(window, TIME_S)
            self.assertAlmostEqual(result["roc_mps"], expected, delta=1e-3)
            self.assertGreaterEqual(result["r_squared"], 0.968)
            self.assertLessEqual(result["r_squared"], 1.0)

    def test_ceiling_series_corrections_over_the_density_altitude_band(self):
        """Step 7: the corrected best-rate points across the density
        altitudes decay from 6.676074041 to 0.429868544 m/s (each within
        1e-3), bracketing the 0.5 m/s service-ceiling threshold."""
        for hp, oat, window, expected in zip(
                CEILING_PRESS_ALT, CEILING_OAT, CEILING_WINDOWS,
                CEILING_ROC_CORR):
            meas = rfc.roc_from_altitude_samples(window, TIME_S)["roc_mps"]
            sigma_test = rfc.pressure_altitude_sigma(hp, oat)
            sigma_ref = rfc.isa_sigma(hp)
            corr = rfc.corrected_roc(meas, W_TEST, W_REF,
                                     sigma_test, sigma_ref)
            self.assertAlmostEqual(corr, expected, delta=1e-3)

    def test_service_ceiling_of_the_worked_band(self):
        """Step 7: climb_ceilings on the worked density-altitude band
        interpolates the service ceiling at 6150.406816 m (within 1.0,
        the altitude where the corrected rate of climb decays to the
        0.5 m/s rotorcraft convention)."""
        result = rfc.climb_ceilings(CEILING_ROC_CORR, CEILING_DA)
        self.assertAlmostEqual(result["service_ceiling_m"],
                               6150.406816, delta=1.0)
        self.assertIsNone(result["absolute_ceiling_m"])

    def test_service_ceiling_none_when_the_band_stays_above_threshold(self):
        """Step 7: a corrected-rate series that stays above the 0.5 m/s
        threshold (3.0 to 2.5 m/s over 0-1000 m) returns None for the
        service ceiling and for the absolute ceiling."""
        result = rfc.climb_ceilings([3.0, 2.5], [0.0, 1000.0])
        self.assertIsNone(result["service_ceiling_m"])
        self.assertIsNone(result["absolute_ceiling_m"])

    def test_absolute_ceiling_zero_crossing_interpolation(self):
        """Step 7: a series that crosses zero inside the band
        interpolates the absolute ceiling at the zero crossing
        (666.67 m for 2.0 to -1.0 m/s over 0-1000 m) and the service
        ceiling at the 0.5 m/s crossing (500.0 m)."""
        result = rfc.climb_ceilings([2.0, -1.0], [0.0, 1000.0])
        self.assertAlmostEqual(result["service_ceiling_m"], 500.0, delta=1e-6)
        self.assertAlmostEqual(result["absolute_ceiling_m"],
                               666.666667, delta=1e-3)

    def test_ceiling_valueerrors_reject_malformed_bands(self):
        """Step 7: mismatched ROC and density-altitude lists, a single
        ceiling point, non-monotone density altitudes and a negative
        density altitude all raise ValueError."""
        with self.assertRaises(ValueError):
            rfc.climb_ceilings([6.0, 5.0, 4.0], [0.0, 1000.0])
        with self.assertRaises(ValueError):
            rfc.climb_ceilings([6.0], [0.0])
        with self.assertRaises(ValueError):
            rfc.climb_ceilings([6.0, 5.0], [1000.0, 0.0])
        with self.assertRaises(ValueError):
            rfc.climb_ceilings([6.0, 5.0], [-100.0, 1000.0])


class ConstantsTests(unittest.TestCase):
    """Module constants and pinning checks."""

    def test_module_constants_match_the_pinned_values(self):
        """The module constants match the pinned values: the ISA
        constants exactly, K_DELTA about 5.25588 (the
        G0/(R_AIR*LAPSE) ratio), K_SIGMA one less, KTAS_TO_MPS about
        0.514444 and the sweep and sample conventions."""
        self.assertEqual(rfc.T0, 288.15)
        self.assertEqual(rfc.LAPSE, 0.0065)
        self.assertEqual(rfc.G0, 9.80665)
        self.assertEqual(rfc.R_AIR, 287.053)
        self.assertEqual(rfc.TROPOPAUSE_M, 11000.0)
        self.assertAlmostEqual(rfc.K_DELTA, 5.25588, delta=1e-3)
        self.assertAlmostEqual(rfc.K_SIGMA, rfc.K_DELTA - 1.0, delta=1e-12)
        self.assertAlmostEqual(rfc.ALT_INV, 44330.77, delta=0.01)
        self.assertAlmostEqual(rfc.KTAS_TO_MPS, 0.514444, delta=1e-6)
        self.assertEqual(rfc.ROC_DENS_EXP, 0.5)
        self.assertEqual(rfc.SERVICE_ROC_MPS, 0.5)
        self.assertEqual(rfc.MIN_SAMPLES, 2)
        self.assertEqual(rfc.SWEEP_MIN, 4)
        self.assertEqual(rfc.SWEEP_MAX, 40)


if __name__ == "__main__":
    unittest.main()
