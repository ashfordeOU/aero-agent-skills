#!/usr/bin/env python3
"""Contract test for the Particle Filter leaf.

Stdlib unittest only (gate 3): imports the standard library and the
sibling logic module particle_filter_logic.py. Deterministic (offline,
every random.Random seeded with a fixed integer). Covers the gate 3
contract:

  - initialization draws from the Gaussian prior with the right moments
  - constant-velocity predict advances the cloud by velocity * dt and
    widens it by the process noise
  - Gaussian likelihood weight updates, the zero-measurement-noise
    limit, and a nonlinear (range-squared) measurement that produces a
    genuinely bimodal likelihood
  - normalization, effective sample size, systematic resampling, and
    the weighted posterior mean and standard deviation
  - the worked example: a 20 step constant-velocity tracking run at
    1.0 m/s with 5000 particles and seed 7 converges to within 0.05 m
    of the true final position (final error about 0.004 m) and stays
    within 0.5 m over the last seven steps
  - the bimodal case: a range-squared sensor keeps both sign modes
    alive at first (a Gaussian filter cannot), then the weights
    concentrate on the true positive corridor as the target recedes
  - ValueError rejection of non-physical inputs and of mismatched
    particle and weight arrays

Run standalone:
    python3 scripts/test_particle_filter.py
"""

import math
import random
import unittest

from particle_filter_logic import (
    effective_sample_size,
    initialize_particles,
    normalize_weights,
    particle_filter_estimate,
    predict_particles,
    run_particle_filter,
    systematic_resample,
    update_weights,
)


def squared_range(x):
    """Nonlinear sensor: squared range from the origin, sign ambiguous."""
    return x * x


def generate_cv_run(meas_seed, v, dt, steps, meas_std, filt_seed,
                    n, process_std, prior):
    """Deterministic constant-velocity scenario: truth, measurements, run.

    The truth starts at zero and moves at constant velocity v; noisy
    position measurements are drawn with meas_seed; the filter runs
    with filt_seed. Returns (truth, result_dict).
    """
    rng = random.Random(meas_seed)
    truth = [v * dt * k for k in range(steps)]
    measurements = [t + rng.gauss(0.0, meas_std) for t in truth]
    result = run_particle_filter(measurements, dt, n, prior, process_std,
                                 meas_std, filt_seed, velocity=v)
    return truth, result


class TestInitialize(unittest.TestCase):
    def test_draws_expected_count(self):
        rng = random.Random(1)
        particles = initialize_particles(1000, 0.0, 1.0, rng)
        self.assertEqual(len(particles), 1000)

    def test_prior_moments_reproduced(self):
        rng = random.Random(2)
        particles = initialize_particles(20000, 3.0, 2.0, rng)
        mean = sum(particles) / len(particles)
        var = sum((p - mean) ** 2 for p in particles) / len(particles)
        self.assertLess(abs(mean - 3.0), 0.05)
        self.assertLess(abs(math.sqrt(var) - 2.0), 0.05)

    def test_deterministic_with_fixed_seed(self):
        rng_a = random.Random(9)
        rng_b = random.Random(9)
        self.assertEqual(initialize_particles(50, 1.0, 0.5, rng_a),
                         initialize_particles(50, 1.0, 0.5, rng_b))

    def test_rejects_nonphysical_arguments(self):
        rng = random.Random(0)
        for bad_n in (0, -1):
            with self.assertRaises(ValueError):
                initialize_particles(bad_n, 0.0, 1.0, rng)
        with self.assertRaises(ValueError):
            initialize_particles(10, 0.0, -0.5, rng)


class TestPredict(unittest.TestCase):
    def test_constant_velocity_drift(self):
        rng = random.Random(3)
        particles = [10.0] * 5000
        out = predict_particles(particles, 2.0, 0.1, rng, velocity=1.5)
        mean = sum(out) / len(out)
        self.assertAlmostEqual(mean, 13.0, places=2)  # 10 + 1.5 * 2.0

    def test_random_walk_keeps_mean(self):
        rng = random.Random(4)
        particles = [10.0] * 8000
        out = predict_particles(particles, 1.0, 0.1, rng)
        mean = sum(out) / len(out)
        self.assertLess(abs(mean - 10.0), 0.01)

    def test_process_noise_spreads_cloud(self):
        rng = random.Random(5)
        particles = [10.0] * 8000
        out = predict_particles(particles, 1.0, 0.5, rng)
        std = math.sqrt(sum((p - 10.0) ** 2 for p in out) / len(out))
        self.assertAlmostEqual(std, 0.5, places=2)

    def test_rejects_nonphysical_arguments(self):
        rng = random.Random(0)
        with self.assertRaises(ValueError):
            predict_particles([], 1.0, 0.1, rng)
        for bad_dt in (0.0, -1.0):
            with self.assertRaises(ValueError):
                predict_particles([1.0], bad_dt, 0.1, rng)
        with self.assertRaises(ValueError):
            predict_particles([1.0], 1.0, -0.1, rng)


