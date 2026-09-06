"""Contract test for imu-static-calibration (gnc-autonomy,
estimation-filtering): exercises workflow steps 1-6 of the SKILL.md
body. Step 1 (record the six-position-test static-hold campaign) and
step 4 (collect the rate-table-calibration runs) are exercised by the
simulation tests; step 2 (run the pair reduction to the
accelerometer-bias-scale pair closed form) by the fit_accel_pair tests;
step 3 (fit the misalignment matrix by least squares over all six
positions) by the fit_accel_ls tests; step 5 (regress the gyro axes to
the gyro-bias-scale factors) by the fit_gyro tests; step 6 (read off
the residual fit errors of both reductions) by the residual-assertion
tests. Deterministic offline unittest, no network, no third-party
imports, runs in well under 20 seconds."""

import inspect
import re
import unittest

import imu_static_calibration_logic as imucal

G0 = imucal.G0
POSITIONS = imucal.POSITIONS

# Worked-example injected truth (from the wave-43 spec): accelerometer
# bias in m/s^2, scale factors, off-diagonal misalignment truth, gyro
# bias in deg/s, gyro scale factors, noise sigmas and seeds.
B_TRUE = (0.0120, -0.0080, 0.0200)
S_TRUE = (1.0020, 0.9980, 1.0010)
MIS_TRUE = ((0.0, 0.0012, -0.0009), (0.0015, 0.0, 0.0006),
            (-0.0011, 0.0008, 0.0))
G_B_TRUE = (0.0500, -0.0300, 0.0200)
G_S_TRUE = (0.9985, 1.0010, 0.9995)
ACC_SIGMA = 5.0e-4
GY_SIGMA = 5.0e-3
ACC_SEED = 7
GY_SEED = 11
CMD = ((50, 30, 10, -10, -30, -50), (40, 25, 5, -5, -25, -40),
       (45, 20, 15, -15, -20, -45))

# Real outputs of the module on the worked example (verified equal to
# the spec anchors within 1e-5): the six hold means, the pair-fit and
# least-squares reductions, the measured rate runs and the gyro
# regression. Taken as assert targets inside the tolerances below.
HOLD_MEANS = (
    (9.83813536, 0.00696569, 0.00909964),
    (-9.81442083, -0.02317498, 0.03068066),
    (0.02432394, 9.77924877, 0.02836376),
    (0.00035647, -9.79483932, 0.01224734),
    (0.00234098, -0.00168839, 9.83670984),
    (0.02107539, -0.01472967, -9.79732859),
)
PAIR_BIAS = (0.01185726, -0.00779527, 0.01969062)
PAIR_SCALE = (1.00200151, 0.99800075, 1.00105737)
PAIR_RMS = 8.713e-3
LS_MATRIX = ((1.00200151, 0.00122200, -0.00095519),
             (0.00153675, 0.99800075, 0.00066492),
             (-0.00110033, 0.00082171, 1.00105737))
LS_BIAS = (0.01196855, -0.00803632, 0.01996211)
LS_RMS = 2.375e-4
MEASURED = ((49.96888, 30.00689, 10.03997, -9.93757, -29.91164, -49.87533),
            (40.01239, 25.00049, 4.96892, -5.04146, -25.05147, -40.06763),
            (45.00517, 20.01491, 15.01199, -14.97387, -19.95715, -44.95894))
GY_BIAS = (0.048534, -0.029794, 0.023685)
GY_SCALE = (0.998506, 1.001011, 0.999550)
GY_RMS = (0.004153, 0.004688, 0.005127)


def worked_means():
    """Shared fixture: the six noisy hold means of the worked example."""
    return imucal.simulate_six_position_means(
        B_TRUE, S_TRUE, MIS_TRUE, sigma=ACC_SIGMA, seed=ACC_SEED)


def worked_measured():
    """Shared fixture: the measured rate runs of the worked example."""
    return imucal.simulate_rate_table(CMD, G_B_TRUE, G_S_TRUE,
                                      sigma=GY_SIGMA, seed=GY_SEED)


