#!/usr/bin/env python3
"""Markov analysis logic for safety and reliability assessment (paraphrase).

Common-knowledge summary (standards-map.yaml, arp4761a: proprietary,
summary-only): Markov analysis models a system as a continuous time
Markov chain (CTMC). States represent configurations such as fully
operational, degraded, and failed; transitions happen at constant
rates (failure rate lambda and repair rate mu, per hour). The state
probability vector P(t) evolves by dP/dt = P Q, where Q is the
transition rate matrix, so P(t) = P(0) exp(Q t). A two-state
failure/repair model converges to the steady state unavailability
lambda/(lambda+mu); with an absorbing failed state the survival
probability is exp(-lambda t) and the mean time to failure is
1/lambda. Redundant chains exit at rates scaled by the number of
working units, so a two-unit active redundancy has mean time to
failure 3/(2 lambda). All functions are deterministic, offline,
stdlib only.
"""

import math


def _require_positive(value, name):
    if not value > 0:
        raise ValueError("%s must be > 0, got %r" % (name, value))


def _require_nonneg(value, name):
    if value < 0:
        raise ValueError("%s must be >= 0, got %r" % (name, value))


def two_state_failure_probability(lam, mu, t):
    """Failure probability of a repairable two-state model at time t.

    P_failed(t) = lam/(lam+mu) * (1 - exp(-(lam+mu) t)). At t = 0 the
    model is operational; mu = 0 reduces it to the non-repairable
    failure probability 1 - exp(-lam t) only in the t small limit of
    the repair term, so use nonrepairable_probabilities for mu = 0.
    """
    _require_positive(lam, "failure rate lam")
    _require_positive(mu, "repair rate mu")
    _require_nonneg(t, "time t")
    return lam / (lam + mu) * (1.0 - math.exp(-(lam + mu) * t))


def two_state_availability(lam, mu, t):
    """(p_ok, p_failed) for the repairable two-state model at time t."""
    pf = two_state_failure_probability(lam, mu, t)
    return 1.0 - pf, pf


def steady_state_availability(lam, mu):
    """(availability, unavailability) = (mu/(lam+mu), lam/(lam+mu))."""
    _require_positive(lam, "failure rate lam")
    _require_positive(mu, "repair rate mu")
    return mu / (lam + mu), lam / (lam + mu)


def nonrepairable_probabilities(lam, t):
    """(reliability, failure probability) for an absorbing failed state.

    R(t) = exp(-lam t), F(t) = 1 - exp(-lam t).
    """
    _require_positive(lam, "failure rate lam")
    _require_nonneg(t, "time t")
    r = math.exp(-lam * t)
    return r, 1.0 - r


def mttf_exponential(lam):
    """Mean time to failure of a non-repairable unit: 1/lambda."""
    _require_positive(lam, "failure rate lam")
    return 1.0 / lam


def series_failure_rate(rates):
    """Total failure rate of a series chain: sum of the rates."""
    if not rates:
        raise ValueError("rates must be a non-empty list")
    for r in rates:
        _require_positive(r, "failure rate")
    return sum(rates)


def redundancy_mttf(n_units, lam):
    """MTTF of n-unit active redundancy, identical units, no repair.

    The chain exits state k (k working units) at rate k*lam, so the
    mean sojourn time is 1/(k*lam) and the MTTF is the harmonic sum
    1/lam * (1/n + 1/(n-1) + ... + 1). Two units give 3/(2 lam).
    """
    _require_positive(lam, "failure rate lam")
    if not isinstance(n_units, int) or n_units < 1:
        raise ValueError("n_units must be a positive integer, got %r" % (n_units,))
    return sum(1.0 / ((n_units - k) * lam) for k in range(n_units))


def k_of_n_reliability(n, k, unit_reliability):
    """Reliability that at least k of n identical units survive.

    sum_{i=k..n} C(n,i) R^i (1-R)^(n-i), with R the per-unit
    reliability at the mission time.
    """
    if not isinstance(n, int) or n < 1:
        raise ValueError("n must be a positive integer, got %r" % (n,))
    if not isinstance(k, int) or k < 1:
        raise ValueError("k must be a positive integer, got %r" % (k,))
    if k > n:
        raise ValueError("k must be <= n, got k %r > n %r" % (k, n))
    if not 0.0 <= unit_reliability <= 1.0:
        raise ValueError(
            "unit_reliability must be in [0, 1], got %r" % (unit_reliability,)
        )
    total = 0.0
    for i in range(k, n + 1):
        total += (
            math.comb(n, i)
            * (unit_reliability**i)
            * ((1.0 - unit_reliability) ** (n - i))
        )
    return total


def _mat_mul(a, b):
    n = len(a)
    m = len(b[0])
    p = len(b)
    out = [[0.0] * m for _ in range(n)]
    for i in range(n):
        for j in range(m):
            s = 0.0
            for l in range(p):
                s += a[i][l] * b[l][j]
            out[i][j] = s
    return out


def _mat_scale(a, factor):
    return [[x * factor for x in row] for row in a]


def _mat_identity(n):
    return [[1.0 if i == j else 0.0 for j in range(n)] for i in range(n)]


def _mat_exp(a, tol=1e-14):
    """Matrix exponential by scaling and squaring plus Taylor series."""
    n = len(a)
    norm = max(sum(abs(x) for x in row) for row in a)
    s = 0
    while norm > 1.0:
        a = _mat_scale(a, 0.5)
        norm *= 0.5
        s += 1
    acc = _mat_identity(n)
    term = _mat_identity(n)
    for k in range(1, 60):
        term = _mat_scale(_mat_mul(term, a), 1.0 / k)
        acc = [[acc[i][j] + term[i][j] for j in range(n)] for i in range(n)]
        if max(abs(term[i][j]) for i in range(n) for j in range(n)) < tol:
            break
    for _ in range(s):
        acc = _mat_mul(acc, acc)
    return acc


def state_probabilities(transition_rates, t, initial=None):
    """State probability vector P(t) = P(0) exp(Q t).

    transition_rates: list of rows; row i gives the rates from state i
    to every other state. Diagonal entries are ignored and rebuilt as
    the negative row sum so the chain conserves probability.
    initial: initial probability vector; defaults to state 0 certain.
    """
    if not isinstance(transition_rates, list) or not transition_rates:
        raise ValueError("transition_rates must be a non-empty list of rows")
    n = len(transition_rates)
    for row in transition_rates:
        if not isinstance(row, list) or len(row) != n:
            raise ValueError(
                "transition_rates must be square, got a row of length %r for %d states"
                % (len(row) if isinstance(row, list) else None, n)
            )
    _require_nonneg(t, "time t")
    if initial is None:
        initial = [1.0] + [0.0] * (n - 1)
    if len(initial) != n:
        raise ValueError(
            "initial must have one entry per state, got %d for %d states"
            % (len(initial), n)
        )
    for p in initial:
        if p < 0:
            raise ValueError("initial probabilities must be >= 0, got %r" % (initial,))
    if abs(sum(initial) - 1.0) > 1e-9:
        raise ValueError("initial probabilities must sum to 1, got %r" % (initial,))
    q = []
    for i, row in enumerate(transition_rates):
        qrow = []
        for j in range(n):
            if i == j:
                qrow.append(0.0)
            else:
                rate = row[j]
                _require_nonneg(rate, "transition rate")
                qrow.append(rate)
        qrow[i] = -sum(qrow[j] for j in range(n) if j != i)
        q.append(qrow)
    e = _mat_exp(_mat_scale(q, t))
    return [sum(initial[i] * e[i][j] for i in range(n)) for j in range(n)]