class TestUpdateWeights(unittest.TestCase):
    def test_gaussian_likelihood_hand_computed(self):
        particles = [0.0, 1.0, 2.0, 3.0]
        out = update_weights(particles, [1.0] * 4, 2.0, 1.0)
        # likelihood exp(-0.5*(z-x)^2): x=2.0 -> 1.0; x=1.0/3.0 -> exp(-0.5)
        self.assertAlmostEqual(out[2], 1.0)
        self.assertAlmostEqual(out[0], math.exp(-2.0))
        self.assertAlmostEqual(out[1], math.exp(-0.5))

    def test_weights_returned_unnormalized(self):
        out = update_weights([5.0], [3.0], 5.0, 1.0)
        self.assertEqual(out, [3.0])  # scale kept, not normalized

    def test_zero_meas_std_keeps_only_exact_match(self):
        weights = [0.1, 0.2, 0.3, 0.4]
        out = update_weights([0.0, 1.0, 2.0, 3.0], weights, 2.0, 0.0)
        self.assertEqual(out[2], 0.3)
        self.assertEqual(sum(out[:2]) + out[3], 0.0)

    def test_range_squared_likelihood_is_bimodal(self):
        # h(x) = x^2: z=16 is explained by x=+4 and x=-4 equally
        out = update_weights([-4.0, -1.0, 0.0, 1.0, 4.0], [1.0] * 5,
                             16.0, 0.5, h=squared_range)
        self.assertAlmostEqual(out[0], out[4])      # both modes equal peak
        self.assertAlmostEqual(out[0], 1.0)
        self.assertLess(out[2], 1e-100)             # valley at x=0 is dead

    def test_rejects_nonphysical_arguments(self):
        with self.assertRaises(ValueError):
            update_weights([1.0, 2.0], [1.0], 1.0, 1.0)  # length mismatch
        with self.assertRaises(ValueError):
            update_weights([], [], 1.0, 1.0)
        with self.assertRaises(ValueError):
            update_weights([1.0], [1.0], 1.0, -0.5)


class TestNormalize(unittest.TestCase):
    def test_sums_to_one_and_preserves_ratios(self):
        out = normalize_weights([1.0, 2.0, 1.0])
        self.assertAlmostEqual(sum(out), 1.0)
        self.assertAlmostEqual(out[1], 0.5)
        self.assertAlmostEqual(out[0], 0.25)

    def test_rejects_zero_total_and_empty(self):
        with self.assertRaises(ValueError):
            normalize_weights([0.0, 0.0])
        with self.assertRaises(ValueError):
            normalize_weights([])


class TestEffectiveSampleSize(unittest.TestCase):
    def test_uniform_weights_give_full_sample(self):
        n = 500
        self.assertAlmostEqual(effective_sample_size([1.0 / n] * n), n)

    def test_point_mass_gives_one(self):
        self.assertAlmostEqual(effective_sample_size([0.0, 1.0, 0.0]), 1.0)

    def test_hand_computed_middle_case(self):
        # weights 0.1, 0.9 -> ESS = 1 / (0.01 + 0.81) = 1.2195...
        self.assertAlmostEqual(effective_sample_size([0.1, 0.9]),
                               1.0 / 0.82, places=6)

    def test_rejects_invalid_weights(self):
        with self.assertRaises(ValueError):
            effective_sample_size([1.0, -1.0])
        with self.assertRaises(ValueError):
            effective_sample_size([0.0, 0.0])


