"""Multipactor testing across the temperature extremes of the critical gap.

Anchor: ECSS-E-ST-20-01C clause 6.3 (multipactor tests run at the
temperature extremes defined for the critical gap region). Paraphrased
into an implementable procedure; no standard text is reproduced.

Stdlib only, offline, deterministic. The module derives qualification
extremes from predicted temperatures plus margin, expands or contracts
the critical gap with temperature through the effective expansion
coefficient, forms the frequency-gap product at each extreme, reads a
breakdown threshold off a susceptibility trend, converts the applied
power into a peak gap voltage, and reports which extreme is the worst
case and whether the campaign soaked and covered both of them.
"""

import math

ABSOLUTE_ZERO_C = -273.15

# Boundary tolerance: a point landing exactly on a requirement is
# compliant, and a difference of two temperatures or a sum of margins can
# sit a few units in the last place beyond it. Absorb the representation
# error here rather than widening the engineering limit.
REL_TOL = 1e-9
ABS_TOL = 1e-12

# Susceptibility trend for a plated metallic surface: first-order
# breakdown voltage against the frequency-gap product. Paraphrased trend
# points for interpolation, not reproduced standard data.
_SUSCEPTIBILITY_TREND = (
    (0.1, 30.0),
    (0.3, 70.0),
    (1.0, 200.0),
    (3.0, 600.0),
    (10.0, 2000.0),
    (30.0, 7000.0),
    (100.0, 30000.0),
)

MIN_FD_GHZ_MM = _SUSCEPTIBILITY_TREND[0][0]
MAX_FD_GHZ_MM = _SUSCEPTIBILITY_TREND[-1][0]

DEFAULT_LINE_IMPEDANCE_OHM = 50.0

_EXTREME_ALIASES = {
    "cold": "cold",
    "cold-extreme": "cold",
    "minimum": "cold",
    "low-temperature": "cold",
    "hot": "hot",
    "hot-extreme": "hot",
    "maximum": "hot",
    "high-temperature": "hot",
}


def _real(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative(value, label):
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def categorize_extreme(label):
    """Map an extreme label onto 'cold' or 'hot'."""
    if not isinstance(label, str):
        raise ValueError("extreme label must be a string, got %r" % (label,))
    key = label.strip().lower().replace(" ", "-").replace("_", "-")
    if not key:
        raise ValueError("extreme label must not be empty")
    if key not in _EXTREME_ALIASES:
        raise ValueError("uncategorized temperature extreme %r" % (label,))
    return _EXTREME_ALIASES[key]


def qualification_extremes(predicted_min_c, predicted_max_c, qualification_margin_k):
    """Cold and hot test temperatures from predictions plus margin."""
    low = _real(predicted_min_c, "predicted_min_c")
    high = _real(predicted_max_c, "predicted_max_c")
    margin = _non_negative(qualification_margin_k, "qualification_margin_k")
    if low > high:
        raise ValueError(
            "predicted_min_c (%g) must not exceed predicted_max_c (%g)" % (low, high)
        )
    cold = low - margin
    hot = high + margin
    if cold <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "cold extreme %g C falls at or below absolute zero; check the margin" % cold
        )
    return {
        "cold_c": cold,
        "hot_c": hot,
        "predicted_min_c": low,
        "predicted_max_c": high,
        "qualification_margin_k": margin,
        "span_k": hot - cold,
    }


def gap_at_temperature(gap_reference_mm, expansion_per_k, reference_c, temperature_c):
    """Critical gap width at a temperature, via linear thermal expansion."""
    gap_ref = _positive(gap_reference_mm, "gap_reference_mm")
    alpha = _real(expansion_per_k, "expansion_per_k")
    t_ref = _real(reference_c, "reference_c")
    temperature = _real(temperature_c, "temperature_c")
    if temperature <= ABSOLUTE_ZERO_C:
        raise ValueError("temperature_c must lie above absolute zero, got %r" % (temperature_c,))
    gap = gap_ref * (1.0 + alpha * (temperature - t_ref))
    if gap <= 0.0:
        raise ValueError(
            "expansion model closes the gap at %g C; expansion_per_k is out of range"
            % temperature
        )
    return gap


def frequency_gap_product(frequency_ghz, gap_mm):
    """Frequency-gap product in gigahertz-millimetre."""
    frequency = _positive(frequency_ghz, "frequency_ghz")
    gap = _positive(gap_mm, "gap_mm")
    return frequency * gap


