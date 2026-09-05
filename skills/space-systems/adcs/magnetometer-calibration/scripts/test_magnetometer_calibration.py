#!/usr/bin/env python3
"""Gate 3 contract test: magnetometer scalar-checking calibration.

Exercises scripts/magnetometer_calibration_logic.py (stdlib unittest,
offline, deterministic). Contract: docs/harness-contract.md gate 3 -
the magnetometer-calibration workflow of SKILL.md: step 1 collects the
in-flight magnetometer samples and the known field magnitudes, step 2
builds the scalar-checking design rows and right sides with
scalar_checking_design, step 3 forms the batch least squares normal
equations with least_squares_solve and solves them by the
partial-pivot Gaussian elimination of solve_linear_system (the
attitude-diversity gate), step 4 reads the bias estimate dict with
estimate_bias (bias vector, recovered bias norm, fourth unknown
expected squared norm, max fit residual), step 5 runs the consistency
check of the fourth unknown against the recovered bias norm, and step
6 cleans the raw samples with calibrate_measurement for the attitude
determination consumers. Invalid inputs raise ValueError. Worked
example: bias (200, -150, 300) nT over ten deterministic unit
directions with field magnitudes 30000 + 1500*k nT. Prep-verified
anchors: recovered bias 200.0, -150.0, 300.0 nT, bias norm 390.512484
nT, fourth unknown 152500 nT^2, sample-4 calibrated vector
19918.584287 nT per component, max calibrate error 3.8e-12 nT; the
module's real outputs are the assert targets within the spec bounds.
"""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import magnetometer_calibration_logic as mcl  # noqa: E402

# Worked example (spec): known bias (200, -150, 300) nT, ten unit
# directions, field magnitudes 30000 + 1500*k nT, noise-free.
S3 = math.sqrt(3.0)
S2 = math.sqrt(2.0)

UNIT_DIRECTIONS = [
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
    (1.0 / S3, 1.0 / S3, 1.0 / S3),
    (1.0 / S3, -1.0 / S3, 1.0 / S3),
    (-1.0 / S3, 1.0 / S3, 1.0 / S3),
    (1.0 / S3, 1.0 / S3, -1.0 / S3),
    (1.0 / S2, 0.0, 1.0 / S2),
    (0.6, 0.8, 0.0),
    (-1.0 / S2, 0.0, -1.0 / S2),
]

FIELD_MAGNITUDES = [30000.0 + 1500.0 * k for k in range(10)]
TRUE_BIAS = (200.0, -150.0, 300.0)
TRUE_BIAS_SQ = 152500.0
TRUE_BIAS_NORM = math.sqrt(TRUE_BIAS_SQ)


def synthetic_fixture(unit_directions, magnitudes, bias=TRUE_BIAS):
    """Noise-free fields h_k = B_k * u_k and samples m_k = h_k + bias."""
    fields = [tuple(B * u for u in unit) for unit, B in
              zip(unit_directions, magnitudes)]
    measurements = [tuple(h + b for h, b in zip(h_k, bias))
                    for h_k in fields]
    return fields, measurements


def rotate_vector(vector, angle_rad):
    """Fixed rotation about the y axis, used by the invariance check."""
    cosine = math.cos(angle_rad)
    sine = math.sin(angle_rad)
    x, y, z = vector
    return (cosine * x + sine * z, y, -sine * x + cosine * z)


def rotate_fixture(unit_directions, measurements, angle_rad):
    """Rotate every direction and sample about the y axis."""
    rotated_dirs = [rotate_vector(u, angle_rad) for u in unit_directions]
    rotated_meas = [rotate_vector(m, angle_rad) for m in measurements]
    return rotated_dirs, rotated_meas


FIELDS, MEASUREMENTS = synthetic_fixture(UNIT_DIRECTIONS,
                                         FIELD_MAGNITUDES)