class TestSimulateSixPosition(unittest.TestCase):
    """Workflow step 1: record the six-position-test static-hold
    campaign, the mean specific force with each body axis held up and
    down against the known plus/minus 1 g references."""

    def test_hold_means_match_worked_example(self):
        """The simulated six-position hold means reproduce the worked
        example (real module outputs) within 1e-5 m/s^2 on every
        channel, so the measurement model m_k = b + A*(f_k*G0) with the
        pinned fixture order +x, -x, +y, -y, +z, -z is exercised."""
        means = worked_means()
        for k in range(6):
            for c in range(3):
                self.assertAlmostEqual(means[k][c], HOLD_MEANS[k][c],
                                       delta=1e-5)

    def test_same_seed_bit_identical(self):
        """Two same-seed simulations of the six-position campaign
        return bit-identical hold mean tuples (deterministic seeded
        reduction)."""
        self.assertEqual(worked_means(), worked_means())

    def test_noise_free_equals_model(self):
        """At sigma = 0.0 the simulated hold means equal the explicit
        model b + A*(f_k*G0) channel by channel, with A the scale
        diagonal and the misalignment off-diagonals."""
        means = imucal.simulate_six_position_means(
            B_TRUE, S_TRUE, MIS_TRUE, sigma=0.0, seed=ACC_SEED)
        for k, fk in enumerate(POSITIONS):
            for c in range(3):
                expected = B_TRUE[c]
                for j in range(3):
                    a_cj = S_TRUE[c] if j == c else MIS_TRUE[c][j]
                    expected += a_cj * fk[j] * G0
                self.assertAlmostEqual(means[k][c], expected, delta=1e-12)

    def test_no_misalignment_defaults_to_diagonal(self):
        """Without a misalignment argument the simulated sensitivity
        matrix is exactly diagonal, so the cross-axis channels of a
        +x hold read only the bias."""
        means = imucal.simulate_six_position_means(
            (0.0, 0.0, 0.0), S_TRUE, sigma=0.0, seed=3)
        self.assertAlmostEqual(means[0][1], 0.0, delta=1e-12)
        self.assertAlmostEqual(means[0][2], 0.0, delta=1e-12)

    def test_simulate_valueerror_guards(self):
        """Non-physical campaign inputs raise ValueError: a non-finite
        or ill-sized bias, a non-positive scale factor, a non-finite
        or ill-shaped misalignment matrix, and a negative or non-finite
        noise sigma."""
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means((0.0, float("nan"), 0.0),
                                               S_TRUE, sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means((0.0, 0.0), S_TRUE,
                                               sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(B_TRUE, (1.0, 0.0, 1.0),
                                               sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(B_TRUE, (1.0, -1.0, 1.0),
                                               sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(
                B_TRUE, S_TRUE,
                ((0.0, float("inf"), 0.0), (0.0, 0.0, 0.0), (0.0, 0.0, 0.0)),
                sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(
                B_TRUE, S_TRUE, ((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)),
                sigma=0.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(B_TRUE, S_TRUE, sigma=-1.0)
        with self.assertRaises(ValueError):
            imucal.simulate_six_position_means(B_TRUE, S_TRUE,
                                               sigma=float("nan"))


class TestPairReduction(unittest.TestCase):
    """Workflow step 2: run the pair reduction, the per-axis
    accelerometer-bias-scale closed form s_i = (plus - minus)/(2*G0)
    and b_i = (plus + minus)/2 from the paired +g and -g holds."""

    def test_pair_bias_and_scale_match_worked_example(self):
        """The pair reduction on the worked-example means returns the
        real module bias (0.01185726, -0.00779527, 0.01969062) m/s^2
        and scale (1.00200151, 0.99800075, 1.00105737) within 1e-5."""
        fit = imucal.fit_accel_pair_bias_scale(worked_means())
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], PAIR_BIAS[i],
                                   delta=1e-5)
            self.assertAlmostEqual(fit["scale"][i], PAIR_SCALE[i],
                                   delta=1e-5)

    def test_pair_recovery_within_spec_verdict(self):
        """On the noisy campaign the recovered bias stays within 1e-3
        m/s^2 and the scale within 1e-3 of the injected truth."""
        fit = imucal.fit_accel_pair_bias_scale(worked_means())
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], B_TRUE[i], delta=1e-3)
            self.assertAlmostEqual(fit["scale"][i], S_TRUE[i], delta=1e-3)

    def test_pair_residual_rms_carries_cross_axis_leakage(self):
        """The diagonal pair model leaves the cross-axis leakage in the
        residual fit error: rms_residual sits at 8.713e-3 m/s^2 on the
        worked example (within 1e-3)."""
        fit = imucal.fit_accel_pair_bias_scale(worked_means())
        self.assertAlmostEqual(fit["rms_residual"], PAIR_RMS, delta=1e-3)

    def test_pair_noise_free_recovers_truth(self):
        """With sigma = 0.0 the pair reduction recovers the injected
        bias and scale exactly (within 1e-9), the noise-free anchor of
        the +/- 1 g pair algebra; the residual keeps only the
        cross-axis leakage the diagonal model cannot absorb."""
        means = imucal.simulate_six_position_means(
            B_TRUE, S_TRUE, MIS_TRUE, sigma=0.0, seed=ACC_SEED)
        fit = imucal.fit_accel_pair_bias_scale(means)
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], B_TRUE[i], delta=1e-9)
            self.assertAlmostEqual(fit["scale"][i], S_TRUE[i], delta=1e-9)
        self.assertAlmostEqual(fit["rms_residual"], 0.0, delta=1e-2)

    def test_pair_valueerror_means_guards(self):
        """Malformed hold means raise ValueError: five holds, rows
        wider than three channels, or a non-finite measured mean."""
        with self.assertRaises(ValueError):
            imucal.fit_accel_pair_bias_scale(list(worked_means())[:5])
        bad = [tuple(row) + (0.0,) for row in worked_means()]
        with self.assertRaises(ValueError):
            imucal.fit_accel_pair_bias_scale(bad)
        bad2 = [list(row) for row in worked_means()]
        bad2[0][0] = float("nan")
        with self.assertRaises(ValueError):
            imucal.fit_accel_pair_bias_scale(bad2)


