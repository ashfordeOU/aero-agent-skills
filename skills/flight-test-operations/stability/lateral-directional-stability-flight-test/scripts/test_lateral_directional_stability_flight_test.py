"""Offline contract test for the lateral-directional stability flight test leaf.

Deterministic, stdlib unittest only, no network, no RNG.  Run from the leaf
scripts directory or repo root:

    python3 scripts/test_lateral_directional_stability_flight_test.py

Covers: the spec worked example (module real outputs as assert targets
within the spec magnitude bounds), the exact LSQ gradients through the
five worked points, sign logic and verdict threshold edges, ValueError
rejections for every non-physical input, matrix row keys, the documented
convenience dict keys, None fields for optional inputs, determinism, and
the module constant conventions.
"""

import unittest

from lateral_directional_stability_flight_test_logic import (
    BETA_SWEEP_MIN,
    SIDESLIP_LIMIT_DEG,
    aileron_gradient,
    build_sideslip_matrix,
    dihedral_verdict,
    fit_slope,
    pedal_force_gradient,
    reduce_sideslip_sweep,
    rudder_gradient,
    signed_directional_estimate,
    signed_lateral_estimate,
    weathercock_verdict,
)

# Spec worked example: stable transport at CAS 80 m/s, 3000 m.
BETA_DEG = [2.0, 5.0, 8.0, 11.0, 14.0]
DELTA_R_DEG = [0.24, 0.58, 0.96, 1.34, 1.70]
DELTA_A_DEG = [-0.35, -0.80, -1.30, -1.80, -2.30]
PEDAL_FORCE_N = [0.0, -95.0, -185.0, -275.0, -360.0]
CN_DR_PER_RAD = -0.90
CL_DA_PER_RAD = -0.35


class TestWorkedExampleGradients(unittest.TestCase):
    """Worked sweep gradients: real outputs exact, within spec bounds."""

    def test_rudder_gradient_positive_within_bounds(self):
        slope = rudder_gradient(BETA_DEG, DELTA_R_DEG)
        self.assertAlmostEqual(slope, 0.1226667, places=6)
        self.assertGreater(slope, 0.0)
        self.assertGreaterEqual(slope, 0.10)
        self.assertLessEqual(slope, 0.15)

    def test_aileron_gradient_negative_within_bounds(self):
        slope = aileron_gradient(BETA_DEG, DELTA_A_DEG)
        self.assertAlmostEqual(slope, -0.1633333, places=6)
        self.assertLess(slope, 0.0)
        self.assertGreaterEqual(slope, -0.20)
        self.assertLessEqual(slope, -0.12)

    def test_pedal_force_gradient_within_bounds(self):
        slope = pedal_force_gradient(BETA_DEG, PEDAL_FORCE_N)
        self.assertAlmostEqual(slope, -30.0, places=6)
        self.assertGreaterEqual(slope, -40.0)
        self.assertLessEqual(slope, -20.0)

    def test_gradient_ratios_deg_per_deg_are_unitless(self):
        # A 1 deg rudder change per 1 deg of slip is slope 1.0 exactly.
        self.assertAlmostEqual(
            rudder_gradient([0.0, 5.0, 10.0], [0.0, 5.0, 10.0]), 1.0, places=10
        )


class TestWorkedExampleEstimates(unittest.TestCase):
    """Signed estimates and verdicts from the worked sweep."""

    def test_cn_beta_estimate_within_bounds(self):
        est = signed_directional_estimate(CN_DR_PER_RAD, 0.1226667)
        self.assertAlmostEqual(est, 0.1104, places=6)
        self.assertGreater(est, 0.0)
        self.assertGreaterEqual(est, 0.08)
        self.assertLessEqual(est, 0.15)

    def test_cl_beta_estimate_within_bounds(self):
        est = signed_lateral_estimate(CL_DA_PER_RAD, -0.1633333)
        self.assertAlmostEqual(est, -0.0571667, places=6)
        self.assertLess(est, 0.0)
        self.assertGreaterEqual(est, -0.10)
        self.assertLessEqual(est, -0.03)

    def test_worked_verdicts_stable(self):
        self.assertEqual(weathercock_verdict(0.1104), "stable")
        self.assertEqual(dihedral_verdict(-0.0571667), "stable")

    def test_reduce_sweep_worked_case_end_to_end(self):
        out = reduce_sideslip_sweep(
            BETA_DEG,
            DELTA_R_DEG,
            DELTA_A_DEG,
            pedal_force_N=PEDAL_FORCE_N,
            cn_dr_per_rad=CN_DR_PER_RAD,
            cl_da_per_rad=CL_DA_PER_RAD,
        )
        self.assertAlmostEqual(out["rudder_gradient_per_deg"], 0.1226667, places=6)
        self.assertAlmostEqual(out["aileron_gradient_per_deg"], -0.1633333, places=6)
        self.assertAlmostEqual(out["pedal_force_gradient_N_per_deg"], -30.0, places=6)
        self.assertAlmostEqual(out["cn_beta_estimate_per_rad"], 0.1104, places=6)
        self.assertAlmostEqual(out["cl_beta_estimate_per_rad"], -0.0571667, places=6)
        self.assertEqual(out["weathercock_verdict"], "stable")
        self.assertEqual(out["dihedral_verdict"], "stable")
        self.assertEqual(out["point_count"], 5)


