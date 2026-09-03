"""Noise certification flight test planning and EPNL logic (pure stdlib).

Implements the acoustic-analysis layer of a transport noise
certification flight test per the FAR 36 / ICAO Annex 16 measurement
procedure summary (reference only, no verbatim regulation text):

- Reference geometry for the three certification measurement
  conditions: flyover, sideline, approach.
- Effective perceived noise level (EPNL) from a measured tone
  corrected perceived noise level (PNLT) time history using the
  10 dB down integration rule and the 10 second normalization.
- Per-point margin to the stated noise limit and the cumulative
  margin verdict for the three point set.

Deterministic, no external dependencies. All inputs are validated:
empty or non-finite PNLT series, non-positive time step, unknown
condition, and negative limits raise ValueError.
"""

import math

# Reference geometry (typical public FAR 36 measurement summary values).
FLYOVER_DISTANCE_M = 6500.0
SIDELINE_LATERAL_M = 450.0
APPROACH_DISTANCE_M = 1200.0
APPROACH_ALTITUDE_M = 120.0
APPROACH_GLIDE_DEG = 3.0

# EPNL integration constants.
T0 = 10.0
DB_DOWN = 10.0

# Cumulative (chapter 4 style) margin rule constant, in EPNdB.
CUMULATIVE_REQUIRED_DB = 10.0

CONDITIONS = ("flyover", "sideline", "approach")


def _finite(value):
    """Return True when value is a real finite number."""
    return isinstance(value, (int, float)) and math.isfinite(float(value))


def geometry(condition):
    """Return the reference geometry dict for a certification condition.

    Args:
        condition: one of "flyover", "sideline", "approach".

    Returns:
        Dict with the condition name and the reference distances from
        the module constants. Flyover is measured at a point 6500 m
        from the brake release on the extended runway centerline,
        sideline at 450 m lateral from the centerline at the point of
        maximum takeoff noise, approach at 1200 m from the threshold
        under the flight path at 120 m altitude on the 3 degree glide
        slope.

    Raises:
        ValueError: for an unknown condition.
    """
    if condition == "flyover":
        return {
            "condition": "flyover",
            "distance_m": FLYOVER_DISTANCE_M,
            "reference": "extended runway centerline, brake release point",
        }
    if condition == "sideline":
        return {
            "condition": "sideline",
            "lateral_m": SIDELINE_LATERAL_M,
            "reference": "lateral of runway centerline at max takeoff noise",
        }
    if condition == "approach":
        return {
            "condition": "approach",
            "distance_m": APPROACH_DISTANCE_M,
            "altitude_m": APPROACH_ALTITUDE_M,
            "glide_deg": APPROACH_GLIDE_DEG,
            "reference": "under the flight path from the threshold",
        }
    raise ValueError("unknown condition: %r (expected flyover, sideline or approach)" % condition)


def _interpolated_db(pnlt, dt, time):
    """Linear interpolation of the PNLT series in dB at a given time.

    Args:
        pnlt: list of PNLT samples in dB, equally spaced at dt seconds.
        dt: sample spacing in seconds (validated positive by caller).
        time: time coordinate of the requested value.

    Returns:
        PNLT in dB at the requested time by linear interpolation
        between the bracketing samples, clamped to the first or last
        sample outside the recorded span.
    """
    n = len(pnlt)
    position = time / dt
    index = int(math.floor(position))
    if index < 0:
        return pnlt[0]
    if index >= n - 1:
        return pnlt[-1]
    fraction = position - index
    return pnlt[index] * (1.0 - fraction) + pnlt[index + 1] * fraction


