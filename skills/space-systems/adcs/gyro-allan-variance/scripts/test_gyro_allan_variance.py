"""Contract test for gyro_allan_variance_logic (space-systems/adcs/gyro-allan-variance).

Deterministic, offline, stdlib unittest. Exits 0 on success:

    python3 scripts/test_gyro_allan_variance.py

Covers: the overlapping Allan deviation against the white-noise closed
form AD(tau) = sigma * sqrt(tau0/tau), the log-log noise slope fit, the
noise classification bands, the angle random walk scale in deg/sqrt(h),
the one-call summary dict, and ValueError rejection of every
non-physical input.

Fixtures: a pure white Gaussian series (sigma = 2.0e-5 rad/s, tau0 = 1 s,
N = 65536) synthesized with a seeded RNG, random.Random(20260904), via
the textbook Box-Muller transform (radius uniform first, angle uniform
second), and its cumulative sum as the integrated white noise (rate
random walk) series. The module under test is input-deterministic; the
seeded fixtures reproduce run-to-run.
"""

import math
import random
import unittest

import gyro_allan_variance_logic as gal

SIGMA = 2.0e-5
N_SAMPLES = 65536
TAU0 = 1.0
RNG_SEED = 20260904

# Worked-example anchors: real module outputs on the seeded white-noise
# fixture, slope fit over the dyadic grid tau = 2..256 s.
ANCHOR_AD_1S = 2.000900140959397e-05
ANCHOR_AD_256S = 1.2679578951815105e-06
ANCHOR_AD4_OVER_AD1 = 0.50089560407726996
ANCHOR_SLOPE = -0.49765739778041801
ANCHOR_RRW_SLOPE = 0.50063943885035833
ANCHOR_ARW = 0.068785904577828849


def make_white_noise(n, sigma, seed):
    """Box-Muller white Gaussian series from the seeded stdlib RNG."""
    rng = random.Random(seed)
    samples = []
    while len(samples) < n:
        u_radius = rng.random()
        u_angle = rng.random()
        rho = math.sqrt(-2.0 * math.log(1.0 - u_radius))
        samples.append(rho * math.cos(2.0 * math.pi * u_angle) * sigma)
        if len(samples) < n:
            samples.append(rho * math.sin(2.0 * math.pi * u_angle) * sigma)
    return samples


def cumulative_sum(samples):
    """Integrated white noise series (rate random walk fixture)."""
    out = []
    acc = 0.0
    for value in samples:
        acc += value
        out.append(acc)
    return out


WHITE = make_white_noise(N_SAMPLES, SIGMA, RNG_SEED)
RRW = cumulative_sum(WHITE)
DYADIC_2_256 = [2 ** k for k in range(1, 9)]


def white_slope(series):
    """Fitted log-log slope over the dyadic tau = 2..256 s grid."""
    ads = gal.allan_deviation(series, TAU0, DYADIC_2_256)
    return gal.noise_slope([math.log(t) for t in DYADIC_2_256],
                           [math.log(a) for a in ads])


def assert_rel(test, actual, expected, rtol=1e-6, msg=""):
    test.assertTrue(
        math.isclose(actual, expected, rel_tol=rtol),
        "%s: %r vs expected %r (rtol %g)" % (msg, actual, expected, rtol),
    )


class FixtureSynthesisTests(unittest.TestCase):
    """The seeded fixtures are reproducible and the module deterministic."""

    def test_seeded_fixture_reproducible(self):
        again = make_white_noise(N_SAMPLES, SIGMA, RNG_SEED)
        self.assertEqual(WHITE, again)
        self.assertEqual(len(WHITE), N_SAMPLES)

    def test_module_input_deterministic(self):
        a = gal.allan_deviation(WHITE, TAU0, [1.0, 2.0])
        b = gal.allan_deviation(WHITE, TAU0, [1.0, 2.0])
        self.assertEqual(a, b)