class TestSystematicResample(unittest.TestCase):
    def test_returns_equal_weights(self):
        rng = random.Random(6)
        out, w = systematic_resample([1.0, 2.0, 3.0, 4.0],
                                     [0.1, 0.2, 0.3, 0.4], rng)
        self.assertEqual(len(out), 4)
        self.assertEqual(w, [0.25] * 4)

    def test_high_weight_particle_dominates(self):
        rng = random.Random(7)
        particles = list(range(10))
        out, _ = systematic_resample(particles, [0.91] + [0.01] * 9, rng)
        # about 91% of the 10 children should copy the heavy particle
        self.assertGreaterEqual(out.count(0), 8)

    def test_preserves_weighted_mean(self):
        rng = random.Random(8)
        particles = [rng.gauss(0.0, 3.0) for _ in range(5000)]
        raw = [abs(rng.gauss(1.0, 0.5)) for _ in range(5000)]
        tot = sum(raw)
        w = [wi / tot for wi in raw]
        before, _ = particle_filter_estimate(particles, w)
        out, w_out = systematic_resample(particles, w, random.Random(8))
        after, _ = particle_filter_estimate(out, w_out)
        self.assertLess(abs(before - after), 0.2)

    def test_deterministic_with_fixed_seed(self):
        p = [1.0, 2.0, 3.0]
        w = [0.2, 0.3, 0.5]
        a, _ = systematic_resample(p, w, random.Random(11))
        b, _ = systematic_resample(p, w, random.Random(11))
        self.assertEqual(a, b)

    def test_rejects_invalid_arguments(self):
        rng = random.Random(0)
        with self.assertRaises(ValueError):
            systematic_resample([1.0, 2.0], [0.5], rng)  # mismatch
        with self.assertRaises(ValueError):
            systematic_resample([1.0, 2.0], [-0.1, 1.1], rng)
        with self.assertRaises(ValueError):
            systematic_resample([1.0, 2.0], [0.0, 0.0], rng)


class TestEstimate(unittest.TestCase):
    def test_hand_computed_mean_and_std(self):
        mean, std = particle_filter_estimate([0.0, 1.0], [0.25, 0.75])
        self.assertAlmostEqual(mean, 0.75)
        self.assertAlmostEqual(std, math.sqrt(0.25 * 0.75), places=10)

    def test_single_particle_zero_std(self):
        mean, std = particle_filter_estimate([3.5], [1.0])
        self.assertAlmostEqual(mean, 3.5)
        self.assertAlmostEqual(std, 0.0)

    def test_rejects_invalid_arguments(self):
        with self.assertRaises(ValueError):
            particle_filter_estimate([1.0, 2.0], [1.0])  # mismatch
        with self.assertRaises(ValueError):
            particle_filter_estimate([1.0, 2.0], [0.0, 0.0])


class TestRunParticleFilter(unittest.TestCase):
    def test_worked_example_converges_to_true_trajectory(self):
        # Constant-velocity target at 1.0 m/s, dt = 1 s, prior N(0, 5),
        # measurement noise std 1.0, process noise std 0.5, n = 5000,
        # filter seed 7 (measurement draws seeded separately).
        truth, result = generate_cv_run(
            meas_seed=26, v=1.0, dt=1.0, steps=20, meas_std=1.0,
            filt_seed=7, n=5000, process_std=0.5, prior=(0.0, 5.0))
        steps = result["steps"]
        self.assertEqual(len(steps), 20)
        errs = [abs(s["mean"] - t) for s, t in zip(steps, truth)]
        # converged: every step from 13 on within 0.5 m of the truth
        for err in errs[13:]:
            self.assertLess(err, 0.5)
        # final estimate at step 19: 19.0039 m against truth 19.0 m
        self.assertAlmostEqual(steps[19]["mean"], 19.0039, places=3)
        self.assertLess(errs[19], 0.05)

    def test_resampling_fires_only_when_ess_below_half(self):
        truth, result = generate_cv_run(
            meas_seed=26, v=1.0, dt=1.0, steps=20, meas_std=1.0,
            filt_seed=7, n=5000, process_std=0.5, prior=(0.0, 5.0))
        for s in result["steps"]:
            self.assertEqual(s["resampled"], s["ess"] < 2500.0)
        # degeneracy recurs: the trigger fires on several steps
        n_fired = sum(1 for s in result["steps"] if s["resampled"])
        self.assertGreaterEqual(n_fired, 3)

    def test_deterministic_run_to_run(self):
        kw = dict(meas_seed=3, v=0.8, dt=1.0, steps=12, meas_std=1.0,
                  filt_seed=10, n=3000, process_std=0.4, prior=(0.0, 3.0))
        _, result_a = generate_cv_run(**kw)
        _, result_b = generate_cv_run(**kw)
        ma = [s["mean"] for s in result_a["steps"]]
        mb = [s["mean"] for s in result_b["steps"]]
        self.assertEqual(ma, mb)

    def test_random_walk_mode_and_empty_input(self):
        # velocity = 0 (pure random walk): one noisy measurement keeps a
        # finite posterior, and an empty measurement list yields no steps
        rng = random.Random(40)
        measurements = [0.0 + rng.gauss(0.0, 1.0)]
        result = run_particle_filter(measurements, 1.0, 2000, (0.0, 2.0),
                                     0.5, 1.0, 41)
        self.assertEqual(len(result["steps"]), 1)
        self.assertLess(result["steps"][0]["std"], 2.0)
        empty = run_particle_filter([], 1.0, 100, (0.0, 1.0), 0.5, 1.0, 1)
        self.assertEqual(empty["steps"], [])

    def test_rejects_nonphysical_arguments(self):
        with self.assertRaises(ValueError):
            run_particle_filter([1.0], 1.0, 0, (0.0, 1.0), 0.5, 1.0, 1)
        with self.assertRaises(ValueError):
            run_particle_filter([1.0], 1.0, 100, (0.0, -1.0), 0.5, 1.0, 1)
        with self.assertRaises(ValueError):
            run_particle_filter([1.0], 0.0, 100, (0.0, 1.0), 0.5, 1.0, 1)
        with self.assertRaises(ValueError):
            run_particle_filter([1.0], 1.0, 100, (0.0, 1.0), -0.5, 1.0, 1)
        with self.assertRaises(ValueError):
            run_particle_filter([1.0], 1.0, 100, (0.0, 1.0), 0.5, -1.0, 1)