def epnl_from_pnlt(pnlt_series, dt=0.5):
    """Compute EPNL from a PNLT time history with the 10 dB down rule.

    EPNL = 10 * log10((1 / T0) * integral of 10**(PNLT/10) dt) taken
    over the 10 dB down interval: the interval in which PNLT stays
    within DB_DOWN dB of its maximum value. The interval boundaries
    are found by linear interpolation between the samples bracketing
    each crossing of the (PNLT_max - DB_DOWN) level; the energy
    integral is evaluated with the trapezoid rule over the sample
    points inside the interval plus the interpolated boundary points.
    When the series never drops DB_DOWN dB below the maximum, the
    whole recorded series is integrated and truncated is False.

    Args:
        pnlt_series: iterable of PNLT samples in dB, equally spaced.
        dt: sample spacing in seconds (default 0.5 s).

    Returns:
        Tuple (epnl_db, t_start_s, t_end_s, truncated): the EPNL in
        EPNdB, the start and end times in seconds of the integration
        interval, and whether the 10 dB down rule cut the interval
        short of the recorded span.

    Raises:
        ValueError: empty or non-finite series, non-finite or
            non-positive dt.
    """
    if not _finite(dt) or dt <= 0.0:
        raise ValueError("dt must be a finite positive time step")
    pnlt = list(pnlt_series)
    if not pnlt:
        raise ValueError("pnlt_series must not be empty")
    for value in pnlt:
        if not _finite(value):
            raise ValueError("pnlt_series contains a non-finite sample")
    n = len(pnlt)
    peak_index = max(range(n), key=lambda idx: pnlt[idx])
    peak_db = pnlt[peak_index]
    threshold_db = peak_db - DB_DOWN

    # Left boundary: walk left from the peak while samples stay above
    # the threshold; the crossing is interpolated between the two
    # bracketing samples.
    index = peak_index
    while index > 0 and pnlt[index - 1] > threshold_db:
        index -= 1
    if index > 0 and pnlt[index - 1] <= threshold_db:
        left_db = pnlt[index - 1]
        t_start = (index - 1) * dt + (threshold_db - left_db) / (
            pnlt[index] - left_db
        ) * dt
        left_found = True
    else:
        t_start = 0.0
        left_found = False

    # Right boundary: walk right from the peak while samples stay
    # above the threshold; the crossing is interpolated similarly.
    index = peak_index
    while index < n - 1 and pnlt[index + 1] > threshold_db:
        index += 1
    if index < n - 1 and pnlt[index + 1] <= threshold_db:
        right_db = pnlt[index + 1]
        t_end = index * dt + (threshold_db - pnlt[index]) / (
            right_db - pnlt[index]
        ) * dt
        right_found = True
    else:
        t_end = (n - 1) * dt
        right_found = False

    truncated = left_found or right_found

    if n == 1:
        # A single sample represents one dt interval at its own level.
        energy = 10.0 ** (pnlt[0] / 10.0) * dt
    else:
        # Trapezoid rule over the breakpoints inside the interval.
        breakpoints = [t_start]
        for sample_index in range(n):
            sample_time = sample_index * dt
            if t_start < sample_time < t_end:
                breakpoints.append(sample_time)
        breakpoints.append(t_end)
        breakpoints = sorted(set(breakpoints))
        energy = 0.0
        for left, right in zip(breakpoints, breakpoints[1:]):
            left_db = _interpolated_db(pnlt, dt, left)
            right_db = _interpolated_db(pnlt, dt, right)
            energy += (
                10.0 ** (left_db / 10.0) + 10.0 ** (right_db / 10.0)
            ) / 2.0 * (right - left)

    epnl_db = 10.0 * math.log10(energy / T0)
    return epnl_db, t_start, t_end, truncated


def margin_to_limit(epnl, limit):
    """Margin of a measured EPNL against its stated noise limit.

    Args:
        epnl: measured effective perceived noise level in EPNdB.
        limit: applicable noise limit in EPNdB (state input).

    Returns:
        Tuple (margin_db, verdict): margin_db = limit - epnl, verdict
        is "pass" when margin_db >= 0 else "fail".

    Raises:
        ValueError: non-finite EPNL or non-finite / negative limit.
    """
    if not _finite(epnl):
        raise ValueError("epnl must be a finite value in EPNdB")
    if not _finite(limit):
        raise ValueError("limit must be a finite value in EPNdB")
    if limit < 0.0:
        raise ValueError("limit must not be negative")
    margin_db = limit - epnl
    return margin_db, ("pass" if margin_db >= 0.0 else "fail")