class AllanDeviationWhiteNoiseTests(unittest.TestCase):
    """Overlapping AD on the seeded white-noise fixture."""

    def test_ad_at_1s_anchor_and_ratio_band(self):
        ad1 = gal.allan_deviation(WHITE, TAU0, [1.0])[0]
        assert_rel(self, ad1, ANCHOR_AD_1S, 1e-6, "AD(1 s)")
        self.assertTrue(0.97 <= ad1 / SIGMA <= 1.03,
                        "AD(1 s)/sigma = %r outside [0.97, 1.03]" % (ad1 / SIGMA))

    def test_ad_decays_one_over_sqrt_tau(self):
        ad1 = gal.allan_deviation(WHITE, TAU0, [1.0])[0]
        ad4 = gal.allan_deviation(WHITE, TAU0, [4.0])[0]
        ratio = ad4 / ad1
        self.assertTrue(0.45 <= ratio <= 0.55,
                        "AD(4 s)/AD(1 s) = %r outside [0.45, 0.55]" % ratio)
        assert_rel(self, ratio, ANCHOR_AD4_OVER_AD1, 1e-6, "AD(4)/AD(1)")

    def test_ad_at_256s_anchor_and_ratio_band(self):
        ad256 = gal.allan_deviation(WHITE, TAU0, [256.0])[0]
        assert_rel(self, ad256, ANCHOR_AD_256S, 1e-6, "AD(256 s)")
        self.assertTrue(0.97 <= ad256 / (SIGMA / 16.0) <= 1.03,
                        "AD(256 s) ratio = %r outside [0.97, 1.03]"
                        % (ad256 / (SIGMA / 16.0)))

    def test_ad_spot_ratios_up_to_256s_in_band(self):
        # Spot ratios AD(tau) / (sigma sqrt(tau0/tau)) at intermediate
        # taus spanning the full range up to 256 s.
        spot_taus = [2, 8, 16, 64, 128]
        ads = gal.allan_deviation(WHITE, TAU0, spot_taus)
        for tau, ad in zip(spot_taus, ads):
            ratio = ad / (SIGMA / math.sqrt(tau))
            self.assertTrue(0.97 <= ratio <= 1.03,
                            "ratio at tau=%g s is %r" % (tau, ratio))

    def test_constant_signal_has_zero_ad(self):
        self.assertEqual(gal.allan_deviation([5.0] * 8, TAU0, [1.0, 2.0]),
                         [0.0, 0.0])

    def test_white_slope_band_class_and_anchor(self):
        slope = white_slope(WHITE)
        self.assertTrue(-0.55 <= slope <= -0.45,
                        "white slope %r outside [-0.55, -0.45]" % slope)
        assert_rel(self, slope, ANCHOR_SLOPE, 1e-5, "white-noise slope")
        self.assertEqual(gal.classify_noise(slope), "angle-random-walk")


class AllanDeviationRateRandomWalkTests(unittest.TestCase):
    """Integrated white noise: slope about +0.5, rate-random-walk class."""

    def test_rrw_slope_band_class_and_anchor(self):
        slope = white_slope(RRW)
        self.assertTrue(0.45 <= slope <= 0.55,
                        "RRW slope %r outside [0.45, 0.55]" % slope)
        assert_rel(self, slope, ANCHOR_RRW_SLOPE, 1e-5, "RRW slope")
        self.assertEqual(gal.classify_noise(slope), "rate-random-walk")


