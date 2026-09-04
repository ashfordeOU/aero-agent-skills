"""Individuals (I) and moving range (MR) control chart logic, pure stdlib.

Use when a process yields ONE measurement per lot or subgroup (destructive
testing, single unit per batch, bond or coating lot) so subgroup charts do
not apply. The module builds the I-MR chart from the time-ordered individual
measurements: moving ranges |x_i - x_{i-1}| between successive values, the
average moving range, the individuals limits from the mean plus and minus
E2 * mr_bar (E2 = 2.66 for n = 1), the process sigma estimate mr_bar / d2
(d2 = 1.128 for n = 2 moving ranges), and the moving range upper limit
3.267 * mr_bar (lower limit 0). Out-of-limit points are flagged by index and
the lot-to-lot stability verdict returned.
"""

# I-MR chart module constants (n = 1 individuals).
E2 = 2.66          # Individuals chart constant: limits from the average moving range.
D2_N1 = 1.128      # d2 constant for n = 2 moving ranges: sigma estimate divisor.
D3_MR_UCL = 3.267  # Moving range chart upper limit factor (lower limit is 0).


def mean(values):
    """Arithmetic mean of a non-empty numeric sequence."""
    if len(values) == 0:
        raise ValueError("mean requires at least one value")
    return sum(values) / len(values)


def moving_ranges(values):
    """Moving ranges |x_i - x_{i-1}| for i >= 1 over a time-ordered series.

    N individual measurements produce N-1 moving ranges. Raises ValueError
    when the series holds fewer than 2 values.
    """
    if len(values) < 2:
        raise ValueError("moving ranges require at least 2 values")
    return [abs(values[i] - values[i - 1]) for i in range(1, len(values))]


def individuals_limits(values):
    """Central line and limits for the individuals (X) chart.

    Returns dict {mean, mr_bar, sigma_hat, UCL, LCL} with:
      mean     = mean of the individual measurements
      mr_bar   = mean of the moving ranges
      sigma_hat = mr_bar / D2_N1 (process sigma estimate)
      UCL      = mean + E2 * mr_bar
      LCL      = mean - E2 * mr_bar
    Raises ValueError when the series holds fewer than 2 values.
    """
    if len(values) < 2:
        raise ValueError("individuals limits require at least 2 values")
    x_bar = mean(values)
    mr_bar = mean(moving_ranges(values))
    sigma_hat = mr_bar / D2_N1
    return {
        "mean": x_bar,
        "mr_bar": mr_bar,
        "sigma_hat": sigma_hat,
        "UCL": x_bar + E2 * mr_bar,
        "LCL": x_bar - E2 * mr_bar,
    }


def moving_range_limits(values):
    """Limits for the moving range (MR) chart from the average moving range.

    Returns dict {mr_bar, UCL} with UCL = D3_MR_UCL * mr_bar; the MR chart
    lower limit is 0. Raises ValueError when the series holds fewer than 2
    values.
    """
    if len(values) < 2:
        raise ValueError("moving range limits require at least 2 values")
    mr_bar = mean(moving_ranges(values))
    return {"mr_bar": mr_bar, "UCL": D3_MR_UCL * mr_bar}


def flag_points(values, ucl, lcl):
    """Indices whose value lies outside the interval [lcl, ucl].

    The interval is inclusive: a value exactly at a limit is not flagged.
    Raises ValueError for an empty values list.
    """
    if len(values) == 0:
        raise ValueError("flagging requires at least one value")
    return [i for i, v in enumerate(values) if v < lcl or v > ucl]


def stability_verdict(individual_flags, mr_flags):
    """In-control verdict when both flag lists are empty, else out-of-control."""
    if len(individual_flags) == 0 and len(mr_flags) == 0:
        return "in-control"
    return "out-of-control"


def imr_summary(values):
    """Full I-MR chart summary for a single-measurement process.

    Returns dict {mean, mr_bar, sigma_hat, x_ucl, x_lcl, mr_ucl,
    flagged_individuals, flagged_moving_ranges, verdict}. Flagged individual
    indices point into the original measurement series; flagged moving range
    indices point into the moving-range list, where index i spans original
    measurements i and i + 1. Raises ValueError for fewer than 2 values.
    """
    ind = individuals_limits(values)
    mr = moving_range_limits(values)
    mrs = moving_ranges(values)
    flagged_individuals = flag_points(values, ind["UCL"], ind["LCL"])
    flagged_moving_ranges = flag_points(mrs, mr["UCL"], 0.0)
    return {
        "mean": ind["mean"],
        "mr_bar": ind["mr_bar"],
        "sigma_hat": ind["sigma_hat"],
        "x_ucl": ind["UCL"],
        "x_lcl": ind["LCL"],
        "mr_ucl": mr["UCL"],
        "flagged_individuals": flagged_individuals,
        "flagged_moving_ranges": flagged_moving_ranges,
        "verdict": stability_verdict(flagged_individuals, flagged_moving_ranges),
    }