class MagnetometerCalibrationWorkflowTests(unittest.TestCase):
    """Workflow steps 4 to 6 on the worked-example fixture."""

    def setUp(self):
        self.estimate = mcl.estimate_bias(MEASUREMENTS, FIELD_MAGNITUDES)

    def test_workflow_step4_recovers_known_bias_vector(self):
        """Step 4 of the SKILL.md workflow (read the estimate dict from
        estimate_bias) recovers the bias vector (200, -150, 300) nT
        within 1e-6 nT on the noise-free batch."""
        for recovered, known in zip(self.estimate["bias"], TRUE_BIAS):
            self.assertAlmostEqual(recovered, known, places=6)

    def test_bias_error_below_one_microtesla_identity_bound(self):
        """The scalar-checking identity bound of the spec (recovered
        bias error below 1e-6 nT) holds for the batch estimate."""
        error = math.sqrt(sum(
            (self.estimate["bias"][i] - TRUE_BIAS[i]) ** 2
            for i in range(3)))
        self.assertLess(error, 1e-6)

    def test_workflow_step4_recovered_bias_norm_matches_true(self):
        """The recovered bias norm 390.512484 nT from step 4 matches
        the true norm of the (200, -150, 300) nT bias within 1e-3."""
        self.assertAlmostEqual(self.estimate["bias_norm_nt"],
                               TRUE_BIAS_NORM, places=4)

    def test_fourth_unknown_matches_true_squared_norm(self):
        """The fourth unknown of the normal equations solution is the
        expected squared norm 152500 nT^2 of the known bias within
        1e-4 (spec bound)."""
        self.assertAlmostEqual(self.estimate["expected_sq_norm"],
                               TRUE_BIAS_SQ, places=4)

    def test_workflow_step5_consistency_gap_below_tolerance(self):
        """Step 5 of the SKILL.md workflow (the consistency check of
        the fourth unknown against the recovered bias norm) closes the
        gap below 1e-3 nT^2."""
        gap = abs(self.estimate["expected_sq_norm"]
                  - self.estimate["bias_norm_nt"] ** 2)
        self.assertLess(gap, 1e-3)

    def test_workflow_step5_max_residual_below_tolerance(self):
        """Step 5 of the SKILL.md workflow (the fit residual gate)
        keeps the max residual below 1e-3 nT^2 on the noise-free
        batch."""
        self.assertLess(self.estimate["max_residual"], 1e-3)

    def test_workflow_step6_calibrate_recovers_true_fields(self):
        """Step 6 of the SKILL.md workflow (clean the samples with
        calibrate_measurement) reproduces the true field vectors on
        all ten samples within 1e-6 nT."""
        for measurement, field in zip(MEASUREMENTS, FIELDS):
            cleaned = mcl.calibrate_measurement(measurement,
                                                self.estimate["bias"])
            for cleaned_i, true_i in zip(cleaned, field):
                self.assertAlmostEqual(cleaned_i, true_i, places=6)

    def test_calibrate_anchor_sample_four_matches_prep(self):
        """Sample 4 of the fixture (the first body diagonal at 34500
        nT) calibrates to 19918.584287 nT per component, the prep
        anchor of the worked example, within 1e-3."""
        cleaned = mcl.calibrate_measurement(MEASUREMENTS[3],
                                            self.estimate["bias"])
        for cleaned_i in cleaned:
            self.assertAlmostEqual(cleaned_i, 19918.584287, places=4)

    def test_max_calibrate_error_over_all_samples_below_tolerance(self):
        """The max calibrate error over all ten cleaned samples stays
        below 1e-6 nT, the identity bound of the spec."""
        worst = 0.0
        for measurement, field in zip(MEASUREMENTS, FIELDS):
            cleaned = mcl.calibrate_measurement(measurement,
                                                self.estimate["bias"])
            worst = max(worst, max(abs(c - t)
                                   for c, t in zip(cleaned, field)))
        self.assertLess(worst, 1e-6)

    def test_rotation_invariance_of_the_bias_estimate(self):
        """The bias estimate is invariant under a fixed rotation of the
        fixture: the rotated batch recovers the rotated known bias
        within 1e-6 nT with the same norm."""
        angle = math.radians(30.0)
        rotated_dirs, rotated_meas = rotate_fixture(
            UNIT_DIRECTIONS, MEASUREMENTS, angle)
        rotated_fields, _ = synthetic_fixture(rotated_dirs,
                                              FIELD_MAGNITUDES)
        rotated_bias = tuple(rotate_vector(v, angle)
                             for v in [TRUE_BIAS])[0]
        estimate = mcl.estimate_bias(rotated_meas, FIELD_MAGNITUDES)
        for recovered, known in zip(estimate["bias"], rotated_bias):
            self.assertAlmostEqual(recovered, known, places=6)
        self.assertAlmostEqual(estimate["bias_norm_nt"],
                               TRUE_BIAS_NORM, places=4)
        self.assertLess(estimate["max_residual"], 1e-3)
        for measurement, field in zip(rotated_meas, rotated_fields):
            cleaned = mcl.calibrate_measurement(measurement,
                                                estimate["bias"])
            for cleaned_i, true_i in zip(cleaned, field):
                self.assertAlmostEqual(cleaned_i, true_i, places=6)

    def test_estimate_bias_dict_keys_exactly_as_documented(self):
        """The estimate dict exposes exactly the documented keys bias,
        bias_norm_nt, expected_sq_norm, max_residual."""
        self.assertEqual(set(self.estimate.keys()),
                         {"bias", "bias_norm_nt", "expected_sq_norm",
                          "max_residual"})

    def test_bias_entry_is_a_three_tuple(self):
        """The bias entry of the estimate dict is a 3-tuple of floats."""
        self.assertEqual(len(self.estimate["bias"]), 3)
        for component in self.estimate["bias"]:
            self.assertIsInstance(component, float)

    def test_determinism_repeated_calls_identical(self):
        """Identical inputs give identical estimates on every call:
        repeated estimate_bias runs return equal dicts and floats."""
        first = mcl.estimate_bias(MEASUREMENTS, FIELD_MAGNITUDES)
        second = mcl.estimate_bias(MEASUREMENTS, FIELD_MAGNITUDES)
        self.assertEqual(first, second)
        self.assertEqual(first["bias"], self.estimate["bias"])

    def test_four_measurements_are_enough_to_constrain(self):
        """Four diverse measurements, the workflow minimum of step 1,
        already constrain the 4 unknowns: the bias is recovered within
        1e-6 nT."""
        dirs = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0),
                (1.0 / S3, 1.0 / S3, 1.0 / S3)]
        magnitudes = [30000.0, 32000.0, 34000.0, 36000.0]
        _, measurements = synthetic_fixture(dirs, magnitudes)
        estimate = mcl.estimate_bias(measurements, magnitudes)
        error = math.sqrt(sum(
            (estimate["bias"][i] - TRUE_BIAS[i]) ** 2 for i in range(3)))
        self.assertLess(error, 1e-6)


