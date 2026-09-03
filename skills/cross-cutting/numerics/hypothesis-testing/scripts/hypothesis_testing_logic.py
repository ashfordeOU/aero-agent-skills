"""Hypothesis testing for aerospace data comparisons (pure stdlib, deterministic).

Implements the standard null-hypothesis significance tests used to compare
measured data sets: one-sample and two-sample Student t tests (pooled and
Welch), the paired t test, the two-variance F test, the chi-square test of
independence, and the one-way ANOVA F test. Every p-value is computed from
this module's own regularized incomplete beta and regularized lower
incomplete gamma implementations (Lentz continued fraction and series),
so no external statistics package is involved.

All tests return a dict with the test statistic, degrees of freedom, the
p-value, and a verdict ("reject-null" when p <= alpha, else
"fail-to-reject") against the stated significance level.

Degenerate cases (documented):
- Two-sample t test with zero variance in BOTH samples: verdict from the
  means alone, stat 0.0 and p 1.0 when the means are equal, stat inf and
  p 0.0 when they differ.
- Paired t test with constant differences: verdict from the mean
  difference alone, stat 0.0 and p 1.0 when the mean difference is zero,
  stat inf and p 0.0 otherwise (a constant +0.1 shift rejects).
- ANOVA with zero within-group variance: verdict from the between-group
  sums of squares, stat 0.0 and p 1.0 when all group means are equal,
  stat inf and p 0.0 otherwise.
"""

import math

# Module constants (Lentz and series convergence controls).
ITMAX = 200
EPS = 3e-12
FPMIN = 1e-300
ALPHA = 0.05

VERDICT_REJECT = "reject-null"
VERDICT_FAIL = "fail-to-reject"


def _check_finite(seq, name):
    for v in seq:
        if not math.isfinite(float(v)):
            raise ValueError("%s contains a non-finite value" % name)


def _check_alpha(alpha):
    if not math.isfinite(alpha) or not (0.0 < alpha < 1.0):
        raise ValueError("alpha must be in (0, 1), got %r" % (alpha,))


def _mean(values):
    return sum(values) / len(values)


def _variance(values, ddof):
    n = len(values)
    m = _mean(values)
    return sum((v - m) ** 2 for v in values) / (n - ddof)


def _std(values, ddof):
    return math.sqrt(_variance(values, ddof))


def _verdict(p, alpha):
    return VERDICT_REJECT if p <= alpha else VERDICT_FAIL


# ---------------------------------------------------------------------------
# Special functions: regularized incomplete beta and gamma
# ---------------------------------------------------------------------------