class TestMisalignmentLeastSquares(unittest.TestCase):
    """Workflow step 3: fit the misalignment matrix by least squares
    over all six positions, the scale-plus-misalignment sensitivity
    matrix with the per-channel normal equations solved by Gaussian
    elimination with partial pivoting."""

    def test_ls_matrix_and_bias_match_worked_example(self):
        """The least-squares sensitivity matrix rows and bias vector
        reproduce the real module outputs of the worked example within
        1e-4 and 1e-5, with the scale factors on the diagonal and the
        misalignment terms off-diagonal."""
        fit = imucal.fit_accel_misalignment_ls(worked_means())
        for i in range(3):
            for j in range(3):
                self.assertAlmostEqual(fit["matrix"][i][j],
                                       LS_MATRIX[i][j], delta=1e-4)
            self.assertAlmostEqual(fit["bias"][i], LS_BIAS[i], delta=1e-5)

    def test_ls_residual_below_pair_residual(self):
        """The misalignment-aware least-squares residual rms sits at
        2.375e-4 m/s^2 (within 1e-4) and strictly below the diagonal
        pair residual, the cross-axis leakage the pairs model leaves
        behind."""
        ls = imucal.fit_accel_misalignment_ls(worked_means())
        pair = imucal.fit_accel_pair_bias_scale(worked_means())
        self.assertAlmostEqual(ls["rms_residual"], LS_RMS, delta=1e-4)
        self.assertLess(ls["rms_residual"], pair["rms_residual"])

    def test_ls_diagonal_equals_pair_scale(self):
        """The LS diagonal equals the pair scale within 1e-6 on the
        noisy worked example, because both reduce to the same +/- 1 g
        pair algebra over the orthogonal fixture."""
        ls = imucal.fit_accel_misalignment_ls(worked_means())
        pair = imucal.fit_accel_pair_bias_scale(worked_means())
        for i in range(3):
            self.assertAlmostEqual(ls["matrix"][i][i], pair["scale"][i],
                                   delta=1e-6)

    def test_ls_cross_axis_recovery_within_verdict(self):
        """Each recovered cross-axis sensitivity entry sits within 2e-4
        of the injected misalignment truth on the noisy campaign."""
        ls = imucal.fit_accel_misalignment_ls(worked_means())
        for i in range(3):
            for j in range(3):
                if i != j:
                    self.assertAlmostEqual(ls["matrix"][i][j],
                                           MIS_TRUE[i][j], delta=2e-4)

    def test_ls_noise_free_recovers_truth(self):
        """With sigma = 0.0 the least-squares fit recovers the injected
        bias, scale diagonal and cross-axis misalignment truth within
        1e-9, the LS diagonal equals the pair scale within 1e-9, and
        the residual rms vanishes exactly."""
        means = imucal.simulate_six_position_means(
            B_TRUE, S_TRUE, MIS_TRUE, sigma=0.0, seed=ACC_SEED)
        ls = imucal.fit_accel_misalignment_ls(means)
        pair = imucal.fit_accel_pair_bias_scale(means)
        for i in range(3):
            self.assertAlmostEqual(ls["bias"][i], B_TRUE[i], delta=1e-9)
            self.assertAlmostEqual(ls["matrix"][i][i], S_TRUE[i],
                                   delta=1e-9)
            self.assertAlmostEqual(ls["matrix"][i][i], pair["scale"][i],
                                   delta=1e-9)
            for j in range(3):
                if i != j:
                    self.assertAlmostEqual(ls["matrix"][i][j],
                                           MIS_TRUE[i][j], delta=1e-9)
        self.assertAlmostEqual(ls["rms_residual"], 0.0, delta=1e-9)

    def test_ls_valueerror_means_guards(self):
        """Five hold means or four-channel rows cannot feed the
        six-position least-squares fit and raise ValueError."""
        with self.assertRaises(ValueError):
            imucal.fit_accel_misalignment_ls(list(worked_means())[:5])
        bad = [tuple(row) + (0.0,) for row in worked_means()]
        with self.assertRaises(ValueError):
            imucal.fit_accel_misalignment_ls(bad)


