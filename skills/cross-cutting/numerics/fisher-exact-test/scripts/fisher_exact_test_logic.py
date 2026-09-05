"""Fisher exact test logic (pure stdlib, deterministic).

Implements the exact Fisher test for a 2x2 contingency table with fixed
row and column margins: the hypergeometric probability of the observed
table, enumeration of every table that shares those margins, the one- and
two-tailed exact p-values, the odds ratio with the Haldane-Anscombe
+0.5 correction for zero cells, and the small-expected-count verdict
that recommends the exact test when the minimum expected cell count
under independence falls below 5. Every probability is built on
math.comb, so the module is stdlib-only, offline and deterministic.

Conventions: table [[a, b], [c, d]] with row margins a+b and c+d,
column margins a+c and b+d and total n = a+b+c+d. Under the fixed-
margin null the top-left count follows the hypergeometric
distribution: P(a) = C(a+b, a) * C(c+d, c) / C(n, a+c) with
C = math.comb.
"""

import math


def _check_nonnegative(a, b, c, d):
    """Raise ValueError when any cell of the 2x2 table is negative."""
    if min(a, b, c, d) < 0:
        raise ValueError(
            "contingency table cells must be non-negative, got (%d, %d, %d, %d)"
            % (a, b, c, d)
        )


def hypergeometric_p(a, b, c, d):
    """Probability of the observed table under the fixed-margin null.

    P(a) = C(a+b, a) * C(c+d, c) / C(n, a+c) with n = a+b+c+d, the
    hypergeometric probability of the top-left count a.
    """
    _check_nonnegative(a, b, c, d)
    return (
        math.comb(a + b, a)
        * math.comb(c + d, c)
        / math.comb(a + b + c + d, a + c)
    )


def enumerate_tables(a, b, c, d):
    """List every 2x2 table (a', b', c', d') with the same margins.

    The top-left count a' runs from max(0, (a+c) - (c+d)) to
    min(a+b, a+c); b' = (a+b) - a', c' = (a+c) - a' and
    d' = (c+d) - c' follow from the fixed margins. Returns tuples in
    increasing a' order.
    """
    _check_nonnegative(a, b, c, d)
    row1 = a + b
    row2 = c + d
    col1 = a + c
    tables = []
    for ap in range(max(0, col1 - row2), min(row1, col1) + 1):
        bp = row1 - ap
        cp = col1 - ap
        dp = row2 - cp
        tables.append((ap, bp, cp, dp))
    return tables


def odds_ratio(a, b, c, d):
    """Odds ratio (a*d)/(b*c) of the table, as a finite float.

    A zero cell makes the raw ratio 0 or infinite, so any zero cell
    triggers the Haldane-Anscombe correction: add 0.5 to every cell
    before forming the ratio.
    """
    _check_nonnegative(a, b, c, d)
    if min(a, b, c, d) == 0:
        return ((a + 0.5) * (d + 0.5)) / ((b + 0.5) * (c + 0.5))
    return (a * d) / (b * c)


def fisher_exact_p_value(a, b, c, d, alternative="two-sided"):
    """Exact Fisher p-values for the observed 2x2 table.

    Returns a dict with keys {p_obs, p_one_tail, p_two_tail,
    direction}:
    - p_obs: hypergeometric probability of the observed table.
    - direction: "low" when the odds ratio is below 1 (small top-left
      counts are the more extreme direction), "high" when it is above
      1, "symmetric" when it equals 1 and the two tails coincide.
    - p_one_tail: sum of table probabilities with a' <= a_obs in the
      low direction, with a' >= a_obs in the high direction, and the
      common sum in the symmetric case.
    - p_two_tail: sum of all table probabilities <= p_obs, the
      documented two-sided definition.

    alternative is accepted for interface compatibility ("two-sided",
    "less" or "greater"); the dict always carries the complete set of
    p-values.
    """
    _check_nonnegative(a, b, c, d)
    if alternative not in ("two-sided", "less", "greater"):
        raise ValueError(
            "alternative must be 'two-sided', 'less' or 'greater', got %r"
            % (alternative,)
        )
    p_obs = hypergeometric_p(a, b, c, d)
    or_value = odds_ratio(a, b, c, d)
    if or_value < 1.0:
        direction = "low"
    elif or_value > 1.0:
        direction = "high"
    else:
        direction = "symmetric"
    p_one_tail = 0.0
    p_two_tail = 0.0
    for ap, bp, cp, dp in enumerate_tables(a, b, c, d):
        p_table = hypergeometric_p(ap, bp, cp, dp)
        if direction == "high":
            if ap >= a:
                p_one_tail += p_table
        else:
            if ap <= a:
                p_one_tail += p_table
        if p_table <= p_obs:
            p_two_tail += p_table
    return {
        "p_obs": p_obs,
        "p_one_tail": p_one_tail,
        "p_two_tail": p_two_tail,
        "direction": direction,
    }


def small_count_verdict(a, b, c, d):
    """Smallest expected cell count and the exact-test recommendation.

    Under independence the expected count of each cell is
    row_total * col_total / n. When the minimum is below 5 the
    large-sample approximation is unreliable and the verdict is
    "exact-test-recommended", otherwise "chi-square-adequate". Raises
    ValueError when the table total n is not positive.
    """
    _check_nonnegative(a, b, c, d)
    n = a + b + c + d
    if n <= 0:
        raise ValueError("table total n must be positive, got %d" % n)
    row1 = a + b
    row2 = c + d
    col1 = a + c
    col2 = b + d
    min_expected = min(row1 * col1, row1 * col2, row2 * col1, row2 * col2) / n
    if min_expected < 5.0:
        return {"min_expected": min_expected, "verdict": "exact-test-recommended"}
    return {"min_expected": min_expected, "verdict": "chi-square-adequate"}