class AllanDeviationValueErrorTests(unittest.TestCase):
    """ValueError rejection of non-physical inputs."""

    def test_fewer_than_three_samples_raises(self):
        for bad in ([], [1.0], [1.0, 2.0]):
            with self.assertRaises(ValueError):
                gal.allan_deviation(bad, TAU0, [1.0])

    def test_tau0_non_positive_raises(self):
        for bad in (0.0, -1.0):
            with self.assertRaises(ValueError):
                gal.allan_deviation(WHITE, bad, [1.0])

    def test_tau_below_tau0_raises(self):
        with self.assertRaises(ValueError):
            gal.allan_deviation(WHITE, TAU0, [0.5])

    def test_tau_not_whole_multiple_raises(self):
        with self.assertRaises(ValueError):
            gal.allan_deviation(WHITE, TAU0, [1.5])

    def test_tau_too_long_for_sample_raises(self):
        short = [0.1 * i for i in range(10)]  # N = 10, m max = 4
        gal.allan_deviation(short, TAU0, [4.0])  # boundary m = 4 allowed
        for bad_tau in (5.0, 6.0):
            with self.assertRaises(ValueError):
                gal.allan_deviation(short, TAU0, [bad_tau])

    def test_taus_output_order_matches_input(self):
        taus = [256.0, 1.0, 4.0]
        ads = gal.allan_deviation(WHITE, TAU0, taus)
        direct = [gal.allan_deviation(WHITE, TAU0, [t])[0] for t in taus]
        self.assertEqual(ads, direct)


class NoiseSlopeTests(unittest.TestCase):
    """Least-squares log-log slope fit."""

    def test_slope_empty_lists_raise(self):
        with self.assertRaises(ValueError):
            gal.noise_slope([], [])
        with self.assertRaises(ValueError):
            gal.noise_slope([1.0], [])

    def test_slope_mismatched_lengths_raise(self):
        with self.assertRaises(ValueError):
            gal.noise_slope([1.0, 2.0], [1.0])

    def test_slope_single_point_raises(self):
        with self.assertRaises(ValueError):
            gal.noise_slope([1.0], [2.0])

    def test_slope_zero_variance_grid_raises(self):
        with self.assertRaises(ValueError):
            gal.noise_slope([1.0, 1.0, 1.0], [2.0, 3.0, 4.0])

    def test_slope_theory_minus_half_line(self):
        # log(AD) = log(sigma) - 0.5 * log(tau): slope is -0.5 exactly.
        xs = [math.log(t) for t in DYADIC_2_256]
        ys = [math.log(SIGMA * math.sqrt(TAU0 / t)) for t in DYADIC_2_256]
        assert_rel(self, gal.noise_slope(xs, ys), -0.5, 1e-9)


class ClassifyNoiseTests(unittest.TestCase):
    """Deterministic slope-band classification."""

    def test_classify_minus_half_angle_random_walk(self):
        self.assertEqual(gal.classify_noise(-0.5), "angle-random-walk")

    def test_classify_plus_half_rate_random_walk(self):
        self.assertEqual(gal.classify_noise(0.5), "rate-random-walk")

    def test_classify_minus_one_quantization_noise(self):
        self.assertEqual(gal.classify_noise(-1.0), "quantization-noise")
        self.assertEqual(gal.classify_noise(-0.85), "quantization-noise")

    def test_classify_zero_bias_instability(self):
        self.assertEqual(gal.classify_noise(0.0), "bias-instability")

    def test_classify_partition_sweep(self):
        # Every band boundary and gap falls to the documented class.
        cases = [
            (-0.9, "quantization-noise"), (-0.85, "quantization-noise"),
            (-0.8, "mixed"), (-0.75, "angle-random-walk"),
            (-0.5, "angle-random-walk"), (-0.25, "angle-random-walk"),
            (-0.2, "mixed"), (-0.14, "bias-instability"),
            (0.0, "bias-instability"), (0.14, "bias-instability"),
            (0.2, "mixed"), (0.25, "rate-random-walk"),
            (0.5, "rate-random-walk"), (0.75, "rate-random-walk"),
            (0.8, "mixed"), (1.0, "mixed"),
        ]
        for slope, expected in cases:
            self.assertEqual(gal.classify_noise(slope), expected,
                             "slope %r" % slope)