class ScalarCheckingDesignTests(unittest.TestCase):
    """Workflow step 1 (batch assembly) and step 2 (design rows)."""

    def test_workflow_step2_design_rows_and_right_sides(self):
        """Step 2 of the SKILL.md workflow builds rows
        [-2*m_kx, -2*m_ky, -2*m_kz, 1] and right sides
        B_k^2 - |m_k|^2, checked here against hand-computed values on
        a four-sample scalar-checking fixture."""
        measurements = [(1000.0, 2000.0, 3000.0), (0.0, 0.0, 5000.0),
                        (100.0, 200.0, 300.0), (4000.0, 3000.0, 2000.0)]
        magnitudes = [30000.0, 35000.0, 25000.0, 40000.0]
        rows, right = mcl.scalar_checking_design(measurements, magnitudes)
        self.assertEqual(rows[0], [-2000.0, -4000.0, -6000.0, 1.0])
        self.assertEqual(rows[1], [0.0, 0.0, -10000.0, 1.0])
        self.assertEqual(rows[3], [-8000.0, -6000.0, -4000.0, 1.0])
        self.assertEqual(right[0],
                         30000.0 ** 2 - (1000.0 ** 2 + 2000.0 ** 2
                                         + 3000.0 ** 2))
        self.assertEqual(right[1], 35000.0 ** 2 - 5000.0 ** 2)
        self.assertEqual(right[2], 25000.0 ** 2 - (100.0 ** 2
                                                   + 200.0 ** 2
                                                   + 300.0 ** 2))

    def test_workflow_step1_rejects_length_mismatch(self):
        """Step 1 of the SKILL.md workflow rejects a length mismatch
        between the sample list and the field magnitude list."""
        with self.assertRaisesRegex(ValueError, "equal length"):
            mcl.scalar_checking_design(MEASUREMENTS[:5],
                                       FIELD_MAGNITUDES)

    def test_workflow_step1_rejects_fewer_than_four_samples(self):
        """Step 1 of the SKILL.md workflow rejects fewer than 4
        measurements: three samples cannot constrain 4 unknowns."""
        with self.assertRaisesRegex(
                ValueError,
                "fewer than 4 measurements cannot constrain 4 unknowns"):
            mcl.scalar_checking_design(MEASUREMENTS[:3],
                                       FIELD_MAGNITUDES[:3])

    def test_workflow_step1_rejects_zero_field_magnitude(self):
        """Step 1 of the SKILL.md workflow rejects a zero field
        magnitude as non-physical."""
        magnitudes = list(FIELD_MAGNITUDES)
        magnitudes[0] = 0.0
        with self.assertRaisesRegex(ValueError, "positive"):
            mcl.scalar_checking_design(MEASUREMENTS, magnitudes)

    def test_workflow_step1_rejects_negative_field_magnitude(self):
        """Step 1 of the SKILL.md workflow rejects a negative field
        magnitude as non-physical."""
        magnitudes = list(FIELD_MAGNITUDES)
        magnitudes[5] = -100.0
        with self.assertRaisesRegex(ValueError, "positive"):
            mcl.scalar_checking_design(MEASUREMENTS, magnitudes)

    def test_design_rejects_non_three_vector_sample(self):
        """A sample that is not a 3-vector breaks the scalar-checking
        geometry and is rejected."""
        with self.assertRaisesRegex(ValueError, "3-vector"):
            mcl.scalar_checking_design([(1.0, 2.0)] + MEASUREMENTS[1:],
                                       FIELD_MAGNITUDES)

    def test_design_of_estimate_passes_errors_through(self):
        """estimate_bias passes the step 1 validation through: a length
        mismatch raises ValueError from the same gate."""
        with self.assertRaisesRegex(ValueError, "equal length"):
            mcl.estimate_bias(MEASUREMENTS, FIELD_MAGNITUDES[:-1])

    def test_estimate_with_three_samples_raises(self):
        """estimate_bias with three samples raises the step 1 count
        ValueError."""
        with self.assertRaisesRegex(
                ValueError,
                "fewer than 4 measurements cannot constrain 4 unknowns"):
            mcl.estimate_bias(MEASUREMENTS[:3], FIELD_MAGNITUDES[:3])


