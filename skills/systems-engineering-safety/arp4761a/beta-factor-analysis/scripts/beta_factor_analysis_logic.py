"""Beta-factor common-cause analysis for redundant channels.

Quantifies the common-cause contribution to redundant-channel failure
with the beta-factor model: a component failure rate lambda is split
into the independent rate (1 - beta) * lambda and the shared
common-cause rate beta * lambda. A common-cause shock with probability
Q_cc = 1 - exp(-beta * lambda * t) fails both channels at once, and the
dual-channel failure probability combines the independent double
failure q_i^2 with the shock by inclusion-exclusion. Pure stdlib,
deterministic, no network.

Assumption recorded (per the wave-39 spec): the standard engineering
beta-factor method with identical redundant channels sharing one
common-cause shock over exposure time t, per ARP4761A common-cause
analysis practice. Summary-only, the standard text is not reproduced.
"""

import math

BETA_MIN = 0.0
BETA_MAX = 1.0


def _validate_inputs(failure_rate, beta, time=None):
    """Reject non-physical inputs shared by every public function.

    failure_rate must be strictly positive, beta must lie in
    [BETA_MIN, BETA_MAX], and time, when given, must be non-negative.
    """
    if failure_rate <= 0:
        raise ValueError("failure_rate must be strictly positive")
    if beta < BETA_MIN or beta > BETA_MAX:
        raise ValueError("beta must be within [0, 1]")
    if time is not None and time < 0:
        raise ValueError("time must be non-negative")


def split_failure_rate(failure_rate, beta):
    """Split a failure rate into independent and common-cause parts.

    Returns {"independent": (1 - beta) * lambda, "common_cause":
    beta * lambda} for the input failure_rate lambda and beta factor.
    The parts sum to the total rate: the shared fraction beta leaves
    (1 - beta) of the rate to fail a channel on its own.
    """
    _validate_inputs(failure_rate, beta)
    return {
        "independent": (1.0 - beta) * failure_rate,
        "common_cause": beta * failure_rate,
    }


def common_cause_probability(failure_rate, beta, time):
    """Compute the common-cause shock probability Q_cc.

    Q_cc = 1 - exp(-beta * lambda * t): the probability that the shared
    cause strikes within exposure time t and fails both channels.
    """
    _validate_inputs(failure_rate, beta, time)
    return 1.0 - math.exp(-beta * failure_rate * time)


def _independent_channel_probability(failure_rate, beta, time):
    """Return q_i = 1 - exp(-(1 - beta) * lambda * t).

    The single-channel failure probability driven by the independent
    rate alone; its square is the independent double failure.
    """
    return 1.0 - math.exp(-(1.0 - beta) * failure_rate * time)


def dual_channel_ccf_probability(failure_rate, beta, time):
    """Compute the dual-channel CCF-inclusive failure probability.

    Q_dual = q_i^2 + q_c - q_i^2 * q_c with q_i the independent
    single-channel probability and q_c the common-cause shock
    probability: the inclusion-exclusion union of the independent
    double failure and the shared shock.
    """
    _validate_inputs(failure_rate, beta, time)
    q_i = _independent_channel_probability(failure_rate, beta, time)
    q_i_sq = q_i * q_i
    q_c = common_cause_probability(failure_rate, beta, time)
    return q_i_sq + q_c - q_i_sq * q_c


def ccf_enhancement(failure_rate, beta, time):
    """Compute the CCF enhancement ratio over independence.

    Q_dual divided by the independence-only parallel probability
    (1 - exp(-lambda * t))^2. At beta == 0 the ratio is exactly 1.0 by
    identity (returned first, which also guards the time == 0 division);
    at beta > 0 with time == 0 the ratio is undefined, so ValueError.
    """
    _validate_inputs(failure_rate, beta, time)
    if beta == BETA_MIN:
        return 1.0
    if time == 0.0:
        raise ValueError("ccf_enhancement needs time > 0 when beta > 0")
    q_dual = dual_channel_ccf_probability(failure_rate, beta, time)
    indep_only = (1.0 - math.exp(-failure_rate * time)) ** 2
    return q_dual / indep_only