class AngleRandomWalkTests(unittest.TestCase):
    """ARW scale in deg/sqrt(h)."""

    def test_arw_reference_scale(self):
        # 2.0e-5 rad/s * 57.2958 * sqrt(3600) ~ 0.0688 deg/sqrt(h).
        arw = gal.angle_random_walk(2.0e-5, 1.0)
        assert_rel(self, arw, 0.06875496, 1e-9)
        self.assertTrue(0.065 <= arw <= 0.073)

    def test_arw_from_fixture_anchor(self):
        ad1 = gal.allan_deviation(WHITE, TAU0, [1.0])[0]
        arw = gal.angle_random_walk(ad1, TAU0)
        assert_rel(self, arw, ANCHOR_ARW, 1e-6, "fixture ARW")
        self.assertTrue(0.065 <= arw <= 0.073)

    def test_arw_doubling_ad_doubles_arw(self):
        base = gal.angle_random_walk(1.0e-5, 1.0)
        assert_rel(self, gal.angle_random_walk(2.0e-5, 1.0), 2.0 * base, 1e-12)

    def test_arw_tau0_scaling_sqrt(self):
        # tau0 = 0.25 s scales the coefficient by sqrt(0.25) = 0.5.
        arw1 = gal.angle_random_walk(2.0e-5, 1.0)
        arw025 = gal.angle_random_walk(2.0e-5, 0.25)
        assert_rel(self, arw025, 0.5 * arw1, 1e-12)

    def test_arw_non_positive_inputs_raise(self):
        for bad_ad in (0.0, -1e-5):
            with self.assertRaises(ValueError):
                gal.angle_random_walk(bad_ad, 1.0)
        for bad_tau0 in (0.0, -0.5):
            with self.assertRaises(ValueError):
                gal.angle_random_walk(1e-5, bad_tau0)


class GyroNoiseSummaryTests(unittest.TestCase):
    """One-call summary dict."""

    def test_summary_dict_keys_exact(self):
        summ = gal.gyro_noise_summary(WHITE, TAU0, DYADIC_2_256)
        self.assertEqual(
            sorted(summ.keys()),
            ["ad_at_1s", "allan_deviations", "arw_deg_per_sqrt_h",
             "fitted_slope", "noise_class", "taus"],
        )

    def test_summary_consistent_with_direct_calls(self):
        summ = gal.gyro_noise_summary(WHITE, TAU0, DYADIC_2_256)
        ad1 = gal.allan_deviation(WHITE, TAU0, [1.0])[0]
        ads = gal.allan_deviation(WHITE, TAU0, DYADIC_2_256)
        slope = gal.noise_slope([math.log(t) for t in DYADIC_2_256],
                                [math.log(a) for a in ads])
        assert_rel(self, summ["ad_at_1s"], ad1, 1e-12)
        assert_rel(self, summ["fitted_slope"], slope, 1e-12)
        assert_rel(self, summ["arw_deg_per_sqrt_h"],
                   gal.angle_random_walk(ad1, TAU0), 1e-12)
        self.assertEqual(summ["taus"], DYADIC_2_256)
        self.assertEqual(summ["allan_deviations"], ads)
        self.assertEqual(summ["noise_class"], gal.classify_noise(slope))

    def test_summary_worked_example_values(self):
        summ = gal.gyro_noise_summary(WHITE, TAU0, DYADIC_2_256)
        self.assertEqual(summ["noise_class"], "angle-random-walk")
        assert_rel(self, summ["fitted_slope"], ANCHOR_SLOPE, 1e-5)
        assert_rel(self, summ["ad_at_1s"], ANCHOR_AD_1S, 1e-6)
        assert_rel(self, summ["arw_deg_per_sqrt_h"], ANCHOR_ARW, 1e-6)

    def test_summary_unreachable_1s_cluster_raises(self):
        # tau0 = 2 s: a 1 s cluster is not representable, so the
        # summary cannot form its ARW reference and must refuse.
        with self.assertRaises(ValueError):
            gal.gyro_noise_summary(WHITE, 2.0, DYADIC_2_256)


if __name__ == "__main__":
    unittest.main()
