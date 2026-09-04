"""Attribute control charts for aerospace conformance and defect count data.

Pure stdlib implementation of the four attribute control charts:

- p-chart: fraction nonconforming of subgroups at constant sample size.
- np-chart: count nonconforming at constant sample size.
- c-chart: defect counts per constant inspection area.
- u-chart: defect counts per unit with variable inspection area.

Every chart derives its own grand average from the raw subgroup
statistics. Control limits are the 3-sigma binomial (p, np) or Poisson
(c, u) normal-approximation limits, and the lower control limit is
floored at zero. Each chart returns the central line, the control
limits, the flagged subgroup indices (statistic strictly outside
[LCL, UCL]) and the shared stability verdict.
"""

import math

# 3-sigma control limit factor for the attribute normal approximation.
SIGMA_FACTOR = 3.0


def attribute_verdict(any_flags):
    """Return the shared stability verdict for the attribute charts.

    any_flags is truthy when at least one subgroup statistic falls
    outside its control limits. Returns "in-control" when no subgroup
    is flagged, otherwise "out-of-control".
    """
    if any_flags:
        return "out-of-control"
    return "in-control"


def _validate_p_counts(nonconforming_counts, sample_size):
    """Reject non-physical p/np inputs with ValueError."""
    if len(nonconforming_counts) == 0:
        raise ValueError("nonconforming_counts must not be empty")
    if sample_size <= 0:
        raise ValueError("sample_size must be positive")
    for count in nonconforming_counts:
        if count < 0:
            raise ValueError("nonconforming count must not be negative")
        if count > sample_size:
            raise ValueError(
                "nonconforming count cannot exceed the sample size")


def p_chart(nonconforming_counts, sample_size):
    """p-chart for fraction nonconforming at constant sample size.

    pbar = sum(counts) / (len(counts) * sample_size), sigma_p =
    sqrt(pbar * (1 - pbar) / sample_size), UCL/LCL = pbar +/- 3
    sigma_p with LCL floored at 0. A subgroup i is flagged when its
    fraction counts[i] / sample_size lies outside [LCL, UCL].

    Returns a dict with keys pbar, sigma_p, UCL, LCL,
    flagged_subgroups, verdict.
    """
    _validate_p_counts(nonconforming_counts, sample_size)
    n_groups = len(nonconforming_counts)
    pbar = float(sum(nonconforming_counts)) / (n_groups * sample_size)
    sigma_p = math.sqrt(pbar * (1.0 - pbar) / sample_size)
    ucl = pbar + SIGMA_FACTOR * sigma_p
    lcl = max(0.0, pbar - SIGMA_FACTOR * sigma_p)
    flagged = [
        i for i, count in enumerate(nonconforming_counts)
        if (count / sample_size) < lcl or (count / sample_size) > ucl
    ]
    return {
        "pbar": pbar,
        "sigma_p": sigma_p,
        "UCL": ucl,
        "LCL": lcl,
        "flagged_subgroups": flagged,
        "verdict": attribute_verdict(flagged),
    }


def np_chart(nonconforming_counts, sample_size):
    """np-chart for count nonconforming at constant sample size.

    Reuses the p-chart summary: npbar = pbar * sample_size and
    UCL/LCL = sample_size * (pbar +/- 3 sigma_p), LCL floored at 0
    through the p-chart floor, so the np limits are exactly
    sample_size times the p limits. A subgroup i is flagged when the
    raw count counts[i] lies outside [LCL, UCL], which matches the
    p-chart fraction flagging.

    Returns a dict with keys npbar, UCL, LCL, flagged_subgroups,
    verdict.
    """
    summary = p_chart(nonconforming_counts, sample_size)
    npbar = summary["pbar"] * sample_size
    ucl = sample_size * summary["UCL"]
    lcl = sample_size * summary["LCL"]
    flagged = [
        i for i, count in enumerate(nonconforming_counts)
        if count < lcl or count > ucl
    ]
    return {
        "npbar": npbar,
        "UCL": ucl,
        "LCL": lcl,
        "flagged_subgroups": flagged,
        "verdict": attribute_verdict(flagged),
    }


def c_chart(defect_counts):
    """c-chart for defect counts per constant inspection area.

    cbar = mean(counts), sigma_c = sqrt(cbar), UCL/LCL = cbar +/- 3
    sigma_c with LCL floored at 0. A subgroup i is flagged when its
    raw defect count lies outside [LCL, UCL].

    Returns a dict with keys cbar, sigma_c, UCL, LCL,
    flagged_subgroups, verdict.
    """
    if len(defect_counts) == 0:
        raise ValueError("defect_counts must not be empty")
    for count in defect_counts:
        if count < 0:
            raise ValueError("defect count must not be negative")
    cbar = float(sum(defect_counts)) / len(defect_counts)
    sigma_c = math.sqrt(cbar)
    ucl = cbar + SIGMA_FACTOR * sigma_c
    lcl = max(0.0, cbar - SIGMA_FACTOR * sigma_c)
    flagged = [
        i for i, count in enumerate(defect_counts)
        if count < lcl or count > ucl
    ]
    return {
        "cbar": cbar,
        "sigma_c": sigma_c,
        "UCL": ucl,
        "LCL": lcl,
        "flagged_subgroups": flagged,
        "verdict": attribute_verdict(flagged),
    }


def u_chart(defect_counts, areas):
    """u-chart for defect counts per unit with variable inspection area.

    ubar = sum(counts) / sum(areas); per-subgroup limits UCL_i/LCL_i =
    ubar +/- 3 sqrt(ubar / area_i) with LCL floored at 0, so the
    limits vary with the subgroup area. A subgroup i is flagged when
    its rate counts[i] / areas[i] lies outside [LCL_i, UCL_i].

    Returns a dict with keys ubar, UCLs, LCLs, flagged_subgroups,
    verdict.
    """
    if len(defect_counts) == 0:
        raise ValueError("defect_counts must not be empty")
    if len(areas) != len(defect_counts):
        raise ValueError("areas and defect_counts must have equal length")
    for count in defect_counts:
        if count < 0:
            raise ValueError("defect count must not be negative")
    for area in areas:
        if area <= 0:
            raise ValueError("area must be positive")
    ubar = float(sum(defect_counts)) / float(sum(areas))
    ucls = []
    lcls = []
    for area in areas:
        sigma_i = math.sqrt(ubar / area)
        ucls.append(ubar + SIGMA_FACTOR * sigma_i)
        lcls.append(max(0.0, ubar - SIGMA_FACTOR * sigma_i))
    flagged = [
        i for i in range(len(defect_counts))
        if (defect_counts[i] / areas[i]) < lcls[i]
        or (defect_counts[i] / areas[i]) > ucls[i]
    ]
    return {
        "ubar": ubar,
        "UCLs": ucls,
        "LCLs": lcls,
        "flagged_subgroups": flagged,
        "verdict": attribute_verdict(flagged),
    }
