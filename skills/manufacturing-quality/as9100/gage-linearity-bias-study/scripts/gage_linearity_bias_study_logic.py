"""Gage linearity and bias study logic: bias per reference level and linearity regression.

Pure stdlib, deterministic. Runs the gage bias and linearity study at the
conceptual level: from reference-level masters and the measured biases at
each level, compute the per-level bias and the overall mean bias, fit the
least-squares regression of bias on the reference value (slope, intercept,
residual sum of squares, R-squared), test the mean bias for significance
against the two-sided 95 percent t critical at the study degrees of
freedom, and apply the percent-of-reference acceptability band per level.

Conventions: references in mm as strictly increasing unique values; one
bias value per reference level (bias = observed - reference, signed mm);
n = number of reference levels. Bias significance tests whether the mean
bias across levels is distinguishable from zero relative to the spread of
the per-level biases (AIAG gage study practice, summary-only).
"""

T_CRIT_95_TWOTAIL = {
    1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447,
    7: 2.365, 8: 2.306, 9: 2.262, 10: 2.228, 11: 2.201, 12: 2.179,
    13: 2.160, 14: 2.145, 15: 2.131, 16: 2.120, 17: 2.110, 18: 2.101,
    19: 2.093, 20: 2.086,
}
T_CRIT_LARGE_DF = 1.96  # normal approximation for df > 20
ACCEPTANCE_PCT_BAND = 10.0  # percent of reference; per-level |bias|/reference bound


def _validate_reference_biases(references, biases):
    """Validate the paired reference and bias arrays.

    Raises ValueError on length mismatch, fewer than 3 levels,
    references that are not strictly increasing, or any reference <= 0.
    """
    if not isinstance(references, (list, tuple)) or not isinstance(
        biases, (list, tuple)
    ):
        raise ValueError("references and biases must be lists or tuples")
    if len(references) != len(biases):
        raise ValueError("references and biases must have the same length")
    if len(references) < 3:
        raise ValueError("at least 3 reference levels are required")
    if any(r <= 0 for r in references):
        raise ValueError("reference values must be positive")
    if any(b <= references[i - 1] for i, b in enumerate(references[1:], start=1)):
        raise ValueError("reference values must be strictly increasing")
    return len(references)


def per_level_bias(references, biases):
    """Return per-level bias dicts {reference, bias, bias_pct_of_reference}.

    bias_pct_of_reference = 100 * bias / reference. Raises ValueError per
    _validate_reference_biases.
    """
    n = _validate_reference_biases(references, biases)
    rows = []
    for i in range(n):
        rows.append(
            {
                "reference": references[i],
                "bias": biases[i],
                "bias_pct_of_reference": 100.0 * biases[i] / references[i],
            }
        )
    return rows


def mean_bias(biases):
    """Return the arithmetic mean of the bias values. ValueError if empty."""
    if not isinstance(biases, (list, tuple)) or len(biases) == 0:
        raise ValueError("biases must be a non-empty list")
    return sum(biases) / len(biases)


def _bias_sst(biases):
    """Return the sum of squared deviations of biases about their mean."""
    bar = mean_bias(biases)
    return sum((b - bar) ** 2 for b in biases)


def linearity_regression(references, biases):
    """Fit bias = intercept + slope * reference by least squares.

    Returns dict {slope, intercept, sse, r_squared, n, xbar, bias_bar}
    with sse = sum (bias - predicted)^2 and r2 = 1 - sse/sst. Raises
    ValueError per _validate_reference_biases.
    """
    n = _validate_reference_biases(references, biases)
    xbar = sum(references) / n
    bias_bar = sum(biases) / n
    sxx = sum((x - xbar) ** 2 for x in references)
    sxy = sum(
        (x - xbar) * (b - bias_bar) for x, b in zip(references, biases)
    )
    slope = sxy / sxx
    intercept = bias_bar - slope * xbar
    sse = sum(
        (b - (intercept + slope * x)) ** 2
        for x, b in zip(references, biases)
    )
    sst = _bias_sst(biases)
    if sst == 0.0:
        # Zero bias variation: the best fit is horizontal at the mean
        # bias with zero residuals; R-squared is 1.0 by convention.
        slope = 0.0
        intercept = bias_bar
        sse = 0.0
        r_squared = 1.0
    else:
        r_squared = 1.0 - sse / sst
    return {
        "slope": slope,
        "intercept": intercept,
        "sse": sse,
        "r_squared": r_squared,
        "n": n,
        "xbar": xbar,
        "bias_bar": bias_bar,
    }


def bias_significance(biases):
    """Test the mean bias against the two-sided 95 percent t critical.

    t = bias_bar / (s / sqrt(n)) with s = sqrt(sst / (n - 1)), df = n - 1
    and t_crit from the table (1.96 for df > 20); significant = |t| >=
    t_crit. A zero-dispersion sample (s = 0) makes the t statistic
    degenerate: the study reports t_stat 0.0 and significant False, the
    convention that identical per-level biases carry no spread evidence.
    Raises ValueError for fewer than 3 bias values.
    """
    if not isinstance(biases, (list, tuple)) or len(biases) < 3:
        raise ValueError("at least 3 bias values are required")
    n = len(biases)
    bias_bar = sum(biases) / n
    sst = sum((b - bias_bar) ** 2 for b in biases)
    s = (sst / (n - 1)) ** 0.5
    df = n - 1
    t_crit = T_CRIT_95_TWOTAIL.get(df, T_CRIT_LARGE_DF)
    if s == 0.0:
        t_stat = 0.0
    else:
        t_stat = bias_bar / (s / n ** 0.5)
    return {
        "t_stat": t_stat,
        "t_crit": t_crit,
        "df": df,
        "significant": abs(t_stat) >= t_crit,
    }


def gage_bias_linearity_study(references, biases):
    """Run the full gage bias and linearity study.

    Returns dict with per_level (per_level_bias rows), mean_bias,
    regression (linearity_regression stats), significance
    (bias_significance verdict), worst_bias_pct, worst_reference,
    per_level_acceptable (all |bias_pct| <= ACCEPTANCE_PCT_BAND) and
    overall ACCEPT when the bias is not significant and every level is
    inside the band, else REVIEW. Raises ValueError per
    _validate_reference_biases (and bias_significance).
    """
    _validate_reference_biases(references, biases)
    rows = per_level_bias(references, biases)
    bar = mean_bias(biases)
    reg = linearity_regression(references, biases)
    sig = bias_significance(biases)
    worst_row = max(rows, key=lambda r: abs(r["bias_pct_of_reference"]))
    per_level_acceptable = all(
        abs(r["bias_pct_of_reference"]) <= ACCEPTANCE_PCT_BAND for r in rows
    )
    overall = (
        "ACCEPT"
        if (not sig["significant"] and per_level_acceptable)
        else "REVIEW"
    )
    return {
        "per_level": rows,
        "mean_bias": bar,
        "regression": reg,
        "significance": sig,
        "worst_bias_pct": worst_row["bias_pct_of_reference"],
        "worst_reference": worst_row["reference"],
        "per_level_acceptable": per_level_acceptable,
        "overall": overall,
    }
