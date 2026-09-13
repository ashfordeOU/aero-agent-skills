#!/usr/bin/env python3
"""First-level multipactor thresholds read from the tabulated charts.

Anchor: ECSS-E-ST-20-01C clause 5.3.3.4. The procedure below is a paraphrased,
implementable restatement -- no verbatim standard text. Offline, deterministic,
Python standard library only.

A first-level multipactor analysis does not solve the electron dynamics: it
reads a threshold off a tabulated parallel-plate susceptibility chart for the
electrode surface, at the frequency-gap-product of the gap, and compares the
operating voltage against it. This module builds that read-out, refuses to
extrapolate beyond the chart, and grades the resulting margin in decibel.
"""

import math

__all__ = [
    "frequency_gap_product",
    "validate_chart",
    "chart_validity_range",
    "select_chart",
    "lookup_threshold_voltage",
    "equivalent_gap_voltage",
    "multipactor_margin_db",
    "assess_gap_first_level",
    "assess_first_level_campaign",
]

# Absorbs the representation error of a product or a sum of decimal terms that
# lands a few ULPs outside its own bound. It never widens the chart range and
# never lowers the required margin.
CHART_REL_TOL = 1e-9


def _finite_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _token(value, label):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip().lower()


def frequency_gap_product(frequency_ghz, gap_mm):
    """Return the similarity parameter of the gap, in GHz*mm."""
    frequency = _finite_number(frequency_ghz, "frequency_ghz")
    gap = _finite_number(gap_mm, "gap_mm")
    if frequency <= 0.0:
        raise ValueError("frequency must be strictly positive, got %r" % (frequency_ghz,))
    if gap <= 0.0:
        raise ValueError("gap must be strictly positive, got %r" % (gap_mm,))
    return frequency * gap


def validate_chart(chart):
    """Normalize one tabulated susceptibility chart, raising on a bad table.

    A chart names the electrode surface it was measured on and carries at
    least two (frequency-gap-product, threshold-voltage) points with strictly
    increasing abscissae and strictly positive voltages.
    """
    if not isinstance(chart, dict):
        raise ValueError("chart must be a mapping, got %r" % type(chart))
    base_material = _token(chart.get("base_material"), "base_material")
    surface_treatment = _token(chart.get("surface_treatment"), "surface_treatment")
    points_in = chart.get("points")
    if not isinstance(points_in, (list, tuple)) or len(points_in) < 2:
        raise ValueError("chart needs at least two (fd_ghz_mm, threshold_v) points")
    points = []
    previous_fd = None
    for index, point in enumerate(points_in):
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("points[%d] must be an (fd_ghz_mm, threshold_v) pair" % index)
        fd_value = _finite_number(point[0], "points[%d] fd_ghz_mm" % index)
        voltage = _finite_number(point[1], "points[%d] threshold_v" % index)
        if fd_value <= 0.0:
            raise ValueError("points[%d] frequency-gap-product must be positive" % index)
        if voltage <= 0.0:
            raise ValueError("points[%d] threshold voltage must be positive" % index)
        if previous_fd is not None and fd_value <= previous_fd:
            raise ValueError(
                "chart abscissae must strictly increase (at index %d)" % index
            )
        previous_fd = fd_value
        points.append((fd_value, voltage))
    return {
        "base_material": base_material,
        "surface_treatment": surface_treatment,
        "points": points,
        "fd_min_ghz_mm": points[0][0],
        "fd_max_ghz_mm": points[-1][0],
    }


def chart_validity_range(chart):
    """Return the frequency-gap-product span the chart was tabulated over."""
    entry = validate_chart(chart)
    return (entry["fd_min_ghz_mm"], entry["fd_max_ghz_mm"])


def select_chart(charts, base_material, surface_treatment):
    """Pick the chart tabulated for this electrode surface.

    A surface with no tabulated chart has no first-level threshold; the caller
    is told so rather than handed the chart of a different metal.
    """
    if not isinstance(charts, (list, tuple)) or not charts:
        raise ValueError("at least one tabulated chart is required")
    material = _token(base_material, "base_material")
    treatment = _token(surface_treatment, "surface_treatment")
    for chart in charts:
        entry = validate_chart(chart)
        if entry["base_material"] == material and entry["surface_treatment"] == treatment:
            return entry
    raise ValueError(
        "no tabulated chart for %s / %s; a dedicated analysis is owed"
        % (material, treatment)
    )


def lookup_threshold_voltage(chart, fd_ghz_mm):
    """Interpolate the threshold voltage at a frequency-gap-product.

    Interpolation is logarithmic in both axes, matching the way the charts are
    plotted, so a read-out between two decades does not sag toward a straight
    line drawn on linear paper. A value outside the tabulated span is refused:
    first-level chart reading stops where the chart stops.
    """
    entry = chart if "fd_min_ghz_mm" in chart else validate_chart(chart)
    fd_value = _finite_number(fd_ghz_mm, "fd_ghz_mm")
    if fd_value <= 0.0:
        raise ValueError("frequency-gap-product must be positive, got %r" % (fd_ghz_mm,))
    low = entry["fd_min_ghz_mm"]
    high = entry["fd_max_ghz_mm"]
    if fd_value < low and not math.isclose(fd_value, low, rel_tol=CHART_REL_TOL):
        raise ValueError(
            "frequency-gap-product %.6g is below the chart range (%.6g)" % (fd_value, low)
        )
    if fd_value > high and not math.isclose(fd_value, high, rel_tol=CHART_REL_TOL):
        raise ValueError(
            "frequency-gap-product %.6g is above the chart range (%.6g)" % (fd_value, high)
        )
    points = entry["points"]
    if fd_value <= low:
        return points[0][1]
    if fd_value >= high:
        return points[-1][1]
    for index in range(1, len(points)):
        left_fd, left_v = points[index - 1]
        right_fd, right_v = points[index]
        if fd_value <= right_fd:
            log_span = math.log10(right_fd) - math.log10(left_fd)
            fraction = (math.log10(fd_value) - math.log10(left_fd)) / log_span
            log_v = math.log10(left_v) + fraction * (math.log10(right_v) - math.log10(left_v))
            return 10.0 ** log_v
    return points[-1][1]