class TestSignLogicAndVerdicts(unittest.TestCase):
    """Stable signs, reverse signs and threshold edges per the convention."""

    def test_stable_signs_from_signed_formulas(self):
        # cn_dr < 0 with a positive rudder slope gives positive Cn_beta.
        self.assertGreater(signed_directional_estimate(-0.90, 0.12), 0.0)
        # cl_da < 0 with a negative aileron slope gives negative Cl_beta.
        self.assertLess(signed_lateral_estimate(-0.35, -0.16), 0.0)

    def test_negative_rudder_slope_yields_unstable_weathercock(self):
        # Reverse-control sweep: rudder deflection decreases as slip grows.
        decreasing = [1.70, 1.34, 0.96, 0.58, 0.24]
        slope = rudder_gradient(BETA_DEG, decreasing)
        self.assertLess(slope, 0.0)
        est = signed_directional_estimate(CN_DR_PER_RAD, slope)
        self.assertLess(est, 0.0)
        self.assertEqual(weathercock_verdict(est), "unstable")

    def test_positive_aileron_slope_yields_unstable_dihedral(self):
        # Reverse-control sweep: aileron deflection grows with the slip.
        increasing = [-2.30, -1.80, -1.30, -0.80, -0.35]
        slope = aileron_gradient(BETA_DEG, increasing)
        self.assertGreater(slope, 0.0)
        est = signed_lateral_estimate(CL_DA_PER_RAD, slope)
        self.assertGreater(est, 0.0)
        self.assertEqual(dihedral_verdict(est), "unstable")

    def test_weathercock_verdict_signs_and_zero_edge(self):
        self.assertEqual(weathercock_verdict(0.001), "stable")
        self.assertEqual(weathercock_verdict(-0.001), "unstable")
        self.assertEqual(weathercock_verdict(0.0), "unstable")

    def test_dihedral_verdict_signs_and_zero_edge(self):
        self.assertEqual(dihedral_verdict(-0.001), "stable")
        self.assertEqual(dihedral_verdict(0.001), "unstable")
        self.assertEqual(dihedral_verdict(0.0), "unstable")


class TestFitSlope(unittest.TestCase):
    """Two-parameter least squares core."""

    def test_fit_slope_perfect_line(self):
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        ys = [1.0, 3.0, 5.0, 7.0, 9.0]
        self.assertAlmostEqual(fit_slope(xs, ys), 2.0, places=10)

    def test_fit_slope_offset_invariant(self):
        xs = [0.0, 1.0, 2.0, 3.0, 4.0]
        base = [1.0, 3.0, 5.0, 7.0, 9.0]
        shifted = [v + 100.0 for v in base]
        self.assertAlmostEqual(fit_slope(xs, base), fit_slope(xs, shifted), places=10)

    def test_fit_slope_two_points_exact_and_min_constant(self):
        self.assertAlmostEqual(fit_slope([2.0, 8.0], [0.24, 0.96]), 0.12, places=10)
        self.assertEqual(BETA_SWEEP_MIN, 2)

    def test_fit_slope_length_mismatch_raises(self):
        with self.assertRaises(ValueError):
            fit_slope([1.0, 2.0, 3.0], [1.0, 2.0])

    def test_fit_slope_too_few_points_raises(self):
        with self.assertRaises(ValueError):
            fit_slope([3.0], [1.0])
        with self.assertRaises(ValueError):
            fit_slope([], [])

    def test_fit_slope_zero_x_variance_raises(self):
        with self.assertRaises(ValueError):
            fit_slope([5.0, 5.0, 5.0], [1.0, 2.0, 3.0])

    def test_gradient_wrappers_delegate_to_fit_slope(self):
        self.assertAlmostEqual(
            rudder_gradient(BETA_DEG, DELTA_R_DEG),
            fit_slope(BETA_DEG, DELTA_R_DEG),
            places=12,
        )
        self.assertAlmostEqual(
            aileron_gradient(BETA_DEG, DELTA_A_DEG),
            fit_slope(BETA_DEG, DELTA_A_DEG),
            places=12,
        )
        self.assertAlmostEqual(
            pedal_force_gradient(BETA_DEG, PEDAL_FORCE_N),
            fit_slope(BETA_DEG, PEDAL_FORCE_N),
            places=12,
        )


class TestSignedEstimateValidators(unittest.TestCase):
    """Control power bookkeeping and zero rejections."""

    def test_signed_directional_estimate_exact_formula(self):
        self.assertAlmostEqual(signed_directional_estimate(-0.50, 0.20), 0.10, places=10)

    def test_signed_lateral_estimate_exact_formula(self):
        self.assertAlmostEqual(signed_lateral_estimate(-0.25, -0.40), -0.10, places=10)

    def test_zero_cn_dr_raises(self):
        with self.assertRaises(ValueError):
            signed_directional_estimate(0.0, 0.12)

    def test_zero_cl_da_raises(self):
        with self.assertRaises(ValueError):
            signed_lateral_estimate(0.0, -0.16)


