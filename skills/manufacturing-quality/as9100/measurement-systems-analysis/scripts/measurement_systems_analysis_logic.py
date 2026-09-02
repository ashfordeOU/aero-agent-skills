#!/usr/bin/env python3
"""Measurement systems analysis (MSA) math for aerospace manufacturing.

Deterministic, offline, stdlib-only helpers for the range-based Gage
repeatability and reproducibility (Gage R and R) study: equipment
variation (EV) from the average range, appraiser variation (AV) from
the spread of appraiser averages, the combined GRR, part-to-part
variation (PV), total variation (TV), the percent GRR against the
acceptance bands (under 10 percent acceptable, 10 to 30 percent
conditional, over 30 percent unacceptable), and the number of distinct
categories.

The K1, K2, and K3 constants are the common published 5.15-sigma
range-method constants (summary values, not reproduced tables from any
standard; per standards-map.yaml as9100 is reference-only). Input is
an operator-part measurement table: a dict of appraiser name to a list
of parts, each part a list of trial readings.

Contract exercised by scripts/test_measurement_systems_analysis.py.
"""

import math

# Range-method constants. K1 scales the average cell range to EV by
# the number of trials, K2 scales the spread of appraiser averages to
# AV by the number of appraisers, K3 scales the spread of part
# averages to PV by the number of parts.
K1 = {2: 4.56, 3: 3.05}  # trials
K2 = {2: 3.65, 3: 2.70}  # appraisers
K3 = {2: 3.65, 3: 2.70, 4: 2.30, 5: 2.08,
      6: 1.93, 7: 1.82, 8: 1.74, 9: 1.67, 10: 1.62}  # parts