def equivalent_gap_voltage(peak_power_w, impedance_ohm):
    """Convert the peak power at the gap into the equivalent gap voltage.

    For a matched line the peak voltage across the gap follows from the peak
    power and the local impedance as sqrt(2 * P * Z), which is the quantity the
    parallel-plate charts are plotted against.
    """
    power = _finite_number(peak_power_w, "peak_power_w")
    impedance = _finite_number(impedance_ohm, "impedance_ohm")
    if power <= 0.0:
        raise ValueError("peak power must be strictly positive, got %r" % (peak_power_w,))
    if impedance <= 0.0:
        raise ValueError("impedance must be strictly positive, got %r" % (impedance_ohm,))
    return math.sqrt(2.0 * power * impedance)


def multipactor_margin_db(threshold_v, operating_v):
    """Return the margin in decibel between threshold and operating voltage."""
    threshold = _finite_number(threshold_v, "threshold_v")
    operating = _finite_number(operating_v, "operating_v")
    if threshold <= 0.0:
        raise ValueError("threshold voltage must be strictly positive")
    if operating <= 0.0:
        raise ValueError("operating voltage must be strictly positive")
    return 20.0 * math.log10(threshold / operating)


def assess_gap_first_level(gap, charts, required_margin_db):
    """Grade one gap against the tabulated chart at first level.

    Returns a verdict of compliant, insufficient-margin, or
    chart-range-exceeded; the last is an escalation to a dedicated analysis,
    not a failure of the gap.
    """
    if not isinstance(gap, dict):
        raise ValueError("gap must be a mapping, got %r" % type(gap))
    name = gap.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("gap requires a non-empty name")
    required = _finite_number(required_margin_db, "required_margin_db")
    if required < 0.0:
        raise ValueError("required margin cannot be negative, got %r" % (required_margin_db,))
    fd_value = frequency_gap_product(gap.get("frequency_ghz"), gap.get("gap_mm"))
    chart = select_chart(
        charts, gap.get("base_material"), gap.get("surface_treatment")
    )
    operating_v = gap.get("operating_voltage_v")
    if operating_v is None:
        operating_v = equivalent_gap_voltage(
            gap.get("peak_power_w"), gap.get("impedance_ohm")
        )
    else:
        operating_v = _finite_number(operating_v, "operating_voltage_v")
        if operating_v <= 0.0:
            raise ValueError("operating voltage must be strictly positive")
    low, high = chart["fd_min_ghz_mm"], chart["fd_max_ghz_mm"]
    inside = True
    if fd_value < low and not math.isclose(fd_value, low, rel_tol=CHART_REL_TOL):
        inside = False
    if fd_value > high and not math.isclose(fd_value, high, rel_tol=CHART_REL_TOL):
        inside = False
    if not inside:
        return {
            "name": name.strip(),
            "frequency_gap_product_ghz_mm": fd_value,
            "chart_range_ghz_mm": (low, high),
            "operating_voltage_v": operating_v,
            "threshold_voltage_v": None,
            "margin_db": None,
            "verdict": "chart-range-exceeded",
            "escalate_to_dedicated_analysis": True,
        }
    threshold_v = lookup_threshold_voltage(chart, fd_value)
    margin = multipactor_margin_db(threshold_v, operating_v)
    compliant = margin >= required or math.isclose(
        margin, required, rel_tol=CHART_REL_TOL, abs_tol=1e-12
    )
    return {
        "name": name.strip(),
        "frequency_gap_product_ghz_mm": fd_value,
        "chart_range_ghz_mm": (low, high),
        "operating_voltage_v": operating_v,
        "threshold_voltage_v": threshold_v,
        "margin_db": margin,
        "required_margin_db": required,
        "verdict": "compliant" if compliant else "insufficient-margin",
        "escalate_to_dedicated_analysis": False,
    }


def assess_first_level_campaign(gaps, charts, required_margin_db):
    """Grade every gap and summarise what first level was able to close."""
    if not isinstance(gaps, (list, tuple)) or not gaps:
        raise ValueError("at least one gap is required")
    results = [assess_gap_first_level(gap, charts, required_margin_db) for gap in gaps]
    names = [entry["name"] for entry in results]
    if len(set(names)) != len(names):
        raise ValueError("gap names must be unique within a campaign")
    failing = [e["name"] for e in results if e["verdict"] == "insufficient-margin"]
    escalated = [e["name"] for e in results if e["verdict"] == "chart-range-exceeded"]
    closed = [e["name"] for e in results if e["verdict"] == "compliant"]
    margins = [e["margin_db"] for e in results if e["margin_db"] is not None]
    return {
        "gaps": results,
        "compliant_gaps": closed,
        "failing_gaps": failing,
        "escalated_gaps": escalated,
        "worst_margin_db": min(margins) if margins else None,
        "first_level_closed": not failing and not escalated,
    }
