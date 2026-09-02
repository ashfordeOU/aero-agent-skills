"""Bootstrap SIR particle filter: nonlinear, non-Gaussian state estimation.

Pure Python standard library only (no numpy, no network). Particles are
scalar positions in one dimension; the ensemble approximates the full
posterior distribution, so it stays valid when the posterior is bimodal
or otherwise non-Gaussian, which a single Gaussian (Kalman family)
filter cannot represent.

Randomness is confined to a caller-supplied random.Random instance or,
for run_particle_filter, to a random.Random seeded with a fixed integer,
so every run is exactly reproducible.

The bootstrap (sampling importance resampling, SIR) recursion per
measurement is:

    predict:   x_i <- x_i + velocity * dt + N(0, process_std)
    update:    w_i <- w_i * N(z; h(x_i), meas_std)   (unnormalized)
    normalize: w_i <- w_i / sum(w)
    resample:  if ESS < n/2, systematic resampling back to equal weights

h is the measurement function; the default is the identity (direct
position measurement). For a nonlinear h (for example a range-squared
sensor h(x) = x^2) the likelihood can be multimodal, and the particle
filter keeps every mode that the data supports.

Public API
----------
initialize_particles(n, prior_mean, prior_std, rng)
predict_particles(particles, dt, process_std, rng, velocity=0.0)
update_weights(particles, weights, measurement, meas_std, h=None)
normalize_weights(weights)
effective_sample_size(weights)
systematic_resample(particles, weights, rng)
particle_filter_estimate(particles, weights)
run_particle_filter(measurements, dt, n, prior, process_std, meas_std,
                    seed, velocity=0.0)
"""

import math
import random