class TestRateTableSimulation(unittest.TestCase):
    """Workflow step 4: collect the rate-table-calibration runs, the
    measured gyro rates at the commanded rotation rates of each body
    axis."""

    def test_measured_rates_match_worked_example(self):
        """The simulated rate-table runs reproduce the worked-example
        measured axis rates within 1e-4 deg/s on every commanded
        rate."""
        meas = worked_measured()
        for a in range(3):
            for i in range(6):
                self.assertAlmostEqual(meas[a][i], MEASURED[a][i],
                                       delta=1e-4)

    def test_rate_table_deterministic(self):
        """Two same-seed rate-table simulations return bit-identical
        measured rate tuples."""
        a = worked_measured()
        b = imucal.simulate_rate_table(CMD, G_B_TRUE, G_S_TRUE,
                                       sigma=GY_SIGMA, seed=GY_SEED)
        self.assertEqual(a, b)

    def test_noise_free_measured_equals_line(self):
        """At sigma = 0.0 each measured rate equals
        scale*commanded + bias exactly (within 1e-12 deg/s)."""
        meas = imucal.simulate_rate_table(CMD, G_B_TRUE, G_S_TRUE,
                                          sigma=0.0, seed=GY_SEED)
        for a in range(3):
            for i in range(6):
                self.assertAlmostEqual(meas[a][i],
                                       G_S_TRUE[a] * CMD[a][i] + G_B_TRUE[a],
                                       delta=1e-12)

    def test_rate_table_valueerror_guards(self):
        """Non-physical rate-table inputs raise ValueError: a single
        commanded rate on an axis, a non-positive gyro scale factor, a
        non-finite commanded rate, or a negative noise sigma."""
        with self.assertRaises(ValueError):
            imucal.simulate_rate_table(((50.0,), (40, 25), (45, 20)),
                                       G_B_TRUE, G_S_TRUE)
        with self.assertRaises(ValueError):
            imucal.simulate_rate_table(CMD, G_B_TRUE, (0.0, 1.0, 1.0))
        with self.assertRaises(ValueError):
            imucal.simulate_rate_table(((50, float("nan"), 10, -10),
                                        (40, 25), (45, 20)),
                                       G_B_TRUE, G_S_TRUE)
        with self.assertRaises(ValueError):
            imucal.simulate_rate_table(CMD, G_B_TRUE, G_S_TRUE, sigma=-1.0)