def breakdown_threshold_v(fd_ghz_mm):
    """First-order breakdown voltage read off the susceptibility trend.

    Log-log interpolation between the tabulated trend points.
    """
    fd = _positive(fd_ghz_mm, "fd_ghz_mm")
    if fd < MIN_FD_GHZ_MM or fd > MAX_FD_GHZ_MM:
        raise ValueError(
            "fd_ghz_mm %g lies outside the tabulated trend (%g to %g)"
            % (fd, MIN_FD_GHZ_MM, MAX_FD_GHZ_MM)
        )
    previous_fd, previous_v = _SUSCEPTIBILITY_TREND[0]
    if math.isclose(fd, previous_fd, rel_tol=REL_TOL, abs_tol=ABS_TOL):
        return previous_v
    for next_fd, next_v in _SUSCEPTIBILITY_TREND[1:]:
        if fd <= next_fd or math.isclose(fd, next_fd, rel_tol=REL_TOL, abs_tol=ABS_TOL):
            span = math.log10(next_fd) - math.log10(previous_fd)
            position = (math.log10(fd) - math.log10(previous_fd)) / span
            log_v = math.log10(previous_v) + position * (
                math.log10(next_v) - math.log10(previous_v)
            )
            return 10.0 ** log_v
        previous_fd, previous_v = next_fd, next_v
    return _SUSCEPTIBILITY_TREND[-1][1]


def peak_voltage_from_power(power_w, impedance_ohm=DEFAULT_LINE_IMPEDANCE_OHM):
    """Peak voltage of a travelling wave carrying a given power."""
    power = _positive(power_w, "power_w")
    impedance = _positive(impedance_ohm, "impedance_ohm")
    return math.sqrt(2.0 * impedance * power)