def initialize_particles(n, prior_mean, prior_std, rng):
    """Draw n particles from N(prior_mean, prior_std).

    Returns a list of n independent Gaussian draws. Raises ValueError
    when n <= 0 or prior_std < 0.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    if prior_std < 0.0:
        raise ValueError("prior_std must be non-negative")
    return [rng.gauss(prior_mean, prior_std) for _ in range(n)]


def predict_particles(particles, dt, process_std, rng, velocity=0.0):
    """Constant-velocity (or random-walk) predict step with Gaussian noise.

    Every particle advances as x_i <- x_i + velocity * dt + w_i with
    w_i ~ N(0, process_std). velocity=0.0 (default) gives a pure random
    walk; a non-zero velocity is the constant-velocity motion model.
    Returns the predicted particle list. Raises ValueError for an empty
    particle list, dt <= 0, or process_std < 0.
    """
    if not particles:
        raise ValueError("particles must not be empty")
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if process_std < 0.0:
        raise ValueError("process_std must be non-negative")
    drift = velocity * dt
    return [p + drift + rng.gauss(0.0, process_std) for p in particles]


def update_weights(particles, weights, measurement, meas_std, h=None):
    """Gaussian likelihood weight update w_i <- w_i * N(z; h(x_i), sigma).

    h defaults to the identity (position measurement). The likelihood
    of particle x_i is exp(-0.5 * ((z - h(x_i)) / meas_std)^2) with the
    constant factor omitted. Returns the UNNORMALIZED weights.

    meas_std == 0.0 is handled as a limit: a particle keeps its weight
    only when h(x_i) equals the measurement exactly (division by zero
    never occurs). Raises ValueError when the particle and weight lists
    differ in length, either is empty, or meas_std < 0.
    """
    if len(particles) != len(weights):
        raise ValueError("particles and weights must have equal length")
    if not particles:
        raise ValueError("particles must not be empty")
    if meas_std < 0.0:
        raise ValueError("meas_std must be non-negative")
    meas = (lambda x: x) if h is None else h
    updated = []
    if meas_std == 0.0:
        for p, w in zip(particles, weights):
            updated.append(w if meas(p) == measurement else 0.0)
        return updated
    inv_var = -0.5 / (meas_std * meas_std)
    for p, w in zip(particles, weights):
        resid = (measurement - meas(p)) / meas_std
        updated.append(w * math.exp(inv_var * resid * resid))
    return updated


def normalize_weights(weights):
    """Normalize weights so they sum to 1.0.

    Raises ValueError when the list is empty or the total weight is
    zero (fully collapsed posterior).
    """
    if not weights:
        raise ValueError("weights must not be empty")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("total weight must be positive")
    return [w / total for w in weights]


def effective_sample_size(weights):
    """Effective sample size ESS = (sum w)^2 / sum(w^2).

    For normalized weights this reduces to 1 / sum(w^2); the general
    form also handles unnormalized inputs. ESS lies between 1 (all mass
    on one particle) and n (uniform). The standard degeneracy trigger
    resamples when ESS < n / 2. Raises ValueError for an empty list,
    negative weights, or a non-positive total.
    """
    if not weights:
        raise ValueError("weights must not be empty")
    if any(w < 0.0 for w in weights):
        raise ValueError("weights must be non-negative")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("total weight must be positive")
    sq = sum(w * w for w in weights)
    if sq <= 0.0:
        raise ValueError("sum of squared weights must be positive")
    return total * total / sq


def systematic_resample(particles, weights, rng):
    """Systematic (deterministic stratified) resampling.

    Draws one uniform start u0 in [0, 1/n) and replicates particle j for
    every stratum target u0 + i/n that falls in the j-th weight bin of
    the cumulative distribution. The returned particles have equal
    weights 1/n. The resampled ensemble is a Monte Carlo copy of the
    weighted one: its weighted estimate is statistically unchanged.
    Raises ValueError for mismatched or empty lists and for invalid
    (negative or all-zero) weights.
    """
    if len(particles) != len(weights):
        raise ValueError("particles and weights must have equal length")
    if not particles:
        raise ValueError("particles must not be empty")
    if any(w < 0.0 for w in weights):
        raise ValueError("weights must be non-negative")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("total weight must be positive")
    n = len(particles)
    cdf = []
    acc = 0.0
    for w in weights:
        acc += w
        cdf.append(acc / total)
    start = rng.random() / n
    new_particles = []
    j = 0
    for i in range(n):
        target = start + i / n
        while j < n - 1 and cdf[j] < target:
            j += 1
        new_particles.append(particles[j])
    return new_particles, [1.0 / n] * n


def particle_filter_estimate(particles, weights):
    """Weighted posterior mean and standard deviation.

    Returns (mean, std) with std the square root of the weighted
    variance about the weighted mean; both computed from UNNORMALIZED
    weights. Raises ValueError for mismatched or empty lists and for a
    non-positive total weight.
    """
    if len(particles) != len(weights):
        raise ValueError("particles and weights must have equal length")
    if not particles:
        raise ValueError("particles must not be empty")
    total = sum(weights)
    if total <= 0.0:
        raise ValueError("total weight must be positive")
    mean = sum(w * p for w, p in zip(weights, particles)) / total
    var = sum(w * (p - mean) * (p - mean)
              for w, p in zip(weights, particles)) / total
    return mean, math.sqrt(max(var, 0.0))


def run_particle_filter(measurements, dt, n, prior, process_std, meas_std,
                        seed, velocity=0.0):
    """Full bootstrap SIR run over a measurement sequence.

    Parameters
    ----------
    measurements : list of float, position measurements z_k, one per step
    dt : float, time between measurements (seconds)
    n : int, particle count
    prior : (mean, std) tuple of the Gaussian initial distribution
    process_std : float, per-step process noise standard deviation
    meas_std : float, measurement noise standard deviation
    seed : int, fixed integer seed for full reproducibility
    velocity : float, constant-velocity model term (0.0 = random walk)

    Each step predicts, updates the weights with the Gaussian
    likelihood, normalizes, records the weighted (mean, std), the
    effective sample size, and whether resampling fired (ESS < n/2);
    a fired trigger is followed by systematic resampling to equal
    weights. Returns a dict:

        {"steps": [{"mean", "std", "ess", "resampled"} x len(measurements)],
         "particles": final particle list,
         "weights":   final weight list}

    Raises ValueError for n <= 0, negative prior_std, dt <= 0, or a
    negative noise standard deviation.
    """
    if n <= 0:
        raise ValueError("n must be positive")
    prior_mean, prior_std = prior
    if prior_std < 0.0:
        raise ValueError("prior_std must be non-negative")
    if dt <= 0.0:
        raise ValueError("dt must be positive")
    if process_std < 0.0 or meas_std < 0.0:
        raise ValueError("noise standard deviations must be non-negative")
    rng = random.Random(seed)
    particles = initialize_particles(n, prior_mean, prior_std, rng)
    weights = [1.0 / n] * n
    steps = []
    for z in measurements:
        particles = predict_particles(particles, dt, process_std, rng,
                                      velocity)
        weights = update_weights(particles, weights, z, meas_std)
        weights = normalize_weights(weights)
        mean, std = particle_filter_estimate(particles, weights)
        ess = effective_sample_size(weights)
        resampled = ess < n / 2.0
        steps.append({"mean": mean, "std": std, "ess": ess,
                      "resampled": resampled})
        if resampled:
            particles, weights = systematic_resample(particles, weights,
                                                     rng)
    return {"steps": steps, "particles": particles, "weights": weights}