class TestGyroRegression(unittest.TestCase):
    """Workflow step 5: regress the gyro axes, the measured rates on
    the commanded rates to the per-axis gyro-bias intercept and scale
    slope with the per-axis residual fit errors."""

    def test_gyro_bias_and_scale_match_worked_example(self):
        """The gyro regression on the worked-example runs returns the
        real module bias (0.048534, -0.029794, 0.023685) deg/s within
        1e-4 and scale (0.998506, 1.001011, 0.999550) within 1e-5."""
        fit = imucal.fit_gyro_rate_table(worked_measured(), CMD)
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], GY_BIAS[i], delta=1e-4)
            self.assertAlmostEqual(fit["scale"][i], GY_SCALE[i],
                                   delta=1e-5)

    def test_gyro_recovery_within_spec_verdict(self):
        """On the noisy rate-table campaign the recovered gyro bias
        stays within 2e-2 deg/s and the scale within 5e-4 of the
        injected truth."""
        fit = imucal.fit_gyro_rate_table(worked_measured(), CMD)
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], G_B_TRUE[i],
                                   delta=2e-2)
            self.assertAlmostEqual(fit["scale"][i], G_S_TRUE[i],
                                   delta=5e-4)

    def test_gyro_residual_rms_at_injected_noise(self):
        """The per-axis residual rms (0.004153, 0.004688, 0.005127)
        deg/s sits within 2e-3 of the injected noise sigma 5e-3 deg/s,
        the expected regression scatter of the rate-table fit."""
        fit = imucal.fit_gyro_rate_table(worked_measured(), CMD)
        for i in range(3):
            self.assertAlmostEqual(fit["rms_per_axis"][i], GY_RMS[i],
                                   delta=2e-3)
            self.assertAlmostEqual(fit["rms_per_axis"][i], GY_SIGMA,
                                   delta=2e-3)

    def test_gyro_noise_free_recovers_truth(self):
        """With sigma = 0.0 the rate-table regression recovers the
        injected gyro bias and scale exactly (within 1e-9) with zero
        residual."""
        meas = imucal.simulate_rate_table(CMD, G_B_TRUE, G_S_TRUE,
                                          sigma=0.0, seed=GY_SEED)
        fit = imucal.fit_gyro_rate_table(meas, CMD)
        for i in range(3):
            self.assertAlmostEqual(fit["bias"][i], G_B_TRUE[i], delta=1e-9)
            self.assertAlmostEqual(fit["scale"][i], G_S_TRUE[i], delta=1e-9)
            self.assertAlmostEqual(fit["rms_per_axis"][i], 0.0, delta=1e-9)

    def test_gyro_valueerror_guards(self):
        """Malformed rate-table data raises ValueError: a single sample
        per axis, measured and commanded lists of unequal length, a
        constant commanded rate (singular regression through ols_fit),
        a non-finite measured rate, or data that does not cover three
        axes."""
        meas = worked_measured()
        with self.assertRaises(ValueError):
            imucal.fit_gyro_rate_table(((1.0,), (2.0, 3.0), (4.0, 5.0)),
                                       ((50.0,), (40.0, 25.0),
                                        (45.0, 20.0)))
        with self.assertRaises(ValueError):
            imucal.fit_gyro_rate_table(meas,
                                       (CMD[0][:5], CMD[1], CMD[2]))
        with self.assertRaises(ValueError):
            imucal.fit_gyro_rate_table(meas,
                                       ((50, 50, 50), CMD[1], CMD[2]))
        bad = [list(row) for row in meas]
        bad[0][0] = float("inf")
        with self.assertRaises(ValueError):
            imucal.fit_gyro_rate_table(bad, CMD)
        with self.assertRaises(ValueError):
            imucal.fit_gyro_rate_table(meas[:2], CMD[:2])