def evaluate_extreme(
    temperature_c,
    gap_reference_mm,
    expansion_per_k,
    reference_c,
    frequency_ghz,
    applied_power_w,
    required_margin_db,
    impedance_ohm=DEFAULT_LINE_IMPEDANCE_OHM,
):
    """Grade one temperature extreme against its multipactor margin."""
    required = _non_negative(required_margin_db, "required_margin_db")
    gap = gap_at_temperature(gap_reference_mm, expansion_per_k, reference_c, temperature_c)
    fd = frequency_gap_product(frequency_ghz, gap)
    threshold = breakdown_threshold_v(fd)
    applied = peak_voltage_from_power(applied_power_w, impedance_ohm)
    margin_db = 20.0 * math.log10(threshold / applied)
    at_requirement = math.isclose(margin_db, required, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return {
        "temperature_c": float(temperature_c),
        "gap_mm": gap,
        "fd_ghz_mm": fd,
        "threshold_v": threshold,
        "applied_peak_v": applied,
        "margin_db": margin_db,
        "required_margin_db": required,
        "at_requirement": at_requirement,
        "compliant": margin_db > required or at_requirement,
    }


def worst_case_extreme(evaluations):
    """The extreme with the least multipactor margin.

    evaluations maps an extreme label to the result of evaluate_extreme.
    """
    if not isinstance(evaluations, dict) or not evaluations:
        raise ValueError("evaluations must be a non-empty mapping of extreme to result")
    resolved = {}
    for raw_label, result in evaluations.items():
        label = categorize_extreme(raw_label)
        if label in resolved:
            raise ValueError("temperature extreme %r supplied twice" % (label,))
        if not isinstance(result, dict) or "margin_db" not in result:
            raise ValueError("evaluation for %r is not an evaluate_extreme result" % (label,))
        resolved[label] = result
    ordered = sorted(resolved.items(), key=lambda item: (item[1]["margin_db"], item[0]))
    label, result = ordered[0]
    return {
        "extreme": label,
        "margin_db": result["margin_db"],
        "gap_mm": result["gap_mm"],
        "fd_ghz_mm": result["fd_ghz_mm"],
        "compliant": result["compliant"],
    }


def evaluate_soak(soak_minutes, required_soak_minutes, measured_drift_k, allowed_drift_k):
    """Check that the item stabilised at the extreme before power was applied."""
    soak = _non_negative(soak_minutes, "soak_minutes")
    required = _positive(required_soak_minutes, "required_soak_minutes")
    drift = _non_negative(measured_drift_k, "measured_drift_k")
    allowed = _positive(allowed_drift_k, "allowed_drift_k")
    soak_ok = soak > required or math.isclose(soak, required, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    drift_ok = drift < allowed or math.isclose(drift, allowed, rel_tol=REL_TOL, abs_tol=ABS_TOL)
    return {
        "soak_minutes": soak,
        "required_soak_minutes": required,
        "measured_drift_k": drift,
        "allowed_drift_k": allowed,
        "soak_sufficient": soak_ok,
        "drift_within_tolerance": drift_ok,
        "stabilised": soak_ok and drift_ok,
    }


def evaluate_temperature_coverage(tested_points_c, extremes, setpoint_tolerance_k):
    """Which required extremes the tested points actually covered."""
    if tested_points_c is None:
        raise ValueError("tested_points_c must be an iterable of temperatures")
    if isinstance(tested_points_c, (str, bytes)):
        raise ValueError("tested_points_c must be a list of temperatures, not a string")
    tolerance = _positive(setpoint_tolerance_k, "setpoint_tolerance_k")
    if not isinstance(extremes, dict):
        raise ValueError("extremes must be the mapping returned by qualification_extremes")
    for key in ("cold_c", "hot_c"):
        if key not in extremes:
            raise ValueError("extremes missing required key %r" % (key,))
    points = [_real(point, "tested point") for point in tested_points_c]
    if not points:
        raise ValueError("tested_points_c must contain at least one temperature")
    covered = {}
    for label, key in (("cold", "cold_c"), ("hot", "hot_c")):
        target = _real(extremes[key], key)
        best = min(abs(point - target) for point in points)
        within = best < tolerance or math.isclose(
            best, tolerance, rel_tol=REL_TOL, abs_tol=ABS_TOL
        )
        covered[label] = {
            "target_c": target,
            "closest_deviation_k": best,
            "covered": within,
        }
    return {
        "coverage": covered,
        "uncovered": sorted(k for k, v in covered.items() if not v["covered"]),
        "complete": all(v["covered"] for v in covered.values()),
    }


def assess_temperature_campaign(campaign):
    """Aggregate the clause 6.3 checks into a findings list."""
    if not isinstance(campaign, dict):
        raise ValueError("campaign must be a mapping")
    required_keys = (
        "predicted_min_c",
        "predicted_max_c",
        "qualification_margin_k",
        "gap_reference_mm",
        "expansion_per_k",
        "reference_c",
        "frequency_ghz",
        "applied_power_w",
        "required_margin_db",
        "tested_points_c",
        "setpoint_tolerance_k",
        "soak_minutes",
        "required_soak_minutes",
        "measured_drift_k",
        "allowed_drift_k",
    )
    for key in required_keys:
        if key not in campaign:
            raise ValueError("campaign missing required key %r" % (key,))
    findings = []
    extremes = qualification_extremes(
        campaign["predicted_min_c"],
        campaign["predicted_max_c"],
        campaign["qualification_margin_k"],
    )
    impedance = campaign.get("impedance_ohm", DEFAULT_LINE_IMPEDANCE_OHM)
    evaluations = {}
    for label, key in (("cold", "cold_c"), ("hot", "hot_c")):
        evaluations[label] = evaluate_extreme(
            extremes[key],
            campaign["gap_reference_mm"],
            campaign["expansion_per_k"],
            campaign["reference_c"],
            campaign["frequency_ghz"],
            campaign["applied_power_w"],
            campaign["required_margin_db"],
            impedance,
        )
        if not evaluations[label]["compliant"]:
            findings.append("%s extreme does not hold the required multipactor margin" % label)

    worst = worst_case_extreme(evaluations)

    coverage = evaluate_temperature_coverage(
        campaign["tested_points_c"], extremes, campaign["setpoint_tolerance_k"]
    )
    for label in coverage["uncovered"]:
        findings.append("no tested point covers the %s extreme" % label)

    soak = evaluate_soak(
        campaign["soak_minutes"],
        campaign["required_soak_minutes"],
        campaign["measured_drift_k"],
        campaign["allowed_drift_k"],
    )
    if not soak["soak_sufficient"]:
        findings.append("soak duration at the extreme is shorter than required")
    if not soak["drift_within_tolerance"]:
        findings.append("temperature drift during the run exceeds its tolerance")

    return {
        "extremes": extremes,
        "evaluations": evaluations,
        "worst_case": worst,
        "coverage": coverage,
        "soak": soak,
        "findings": sorted(findings),
        "compliant": not findings,
    }
