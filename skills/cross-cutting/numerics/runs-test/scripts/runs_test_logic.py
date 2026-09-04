"""runs_test_logic.py

Wald-Wolfowitz runs test on a binary (+1 / -1) sign sequence, pure
stdlib. Counts the runs of identical signs, computes the expected
number of runs and its variance under the null hypothesis of
randomness from the two sign counts, forms the standard normal z
statistic, and returns the randomness verdict against a two-sided
normal critical value.
"""

import math

# Two-sided 95 percent normal critical value.
Z_CRIT_95_TWOTAIL = 1.96

PLUS = 1
MINUS = -1


def count_runs(signs):
    """Return the number of maximal consecutive same-sign blocks.

    A run is a maximal consecutive block of one sign. Raises
    ValueError when fewer than 4 signs are given, when any sign is
    not +1 or -1, or when every sign is the same (a single-sign
    sequence has no runs to test).
    """
    n = len(signs)
    if n < 4:
        raise ValueError("at least 4 signs are required")
    for s in signs:
        if s not in (PLUS, MINUS):
            raise ValueError("each sign must be +1 or -1")
    if all(s == PLUS for s in signs) or all(s == MINUS for s in signs):
        raise ValueError("sequence must contain both signs")
    runs = 1
    for i in range(1, n):
        if signs[i] != signs[i - 1]:
            runs += 1
    return runs


def expected_runs(n1, n2):
    """Return E(R) = 1 + 2 n1 n2 / (n1 + n2) under the null.

    Raises ValueError when either sign count is not positive.
    """
    if n1 <= 0 or n2 <= 0:
        raise ValueError("n1 and n2 must both be positive")
    return 1.0 + 2.0 * n1 * n2 / (n1 + n2)


def runs_variance(n1, n2):
    """Return Var(R) = 2 n1 n2 (2 n1 n2 - n) / (n^2 (n - 1)).

    Raises ValueError when either sign count is not positive or when
    the total n = n1 + n2 is below 4.
    """
    if n1 <= 0 or n2 <= 0:
        raise ValueError("n1 and n2 must both be positive")
    n = n1 + n2
    if n < 4:
        raise ValueError("total count n1 + n2 must be at least 4")
    return 2.0 * n1 * n2 * (2.0 * n1 * n2 - n) / (n * n * (n - 1.0))


def runs_test(signs, z_crit=Z_CRIT_95_TWOTAIL):
    """Run the Wald-Wolfowitz runs test and return the result dict.

    Keys: n1, n2, runs, expected, variance, sd, z, verdict. Verdict
    is REJECT (evidence of non-random ordering) when abs(z) >=
    z_crit, else FAIL_TO_REJECT. Raises ValueError for the same
    non-physical inputs as count_runs and runs_variance.
    """
    runs = count_runs(signs)
    n1 = sum(1 for s in signs if s == PLUS)
    n2 = len(signs) - n1
    expected = expected_runs(n1, n2)
    variance = runs_variance(n1, n2)
    sd = math.sqrt(variance)
    z = (runs - expected) / sd
    verdict = "REJECT" if abs(z) >= z_crit else "FAIL_TO_REJECT"
    return {
        "n1": n1,
        "n2": n2,
        "runs": runs,
        "expected": expected,
        "variance": variance,
        "sd": sd,
        "z": z,
        "verdict": verdict,
    }