class LinearSolverAndDiversityGateTests(unittest.TestCase):
    """Workflow step 3: the partial-pivot solver and the
    attitude-diversity gate on the normal equations."""

    def test_solver_two_unknown_system(self):
        """solve_linear_system, the small Gaussian elimination of step
        3, solves the 2 by 2 system 2x + y = 5, x + 3y = 7."""
        unknowns = mcl.solve_linear_system([[2.0, 1.0], [1.0, 3.0]],
                                           [5.0, 7.0])
        self.assertAlmostEqual(unknowns[0], 1.6, places=12)
        self.assertAlmostEqual(unknowns[1], 1.8, places=12)

    def test_solver_three_unknown_system(self):
        """solve_linear_system solves a 3 by 3 diagonal-dominant system
        exactly within float precision."""
        matrix = [[3.0, 1.0, 0.0], [1.0, 4.0, 1.0], [0.0, 1.0, 2.0]]
        # Vector chosen as A * [2, 1, 2] so the solution is known.
        vector = [7.0, 8.0, 5.0]
        unknowns = mcl.solve_linear_system(matrix, vector)
        for unknown, expected in zip(unknowns, [2.0, 1.0, 2.0]):
            self.assertAlmostEqual(unknown, expected, places=12)

    def test_solver_identity_matrix(self):
        """solve_linear_system on the identity returns the right side
        unchanged."""
        unknowns = mcl.solve_linear_system(
            [[1.0, 0.0, 0.0, 0.0], [0.0, 1.0, 0.0, 0.0],
             [0.0, 0.0, 1.0, 0.0], [0.0, 0.0, 0.0, 1.0]],
            [1.0, 2.0, 3.0, 4.0])
        self.assertEqual(unknowns, [1.0, 2.0, 3.0, 4.0])

    def test_solver_singular_matrix_raises_diversity(self):
        """A singular coefficient matrix trips the pivot floor of step
        3 and raises the insufficient attitude diversity ValueError."""
        with self.assertRaisesRegex(ValueError,
                                    "insufficient attitude diversity"):
            mcl.solve_linear_system([[1.0, 2.0], [2.0, 4.0]],
                                    [1.0, 2.0])

    def test_collinear_fixture_raises_diversity_gate(self):
        """Measurements confined to one line (all samples along the x
        axis with the bias attached) make the normal equations rank
        deficient, so step 3 raises the insufficient attitude
        diversity ValueError."""
        dirs = [(1.0, 0.0, 0.0)] * 6
        magnitudes = [30000.0 + 1500.0 * k for k in range(6)]
        _, measurements = synthetic_fixture(dirs, magnitudes)
        with self.assertRaisesRegex(ValueError,
                                    "insufficient attitude diversity"):
            mcl.estimate_bias(measurements, magnitudes)

    def test_planar_fixture_raises_diversity_gate(self):
        """Directions confined to one plane (zero-rank geometry) also
        trip the attitude-diversity gate of step 3."""
        dirs = [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0),
                (1.0 / S2, 1.0 / S2, 0.0), (-1.0 / S2, 1.0 / S2, 0.0),
                (1.0 / S2, -1.0 / S2, 0.0)]
        magnitudes = [30000.0 + 1500.0 * k for k in range(5)]
        _, measurements = synthetic_fixture(dirs, magnitudes)
        with self.assertRaisesRegex(ValueError,
                                    "insufficient attitude diversity"):
            mcl.estimate_bias(measurements, magnitudes)

    def test_least_squares_solve_exact_consistent_system(self):
        """least_squares_solve of step 3 recovers the exact unknowns of
        a consistent overdetermined system: rows [[1,2],[3,4],[5,6]]
        with right side A x_true for x_true = [7, -2]."""
        rows = [[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]
        right = [3.0, 13.0, 23.0]
        unknowns = mcl.least_squares_solve(rows, right)
        self.assertAlmostEqual(unknowns[0], 7.0, places=10)
        self.assertAlmostEqual(unknowns[1], -2.0, places=10)

    def test_least_squares_solve_returns_four_unknowns(self):
        """On the worked-example scalar-checking rows the step 3
        normal equations return exactly 4 unknowns."""
        rows, right = mcl.scalar_checking_design(MEASUREMENTS,
                                                 FIELD_MAGNITUDES)
        unknowns = mcl.least_squares_solve(rows, right)
        self.assertEqual(len(unknowns), 4)

    def test_residual_norm_exact_zero_and_identity_tolerance(self):
        """residual_norm reports exactly zero when the unknowns close
        the rows by hand (identity rows with right side [3, 7] and
        unknowns [3, 7]), and stays below the 1e-3 nT^2 fit tolerance
        of the workflow when the scalar-checking rows are closed with
        the true bias unknowns."""
        rows = [[1.0, 0.0], [0.0, 1.0]]
        right = [3.0, 7.0]
        unknowns = [3.0, 7.0]
        self.assertEqual(mcl.residual_norm(rows, right, unknowns), 0.0)
        design_rows, design_right = mcl.scalar_checking_design(
            MEASUREMENTS, FIELD_MAGNITUDES)
        identity_unknowns = list(TRUE_BIAS) + [TRUE_BIAS_SQ]
        self.assertLess(mcl.residual_norm(design_rows, design_right,
                                          identity_unknowns), 1e-3)


class CalibrateMeasurementTests(unittest.TestCase):
    """Workflow step 6: bias subtraction on the cleaned samples."""

    def test_calibrate_length_mismatch_raises(self):
        """calibrate_measurement rejects a measurement and bias vector
        of different lengths."""
        with self.assertRaisesRegex(ValueError, "equal length"):
            mcl.calibrate_measurement((1.0, 2.0, 3.0), (1.0, 2.0))

    def test_calibrate_subtracts_elementwise(self):
        """calibrate_measurement subtracts the bias componentwise: a
        hand sample minus the known bias returns the clean vector."""
        sample = (30100.0, 29850.0, 30300.0)
        cleaned = mcl.calibrate_measurement(sample, TRUE_BIAS)
        self.assertEqual(cleaned, (29900.0, 30000.0, 30000.0))

    def test_calibrate_returns_tuple(self):
        """calibrate_measurement returns a tuple of floats ready for
        the attitude consumers."""
        bias = mcl.estimate_bias(MEASUREMENTS, FIELD_MAGNITUDES)["bias"]
        cleaned = mcl.calibrate_measurement(MEASUREMENTS[0], bias)
        self.assertIsInstance(cleaned, tuple)
        self.assertEqual(len(cleaned), 3)

    def test_calibrate_with_zero_bias_is_identity(self):
        """A zero bias leaves the measurement unchanged, the trivial
        end of the calibration workflow."""
        sample = (1.0, -2.0, 3.0)
        self.assertEqual(mcl.calibrate_measurement(sample, (0.0, 0.0,
                                                            0.0)), sample)


if __name__ == "__main__":
    unittest.main()