def cumulative_margin(margins):
    """Assess the three point set against the cumulative margin rule.

    The typical chapter 4 / stage 4 cumulative check at reference
    level: the sum of the three per point margins must be at least
    CUMULATIVE_REQUIRED_DB EPNdB and every individual margin must be
    at or above zero. The exact rule set depends on the certification
    basis; this module documents the typical rule at reference level.

    Args:
        margins: iterable of the three per point margins in EPNdB.

    Returns:
        Dict with sum_db, required_db, min_margin_db, verdict ("pass"
        or "fail") and a reasons list describing any shortfall.

    Raises:
        ValueError: empty margins list or a non-finite margin.
    """
    margins = list(margins)
    if not margins:
        raise ValueError("margins must not be empty")
    for margin in margins:
        if not _finite(margin):
            raise ValueError("margins contains a non-finite value")
    sum_db = sum(margins)
    min_db = min(margins)
    reasons = []
    if sum_db < CUMULATIVE_REQUIRED_DB:
        reasons.append(
            "sum of margins %.3f EPNdB below the required %.1f EPNdB"
            % (sum_db, CUMULATIVE_REQUIRED_DB)
        )
    if min_db < 0.0:
        reasons.append(
            "individual margin %.3f EPNdB below zero" % min_db
        )
    if not reasons:
        reasons.append(
            "sum of margins %.3f EPNdB meets the required %.1f EPNdB "
            "and every individual margin is at or above zero"
            % (sum_db, CUMULATIVE_REQUIRED_DB)
        )
    verdict = "pass" if (sum_db >= CUMULATIVE_REQUIRED_DB and min_db >= 0.0) else "fail"
    return {
        "sum_db": sum_db,
        "required_db": CUMULATIVE_REQUIRED_DB,
        "min_margin_db": min_db,
        "verdict": verdict,
        "reasons": reasons,
    }


def test_matrix(takeoff_weight, landing_weight, v2_kt, approach_speed_kt, limits):
    """Build the three condition certification test matrix rows.

    Args:
        takeoff_weight: takeoff gross weight in kg (flyover and
            sideline conditions).
        landing_weight: landing gross weight in kg (approach
            condition).
        v2_kt: takeoff safety speed V2 in knots (sideline reference;
            flyover reference is V2 + 10 kt per the typical FAR 36
            measurement summary).
        approach_speed_kt: reference approach speed in knots.
        limits: dict with the applicable noise limit in EPNdB for each
            of flyover, sideline and approach (state inputs).

    Returns:
        List of three row dicts, one per condition, each with
        condition, configuration, weight_kg, reference_speed_kt,
        limit and target_epnl (the demonstration target equals the
        stated limit).

    Raises:
        ValueError: missing key in limits, non-positive weight or
            speed, or a negative limit value.
    """
    for condition in CONDITIONS:
        if condition not in limits:
            raise ValueError("limits missing key %r" % condition)
    for value, name in (
        (takeoff_weight, "takeoff_weight"),
        (landing_weight, "landing_weight"),
        (v2_kt, "v2_kt"),
        (approach_speed_kt, "approach_speed_kt"),
    ):
        if not _finite(value) or value <= 0.0:
            raise ValueError("%s must be a finite positive value" % name)
    rows = []
    for condition in CONDITIONS:
        if condition == "approach":
            configuration = "landing"
            weight = landing_weight
            speed = approach_speed_kt
        else:
            configuration = "takeoff"
            weight = takeoff_weight
            speed = v2_kt + (10.0 if condition == "flyover" else 0.0)
        limit = limits[condition]
        if not _finite(limit) or limit < 0.0:
            raise ValueError("limit for %r must not be negative" % condition)
        rows.append(
            {
                "condition": condition,
                "configuration": configuration,
                "weight_kg": weight,
                "reference_speed_kt": speed,
                "limit": limit,
                "target_epnl": limit,
            }
        )
    return rows


def summarize(epnl_by_condition, limits):
    """Summarize EPNL, margin and cumulative verdict per condition.

    Args:
        epnl_by_condition: dict mapping flyover, sideline and approach
            to their measured EPNL in EPNdB.
        limits: dict with the applicable noise limit in EPNdB for each
            of the three conditions.

    Returns:
        Dict with epnl and margin per condition, the per condition
        verdicts, and the cumulative margin assessment dict.

    Raises:
        ValueError: missing condition key in either input, non-finite
            EPNL, or negative limit (via margin_to_limit).
    """
    for condition in CONDITIONS:
        if condition not in epnl_by_condition:
            raise ValueError("epnl_by_condition missing key %r" % condition)
        if condition not in limits:
            raise ValueError("limits missing key %r" % condition)
    margins = {}
    verdicts = {}
    for condition in CONDITIONS:
        margin_db, verdict = margin_to_limit(
            epnl_by_condition[condition], limits[condition]
        )
        margins[condition] = margin_db
        verdicts[condition] = verdict
    cumulative = cumulative_margin(
        [margins[condition] for condition in CONDITIONS]
    )
    return {
        "epnl": dict(epnl_by_condition),
        "margin": margins,
        "verdict": verdicts,
        "cumulative": cumulative,
    }