class TestSideslipMatrix(unittest.TestCase):
    """Sweep matrix rows and declared limit enforcement."""

    def test_build_matrix_rows_and_keys(self):
        rows = build_sideslip_matrix([0.0, 5.0, 10.0], 80.0, 3000.0)
        self.assertEqual(len(rows), 3)
        for row, target in zip(rows, [0.0, 5.0, 10.0]):
            self.assertEqual(sorted(row.keys()), ["altitude_m", "beta_target_deg", "cas_ms"])
            self.assertEqual(row["beta_target_deg"], target)
            self.assertEqual(row["cas_ms"], 80.0)
            self.assertEqual(row["altitude_m"], 3000.0)

    def test_build_matrix_edges_within_declared_limit(self):
        rows = build_sideslip_matrix([-15.0, 15.0], 80.0, 3000.0)
        self.assertEqual([r["beta_target_deg"] for r in rows], [-15.0, 15.0])
        self.assertEqual(SIDESLIP_LIMIT_DEG, 15.0)

    def test_build_matrix_target_beyond_limit_raises(self):
        with self.assertRaises(ValueError):
            build_sideslip_matrix([0.0, 20.0], 80.0, 3000.0)

    def test_build_matrix_target_below_negative_limit_raises(self):
        with self.assertRaises(ValueError):
            build_sideslip_matrix([-16.0], 80.0, 3000.0)

    def test_build_matrix_nonpositive_cas_raises(self):
        with self.assertRaises(ValueError):
            build_sideslip_matrix([0.0], 0.0, 3000.0)
        with self.assertRaises(ValueError):
            build_sideslip_matrix([0.0], -5.0, 3000.0)


class TestReduceSweepContract(unittest.TestCase):
    """Convenience dict contract and determinism."""

    DOC_KEYS = {
        "rudder_gradient_per_deg",
        "aileron_gradient_per_deg",
        "pedal_force_gradient_N_per_deg",
        "cn_beta_estimate_per_rad",
        "cl_beta_estimate_per_rad",
        "weathercock_verdict",
        "dihedral_verdict",
        "point_count",
    }

    def test_reduce_sweep_contains_exactly_documented_keys(self):
        out = reduce_sideslip_sweep(BETA_DEG, DELTA_R_DEG, DELTA_A_DEG)
        self.assertEqual(set(out.keys()), self.DOC_KEYS)

    def test_reduce_sweep_none_fields_without_optional_inputs(self):
        out = reduce_sideslip_sweep(BETA_DEG, DELTA_R_DEG, DELTA_A_DEG)
        self.assertIsNone(out["pedal_force_gradient_N_per_deg"])
        self.assertIsNone(out["cn_beta_estimate_per_rad"])
        self.assertIsNone(out["cl_beta_estimate_per_rad"])
        self.assertIsNone(out["weathercock_verdict"])
        self.assertIsNone(out["dihedral_verdict"])
        self.assertEqual(out["point_count"], 5)

    def test_reduce_sweep_partial_optional_population(self):
        with_cn = reduce_sideslip_sweep(
            BETA_DEG, DELTA_R_DEG, DELTA_A_DEG, cn_dr_per_rad=CN_DR_PER_RAD
        )
        self.assertIsNotNone(with_cn["cn_beta_estimate_per_rad"])
        self.assertEqual(with_cn["weathercock_verdict"], "stable")
        self.assertIsNone(with_cn["cl_beta_estimate_per_rad"])
        self.assertIsNone(with_cn["dihedral_verdict"])
        with_pedal = reduce_sideslip_sweep(
            BETA_DEG, DELTA_R_DEG, DELTA_A_DEG, pedal_force_N=PEDAL_FORCE_N
        )
        self.assertAlmostEqual(with_pedal["pedal_force_gradient_N_per_deg"], -30.0, places=6)

    def test_reduce_sweep_propagates_value_errors(self):
        with self.assertRaises(ValueError):
            reduce_sideslip_sweep([1.0, 2.0], [1.0], DELTA_A_DEG)
        with self.assertRaises(ValueError):
            reduce_sideslip_sweep(BETA_DEG, DELTA_R_DEG, DELTA_A_DEG, cn_dr_per_rad=0.0)
        with self.assertRaises(ValueError):
            reduce_sideslip_sweep(BETA_DEG, DELTA_R_DEG, DELTA_A_DEG, cl_da_per_rad=0.0)

    def test_determinism_run_to_run_identical_floats(self):
        def run():
            return reduce_sideslip_sweep(
                BETA_DEG,
                DELTA_R_DEG,
                DELTA_A_DEG,
                pedal_force_N=PEDAL_FORCE_N,
                cn_dr_per_rad=CN_DR_PER_RAD,
                cl_da_per_rad=CL_DA_PER_RAD,
            )

        first = run()
        second = run()
        for key in first:
            self.assertEqual(first[key], second[key])


if __name__ == "__main__":
    unittest.main()