def _betacf(a, b, x):
    """Continued fraction for the incomplete beta (Lentz algorithm)."""
    qab = a + b
    qap = a + 1.0
    qam = a - 1.0
    c = 1.0
    d = 1.0 - qab * x / qap
    if abs(d) < FPMIN:
        d = FPMIN
    d = 1.0 / d
    h = d
    for m in range(1, ITMAX + 1):
        m2 = 2 * m
        aa = m * (b - m) * x / ((qam + m2) * (a + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        h *= d * c
        aa = -(a + m) * (qab + m) * x / ((a + m2) * (qap + m2))
        d = 1.0 + aa * d
        if abs(d) < FPMIN:
            d = FPMIN
        c = 1.0 + aa / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h


def regularized_incomplete_beta(a, b, x):
    """Regularized incomplete beta I_x(a, b) on [0, 1].

    Uses the Lentz continued fraction with the standard symmetry
    I_x(a, b) = 1 - I_(1-x)(b, a) to stay in the convergent regime.
    Raises ValueError for a <= 0, b <= 0, or x outside [0, 1].
    """
    if a <= 0.0 or b <= 0.0:
        raise ValueError("beta shape arguments must be positive, got a=%r b=%r" % (a, b))
    if x < 0.0 or x > 1.0:
        raise ValueError("beta argument x must lie in [0, 1], got %r" % (x,))
    if x == 0.0:
        return 0.0
    if x == 1.0:
        return 1.0
    if x < (a + 1.0) / (a + b + 2.0):
        return _beta_terms(a, b, x)
    return 1.0 - _beta_terms(b, a, 1.0 - x)


def _beta_terms(a, b, x):
    """x^a (1-x)^b / (a B(a, b)) times the continued fraction."""
    bt = math.exp(
        math.lgamma(a + b) - math.lgamma(a) - math.lgamma(b)
        + a * math.log(x) + b * math.log1p(-x)
    )
    ans = bt * _betacf(a, b, x) / a
    if ans < 0.0:
        return 0.0
    if ans > 1.0:
        return 1.0
    return ans


def _gamma_series(a, x):
    """Lower incomplete gamma series term for x < a + 1."""
    ap = a
    total = 1.0 / a
    term = total
    for _ in range(1, ITMAX + 1):
        ap += 1.0
        term *= x / ap
        total += term
        if abs(term) < abs(total) * EPS:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_cf(a, x):
    """Complement Q(a, x) = 1 - P(a, x) via continued fraction (x >= a + 1)."""
    b = x + 1.0 - a
    c = 1.0 / FPMIN
    d = 1.0 / b if b != 0.0 else FPMIN
    h = d
    for i in range(1, ITMAX + 1):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < FPMIN:
            d = FPMIN
        c = b + an / c
        if abs(c) < FPMIN:
            c = FPMIN
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < EPS:
            break
    return h * math.exp(-x + a * math.log(x) - math.lgamma(a))


def regularized_lower_incomplete_gamma(a, x):
    """Regularized lower incomplete gamma P(a, x).

    Series for x < a + 1, continued fraction for the complement
    otherwise; normalized with math.lgamma. Raises ValueError for
    a <= 0 or x < 0.
    """
    if a <= 0.0:
        raise ValueError("gamma shape a must be positive, got %r" % (a,))
    if x < 0.0:
        raise ValueError("gamma argument x must be >= 0, got %r" % (x,))
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gamma_series(a, x)
    return 1.0 - _gamma_cf(a, x)


# ---------------------------------------------------------------------------
# CDFs built on the special functions
# ---------------------------------------------------------------------------

def t_cdf(t, df, tails="two-sided"):
    """p-value for a Student t statistic.

    Two-tailed: I_(df/(df + t^2))(df/2, 1/2) on |t| (the standard form).
    One-tailed halves the two-tailed p. Raises ValueError for df <= 0.
    """
    if df <= 0.0:
        raise ValueError("degrees of freedom must be positive, got %r" % (df,))
    if tails not in ("two-sided", "one-sided"):
        raise ValueError("tails must be 'two-sided' or 'one-sided', got %r" % (tails,))
    x = df / (df + t * t)
    p = regularized_incomplete_beta(df / 2.0, 0.5, x)
    if tails == "one-sided":
        return p / 2.0
    return p


def f_cdf(f, df1, df2):
    """Upper-tail p-value P(F > f) for an F(df1, df2) statistic.

    Computed as I_(df2/(df2 + df1 f))(df2/2, df1/2), the standard
    right-tail beta form. Raises ValueError for f < 0 or df <= 0.
    """
    if f < 0.0:
        raise ValueError("F statistic must be >= 0, got %r" % (f,))
    if df1 <= 0.0 or df2 <= 0.0:
        raise ValueError("F degrees of freedom must be positive")
    x = df2 / (df2 + df1 * f)
    return regularized_incomplete_beta(df2 / 2.0, df1 / 2.0, x)


def chi2_cdf(x, df):
    """Cumulative P(chi2 <= x) = P(df/2, x/2) for df degrees of freedom."""
    if x < 0.0:
        raise ValueError("chi-square argument must be >= 0, got %r" % (x,))
    if df <= 0.0:
        raise ValueError("chi-square degrees of freedom must be positive")
    return regularized_lower_incomplete_gamma(df / 2.0, x / 2.0)


# ---------------------------------------------------------------------------
# Significance tests
# ---------------------------------------------------------------------------

def t_test_1samp(data, mu0, alternative="two-sided", alpha=ALPHA):
    """One-sample t test of mean(data) against mu0.

    stat = (mean - mu0) / (s / sqrt(n)), df = n - 1. Raises ValueError
    for fewer than 2 points, zero sample variance, non-finite values, or
    alpha outside (0, 1).
    """
    _check_alpha(alpha)
    data = [float(v) for v in data]
    if len(data) < 2:
        raise ValueError("one-sample t test needs at least 2 points")
    _check_finite(data, "data")
    if not math.isfinite(float(mu0)):
        raise ValueError("mu0 must be finite")
    if alternative not in ("two-sided", "greater", "less"):
        raise ValueError("alternative must be 'two-sided', 'greater' or 'less'")
    n = len(data)
    m = _mean(data)
    s = _std(data, 1)
    if s == 0.0:
        raise ValueError("one-sample t test needs non-zero sample variance")
    df = n - 1
    stat = (m - float(mu0)) / (s / math.sqrt(n))
    p = t_cdf(stat, df)
    if alternative == "greater":
        p = p / 2.0 if stat >= 0.0 else 1.0 - p / 2.0
    elif alternative == "less":
        p = 1.0 - p / 2.0 if stat >= 0.0 else p / 2.0
    return {"stat": stat, "df": df, "p": p, "verdict": _verdict(p, alpha)}


def t_test_2samp(a, b, equal_var=True, alpha=ALPHA):
    """Two-sample Student t test, pooled (equal_var True) or Welch.

    Pooled s_p^2 = ((n1-1)s1^2 + (n2-1)s2^2)/(n1 + n2 - 2) with df
    n1 + n2 - 2; Welch uses the Satterthwaite df. Both variances zero is
    allowed with the documented degenerate verdict. Raises ValueError for
    groups under 2 points or non-finite values.
    """
    _check_alpha(alpha)
    a = [float(v) for v in a]
    b = [float(v) for v in b]
    if len(a) < 2 or len(b) < 2:
        raise ValueError("two-sample t test needs at least 2 points per group")
    _check_finite(a, "group a")
    _check_finite(b, "group b")
    n1, n2 = len(a), len(b)
    m1, m2 = _mean(a), _mean(b)
    v1, v2 = _variance(a, 1), _variance(b, 1)
    df = n1 + n2 - 2
    if v1 == 0.0 and v2 == 0.0:
        # Degenerate: no variance to estimate, verdict from the means.
        if m1 == m2:
            return {"stat": 0.0, "df": df, "p": 1.0,
                    "verdict": VERDICT_FAIL}
        return {"stat": float("inf"), "df": df, "p": 0.0,
                "verdict": VERDICT_REJECT}
    if equal_var:
        sp2 = ((n1 - 1) * v1 + (n2 - 1) * v2) / df
        stat = (m1 - m2) / math.sqrt(sp2 * (1.0 / n1 + 1.0 / n2))
    else:
        se2 = v1 / n1 + v2 / n2
        stat = (m1 - m2) / math.sqrt(se2)
        df = se2 ** 2 / ((v1 / n1) ** 2 / (n1 - 1) + (v2 / n2) ** 2 / (n2 - 1))
    p = t_cdf(stat, df)
    return {"stat": stat, "df": df, "p": p, "verdict": _verdict(p, alpha)}


def t_test_paired(a, b, alpha=ALPHA):
    """Paired t test on the differences d = a - b against 0.

    One-sample t on d with df = n - 1. Constant differences give the
    documented degenerate verdict (stat inf, p 0.0 when the mean
    difference is non-zero, stat 0.0 and p 1.0 otherwise). Raises
    ValueError on length mismatch, fewer than 2 pairs, or non-finite
    values.
    """
    _check_alpha(alpha)
    a = [float(v) for v in a]
    b = [float(v) for v in b]
    if len(a) != len(b):
        raise ValueError("paired t test needs equal-length samples, got %d and %d"
                         % (len(a), len(b)))
    if len(a) < 2:
        raise ValueError("paired t test needs at least 2 pairs")
    _check_finite(a, "group a")
    _check_finite(b, "group b")
    d = [x - y for x, y in zip(a, b)]
    n = len(d)
    m = _mean(d)
    s = _std(d, 1)
    df = n - 1
    if s == 0.0:
        if m == 0.0:
            return {"stat": 0.0, "df": df, "p": 1.0, "verdict": VERDICT_FAIL}
        return {"stat": float("inf"), "df": df, "p": 0.0,
                "verdict": VERDICT_REJECT}
    stat = m / (s / math.sqrt(n))
    p = t_cdf(stat, df)
    return {"stat": stat, "df": df, "p": p, "verdict": _verdict(p, alpha)}


def f_test_variances(a, b, alpha=ALPHA):
    """Two-variance F test: stat = s1^2/s2^2 with the larger variance on top.

    Two-sided p = 2 * min(F_cdf, 1 - F_cdf) capped at 1.0, where F_cdf is
    the upper tail from f_cdf. Raises ValueError for groups under 3
    points, a zero sample variance (undefined ratio), or non-finite
    values.
    """
    _check_alpha(alpha)
    a = [float(v) for v in a]
    b = [float(v) for v in b]
    if len(a) < 3 or len(b) < 3:
        raise ValueError("F test needs at least 3 points per group")
    _check_finite(a, "group a")
    _check_finite(b, "group b")
    n1, n2 = len(a), len(b)
    v1, v2 = _variance(a, 1), _variance(b, 1)
    if v1 == 0.0 or v2 == 0.0:
        raise ValueError("F test is undefined for a zero sample variance")
    if v1 >= v2:
        stat, df1, df2 = v1 / v2, n1 - 1, n2 - 1
    else:
        stat, df1, df2 = v2 / v1, n2 - 1, n1 - 1
    tail = f_cdf(stat, df1, df2)
    p = 2.0 * min(tail, 1.0 - tail)
    if p > 1.0:
        p = 1.0
    return {"stat": stat, "df1": df1, "df2": df2, "p": p,
            "verdict": _verdict(p, alpha)}


def chi2_independence(table, alpha=ALPHA):
    """Chi-square test of independence on a contingency table.

    stat = sum (O - E)^2 / E over rows x cols with df = (r-1)(c-1) and
    expected counts E = row_total * col_total / n. Returns the expected
    table alongside stat, df, p and verdict. Raises ValueError for a
    non-rectangular table, a zero row or column total, any expected count
    below 1 (test not valid), negative or non-finite entries.
    """
    _check_alpha(alpha)
    rows = [list(map(float, row)) for row in table]
    if len(rows) < 2:
        raise ValueError("chi-square test needs at least 2 rows")
    ncols = len(rows[0])
    if ncols < 2:
        raise ValueError("chi-square test needs at least 2 columns")
    for row in rows:
        if len(row) != ncols:
            raise ValueError("contingency table must be rectangular")
        _check_finite(row, "table")
        for v in row:
            if v < 0.0:
                raise ValueError("table entries must be non-negative")
    row_totals = [sum(row) for row in rows]
    col_totals = [sum(rows[i][j] for i in range(len(rows))) for j in range(ncols)]
    if any(t == 0.0 for t in row_totals) or any(t == 0.0 for t in col_totals):
        raise ValueError("contingency table has a zero row or column total")
    n = sum(row_totals)
    expected = [[row_totals[i] * col_totals[j] / n
                 for j in range(ncols)] for i in range(len(rows))]
    for row in expected:
        for e in row:
            if e < 1.0:
                raise ValueError("chi-square test invalid: expected count below 1")
    stat = 0.0
    for i in range(len(rows)):
        for j in range(ncols):
            stat += (rows[i][j] - expected[i][j]) ** 2 / expected[i][j]
    df = (len(rows) - 1) * (ncols - 1)
    p = 1.0 - chi2_cdf(stat, df)
    return {"stat": stat, "df": df, "p": p, "verdict": _verdict(p, alpha),
            "expected": expected}


def anova_oneway(groups, alpha=ALPHA):
    """One-way ANOVA F test across k groups.

    Between and within sums of squares with df_between = k - 1 and
    df_within = N - k; p is the upper tail f_cdf(F, df_between,
    df_within). Zero within-group variance gives the documented
    degenerate verdict. Raises ValueError for fewer than 2 groups, any
    group under 3 points, or non-finite values.
    """
    _check_alpha(alpha)
    groups = [[float(v) for v in g] for g in groups]
    if len(groups) < 2:
        raise ValueError("ANOVA needs at least 2 groups")
    for g in groups:
        if len(g) < 3:
            raise ValueError("ANOVA needs at least 3 points per group")
        _check_finite(g, "group")
    k = len(groups)
    sizes = [len(g) for g in groups]
    means = [_mean(g) for g in groups]
    n_total = sum(sizes)
    grand = sum(m * sz for m, sz in zip(means, sizes)) / n_total
    ss_between = sum(sz * (m - grand) ** 2 for m, sz in zip(means, sizes))
    ss_within = sum((v - m) ** 2 for g, m in zip(groups, means) for v in g)
    df_between = k - 1
    df_within = n_total - k
    if ss_within == 0.0:
        if ss_between == 0.0:
            return {"stat": 0.0, "df_between": df_between,
                    "df_within": df_within, "p": 1.0,
                    "verdict": VERDICT_FAIL}
        return {"stat": float("inf"), "df_between": df_between,
                "df_within": df_within, "p": 0.0,
                "verdict": VERDICT_REJECT}
    stat = (ss_between / df_between) / (ss_within / df_within)
    p = f_cdf(stat, df_between, df_within)
    return {"stat": stat, "df_between": df_between, "df_within": df_within,
            "p": p, "verdict": _verdict(p, alpha)}


def summarize(results, alpha=ALPHA):
    """Condense a dict of test result dicts into rows plus a combined note.

    Each row carries the test name, statistic, degrees of freedom,
    p-value and verdict; the note lists the tests whose verdict is
    reject-null at alpha.
    """
    _check_alpha(alpha)
    rows = []
    rejecting = []
    for name, res in results.items():
        if "df1" in res:
            df_text = "%s,%s" % (res["df1"], res["df2"])
        else:
            df_text = str(res.get("df", ""))
        rows.append({"test": name, "stat": res["stat"], "df": df_text,
                     "p": res["p"], "verdict": res["verdict"]})
        if res["verdict"] == VERDICT_REJECT:
            rejecting.append(name)
    if rejecting:
        note = "tests rejecting the null at alpha %g: %s" % (alpha,
                                                             ", ".join(rejecting))
    else:
        note = "no test rejects the null at alpha %g" % (alpha,)
    return {"rows": rows, "rejecting": rejecting, "note": note}