class TestOlsFitAndModule(unittest.TestCase):
    """Workflow steps 3, 5 and 6 support: the shared normal-equations
    solver and the module constants that pin the reduction."""

    def test_ols_fit_exact_line_recovery(self):
        """ols_fit on the design rows (x, 1) recovers the exact slope 3
        and intercept 2 of y = 3x + 2, the closed-form identity of the
        normal equations."""
        x = [1.0, 2.0, 3.0, 4.0]
        q = imucal.ols_fit([(xi, 1.0) for xi in x],
                           [5.0, 8.0, 11.0, 14.0])
        self.assertAlmostEqual(q[0], 3.0, delta=1e-9)
        self.assertAlmostEqual(q[1], 2.0, delta=1e-9)

    def test_ols_fit_diagonal_design(self):
        """ols_fit on an identity design matrix returns the response
        values as the coefficients."""
        q = imucal.ols_fit([(1.0, 0.0), (0.0, 1.0)], (2.0, 3.0))
        self.assertAlmostEqual(q[0], 2.0, delta=1e-12)
        self.assertAlmostEqual(q[1], 3.0, delta=1e-12)

    def test_ols_fit_valueerror_guards(self):
        """Malformed regressions raise ValueError: unequal design and
        response lengths, inconsistent row widths, a non-finite
        response, or a singular normal matrix."""
        with self.assertRaises(ValueError):
            imucal.ols_fit([(1.0, 2.0), (3.0, 4.0)], (1.0,))
        with self.assertRaises(ValueError):
            imucal.ols_fit([(1.0, 2.0), (3.0,)], (1.0, 2.0))
        with self.assertRaises(ValueError):
            imucal.ols_fit([(1.0,), (2.0,)], (1.0, float("nan")))
        with self.assertRaises(ValueError):
            imucal.ols_fit([(1.0, 1.0), (1.0, 1.0)], (2.0, 3.0))

    def test_module_imports_math_random_only(self):
        """The logic module imports only the stdlib math and random
        modules, keeping the reduction pure and offline."""
        source = inspect.getsource(imucal)
        imports = set(re.findall(r"^\s*(?:import|from)\s+(\w+)", source,
                                 re.MULTILINE))
        self.assertTrue(imports.issubset({"math", "random"}), imports)
        self.assertNotIn("numpy", source)
        self.assertNotIn("scipy", source)

    def test_module_constants_pinned(self):
        """G0 is pinned to 9.80665 m/s^2 and the fixture order to +x,
        -x, +y, -y, +z, -z with the +g hold of axis i at index 2*i."""
        self.assertEqual(G0, 9.80665)
        self.assertEqual(POSITIONS,
                         ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0),
                          (0, 0, 1), (0, 0, -1)))
        for i in range(3):
            self.assertEqual(POSITIONS[2 * i][i], 1)
            self.assertEqual(POSITIONS[2 * i + 1][i], -1)

    def test_read_off_residuals_gate_calibration(self):
        """Step 6 read-off: the six-position residual rms drops from
        the 8.7e-3 m/s^2 pair level to the 2.4e-4 m/s^2 level once the
        misalignment matrix is fitted, and both gyro per-axis residuals
        sit at the injected rate noise, the two residual fit errors
        that gate the navigation error analysis."""
        pair = imucal.fit_accel_pair_bias_scale(worked_means())
        ls = imucal.fit_accel_misalignment_ls(worked_means())
        self.assertGreater(pair["rms_residual"], 5e-3)
        self.assertLess(ls["rms_residual"], 1e-3)
        gy = imucal.fit_gyro_rate_table(worked_measured(), CMD)
        for rms in gy["rms_per_axis"]:
            self.assertLess(rms, 1e-2)


if __name__ == "__main__":
    unittest.main()