def _is_number(value):
    """True when value is an int or float, excluding bool."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate_table(measurements):
    """Validate an operator-part measurement table, raise ValueError.

    measurements maps an appraiser name to a list of parts, each part
    a list of trial readings. The range method requires at least two
    appraisers (2 or 3), the same number of parts per appraiser (2 to
    10), the same number of trials per part (2 or 3), and every
    reading a non-negative number. Empty tables, inconsistent
    dimensions, unsupported counts, and negative values all raise
    ValueError.
    """
    if not isinstance(measurements, dict):
        raise ValueError("measurements must be a dict of appraiser tables")
    if len(measurements) < 2:
        raise ValueError(
            "at least two appraisers are required, got %d" % len(measurements)
        )
    if len(measurements) > 3:
        raise ValueError(
            "range method supports 2 or 3 appraisers, got %d" % len(measurements)
        )
    parts_per_appraiser = None
    trials = None
    for appraiser, parts in measurements.items():
        if not isinstance(parts, list) or not parts:
            raise ValueError(
                "appraiser %r must have a non-empty list of parts" % (appraiser,)
            )
        if parts_per_appraiser is None:
            parts_per_appraiser = len(parts)
        elif len(parts) != parts_per_appraiser:
            raise ValueError("inconsistent part counts across appraisers")
        for part in parts:
            if not isinstance(part, list) or not part:
                raise ValueError("each part must have a non-empty list of trials")
            if trials is None:
                trials = len(part)
            elif len(part) != trials:
                raise ValueError("inconsistent trial counts across parts")
            for value in part:
                if not _is_number(value):
                    raise ValueError(
                        "measurement values must be numbers, got %r" % (value,)
                    )
                if value < 0:
                    raise ValueError(
                        "measurement values must be >= 0, got %r" % (value,)
                    )
    if parts_per_appraiser is None or trials is None:
        raise ValueError("measurements table is empty")
    if parts_per_appraiser < 2:
        raise ValueError(
            "at least two parts are required, got %d" % parts_per_appraiser
        )
    if parts_per_appraiser > 10:
        raise ValueError(
            "range method supports 2 to 10 parts, got %d" % parts_per_appraiser
        )
    if trials not in K1:
        raise ValueError("range method supports 2 or 3 trials, got %d" % trials)


def _trials(measurements):
    """Number of trials per part (validated table)."""
    return len(next(iter(measurements.values()))[0])


def _parts_count(measurements):
    """Number of parts per appraiser (validated table)."""
    return len(next(iter(measurements.values())))


def equipment_variation(measurements):
    """Return EV: repeatability from the average cell range.

    EV = K1 * rbar with rbar the average of the trial ranges across
    all appraiser-part cells. This is the equipment contribution to
    measurement error. Raises ValueError on a malformed table.
    """
    validate_table(measurements)
    ranges = []
    for parts in measurements.values():
        for part in parts:
            ranges.append(max(part) - min(part))
    rbar = sum(ranges) / len(ranges)
    return K1[_trials(measurements)] * rbar


def appraiser_variation(measurements):
    """Return AV: reproducibility from the spread of appraiser averages.

    AV = sqrt((K2 * xdiff)^2 - EV^2 / (trials * parts)) with xdiff the
    spread of the appraiser averages. A negative radicand means the
    appraisers agree within equipment variation, so AV is clamped to
    zero. Raises ValueError on a malformed table.
    """
    validate_table(measurements)
    means = []
    for parts in measurements.values():
        flat = [value for part in parts for value in part]
        means.append(sum(flat) / len(flat))
    xdiff = max(means) - min(means)
    ev = equipment_variation(measurements)
    trials = _trials(measurements)
    parts = _parts_count(measurements)
    radicand = (K2[len(measurements)] * xdiff) ** 2 - ev ** 2 / (trials * parts)
    return math.sqrt(max(0.0, radicand))


def grr_variation(measurements):
    """Return GRR: the combined gage error, sqrt(EV^2 + AV^2)."""
    ev = equipment_variation(measurements)
    av = appraiser_variation(measurements)
    return math.sqrt(ev ** 2 + av ** 2)


def part_variation(measurements):
    """Return PV: part-to-part variation from the spread of part averages.

    PV = K3 * Rp with Rp the range of the part averages across
    appraisers and trials. Raises ValueError on a malformed table.
    """
    validate_table(measurements)
    parts = _parts_count(measurements)
    trials = _trials(measurements)
    appraisers = len(measurements)
    part_means = []
    for j in range(parts):
        total = 0.0
        for parts_list in measurements.values():
            for value in parts_list[j]:
                total += value
        part_means.append(total / (appraisers * trials))
    rp = max(part_means) - min(part_means)
    return K3[parts] * rp


def total_variation(measurements):
    """Return TV: sqrt(GRR^2 + PV^2)."""
    grr = grr_variation(measurements)
    pv = part_variation(measurements)
    return math.sqrt(grr ** 2 + pv ** 2)


def number_distinct_categories(pv, grr):
    """Return ndc = floor(1.41 * PV / GRR), None when GRR is zero.

    The common guidance treats five or more distinct categories as the
    threshold for an adequate measurement system. Raises ValueError
    for negative inputs.
    """
    if not _is_number(pv) or not _is_number(grr):
        raise ValueError("pv and grr must be numbers")
    if pv < 0 or grr < 0:
        raise ValueError("pv and grr must be >= 0")
    if grr == 0:
        return None
    return int(math.floor(1.41 * pv / grr))


def acceptance_verdict(grr_pct):
    """Return the verdict for a percent GRR value.

    Under 10 percent is acceptable, 10 to 30 percent is conditional
    (acceptable only for specific applications), over 30 percent is
    unacceptable. Raises ValueError for a negative input.
    """
    if not _is_number(grr_pct):
        raise ValueError("grr_pct must be a number")
    if grr_pct < 0:
        raise ValueError("grr_pct must be >= 0, got %r" % (grr_pct,))
    if grr_pct < 10:
        return "acceptable"
    if grr_pct <= 30:
        return "conditional"
    return "unacceptable"


def study_summary(measurements):
    """Return the full range-method study summary as a dict.

    Keys: ev, av, grr, pv, tv, ev_pct, av_pct, grr_pct, pv_pct, ndc,
    verdict. Percentages are relative to total variation. A study with
    zero total variation (identical readings everywhere) reports zero
    percent GRR, an acceptable verdict, and ndc None. Raises
    ValueError on a malformed table.
    """
    ev = equipment_variation(measurements)
    av = appraiser_variation(measurements)
    grr = grr_variation(measurements)
    pv = part_variation(measurements)
    tv = total_variation(measurements)
    if tv > 0:
        ev_pct = 100.0 * ev / tv
        av_pct = 100.0 * av / tv
        grr_pct = 100.0 * grr / tv
        pv_pct = 100.0 * pv / tv
    else:
        ev_pct = av_pct = grr_pct = pv_pct = 0.0
    return {
        "ev": ev,
        "av": av,
        "grr": grr,
        "pv": pv,
        "tv": tv,
        "ev_pct": ev_pct,
        "av_pct": av_pct,
        "grr_pct": grr_pct,
        "pv_pct": pv_pct,
        "ndc": number_distinct_categories(pv, grr),
        "verdict": acceptance_verdict(grr_pct),
    }