class TestBimodalNonGaussian(unittest.TestCase):
    """Squared-range sensor: z = x^2 + noise is sign ambiguous.

    A single Gaussian posterior cannot hold the two modes x = +sqrt(z)
    and x = -sqrt(z); the particle ensemble keeps both alive until the
    receding motion of the true corridor concentrates the weights.
    """

    @staticmethod
    def run_scenario(meas_seed, filt_seed, steps=10, n_per_mode=2000,
                     x0=4.0, v=0.4, process_std=0.1, meas_std=1.5,
                     prior_std=0.5):
        rng = random.Random(meas_seed)
        truth = [x0 + v * k for k in range(steps)]
        measurements = [t * t + rng.gauss(0.0, meas_std) for t in truth]
        frng = random.Random(filt_seed)
        particles = (initialize_particles(n_per_mode, x0, prior_std, frng) +
                     initialize_particles(n_per_mode, -x0, prior_std, frng))
        weights = [1.0 / len(particles)] * len(particles)
        rows = []
        for z in measurements:
            particles = predict_particles(particles, 1.0, process_std, frng,
                                          velocity=v)
            weights = update_weights(particles, weights, z, meas_std,
                                     h=squared_range)
            weights = normalize_weights(weights)
            mean, std = particle_filter_estimate(particles, weights)
            mass_pos = sum(w for p, w in zip(particles, weights) if p > 0.0)
            ess = effective_sample_size(weights)
            rows.append({"mean": mean, "std": std, "mass_pos": mass_pos,
                         "ess": ess})
            if ess < len(particles) / 2.0:
                particles, weights = systematic_resample(particles, weights,
                                                         frng)
        return truth, rows

    def test_early_posterior_keeps_both_modes(self):
        truth, rows = self.run_scenario(meas_seed=5, filt_seed=3)
        # step 0: range-squared of x=+4 and x=-4 both explain z ~ 16, so
        # the posterior stays wide and split across both corridors
        self.assertGreater(rows[0]["std"], 2.0)
        self.assertGreater(rows[0]["mass_pos"], 0.2)
        self.assertLess(rows[0]["mass_pos"], 0.8)

    def test_weights_concentrate_on_true_mode(self):
        truth, rows = self.run_scenario(meas_seed=5, filt_seed=3)
        # as the true target recedes, z grows like (4 + 0.4t)^2 and the
        # mirror hypothesis at negative x loses likelihood; by step 9 the
        # whole posterior mass sits on the true positive corridor and the
        # estimate matches the truth at 7.60 m (estimate 7.6035 m)
        self.assertGreater(rows[-1]["mass_pos"], 0.999)
        self.assertAlmostEqual(rows[-1]["mean"], truth[-1], places=2)
        for row in rows[2:]:
            self.assertGreater(row["mass_pos"], 0.999)


if __name__ == "__main__":
    unittest.main()
