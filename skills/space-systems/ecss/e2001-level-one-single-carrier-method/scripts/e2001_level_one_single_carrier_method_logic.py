#!/usr/bin/env python3
"""Level-one single-carrier multipactor method (ECSS-E-ST-20-01C clause 5.3.2.2.3).

Deterministic, offline, stdlib-only implementation of the first-level procedure
for one carrier: start from the peak voltage in the critical region, index the
susceptibility boundary on the frequency-gap product, and turn the ratio of the
boundary voltage to the applied voltage into a decibel margin the selected
verification route can be checked against.

No standard text is reproduced; the clause is cited as the anchor only. The
bundled boundary curve is an in-house, monotone stand-in whose only role is to
make the procedure runnable and testable offline -- a project supplies its own
digitised chart through the `chart` argument of threshold_voltage().
"""

import math

DEFAULT_IMPEDANCE_OHM = 50.0

# Decibel margin owed by each verification route. These are project-agreed
# defaults carried so the procedure runs end to end; a project that agrees a
# different value passes it in explicitly.
ROUTE_MARGIN_DB = {
    "analysis-only": 6.0,
    "test-supported": 3.0,
}

# Surface finish aliases seen in radio-frequency build records.
MATERIAL_ALIASES = {
    "silver": "silver",
    "silver-plated": "silver",
    "ag": "silver",
    "gold": "gold",
    "gold-plated": "gold",
    "au": "gold",
    "copper": "copper",
    "cu": "copper",
    "alodine": "alodine",
    "alodine-1200": "alodine",
    "chromate-conversion": "alodine",
    "aluminium": "aluminium",
    "aluminum": "aluminium",
    "bare-aluminium": "aluminium",
}

# Monotone boundary curve for a silver surface: (frequency-gap product in
# GHz.mm, first-order boundary voltage in volts peak).
_SILVER_CURVE = (
    (0.05, 20.0),
    (0.1, 35.0),
    (0.2, 62.0),
    (0.5, 130.0),
    (1.0, 210.0),
    (2.0, 360.0),
    (5.0, 780.0),
    (10.0, 1400.0),
    (20.0, 2600.0),
    (50.0, 6000.0),
    (100.0, 11000.0),
)

# Surface-relative scaling of the boundary: a finish with a lower secondary
# yield sustains a higher voltage before the resonance closes.
MATERIAL_FACTORS = {
    "silver": 1.0,
    "gold": 1.05,
    "copper": 0.85,
    "alodine": 0.9,
    "aluminium": 0.75,
}

SUSCEPTIBILITY_CHARTS = {
    material: tuple((fd, volts * factor) for fd, volts in _SILVER_CURVE)
    for material, factor in MATERIAL_FACTORS.items()
}

VERDICT_COMPLIANT = "compliant"
VERDICT_INSUFFICIENT = "insufficient-margin"
VERDICT_PREDICTED = "multipaction-predicted"

REL_TOL = 1e-9


def _require_number(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return value


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return value


def reflection_magnitude(vswr):
    """Return the voltage reflection magnitude for a standing-wave ratio."""
    vswr = _require_number("vswr", vswr)
    if vswr < 1.0 and not math.isclose(vswr, 1.0, rel_tol=REL_TOL):
        raise ValueError("vswr must be at least 1.0, got %r" % (vswr,))
    vswr = max(vswr, 1.0)
    return (vswr - 1.0) / (vswr + 1.0)


def peak_voltage_from_power(power_w, impedance_ohm=DEFAULT_IMPEDANCE_OHM, vswr=1.0):
    """Return the peak line voltage for a forward power on a mismatched line."""
    power_w = _require_positive("power_w", power_w)
    impedance_ohm = _require_positive("impedance_ohm", impedance_ohm)
    gamma = reflection_magnitude(vswr)
    return math.sqrt(2.0 * power_w * impedance_ohm) * (1.0 + gamma)


def critical_region_voltage(
    power_w,
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
):
    """Return the peak gap voltage in the critical region.

    The field-concentration factor carries the ratio, taken from the
    electromagnetic field solution, between the gap voltage at the critical
    region and the line voltage feeding it.
    """
    field_concentration = _require_positive("field_concentration", field_concentration)
    return peak_voltage_from_power(power_w, impedance_ohm, vswr) * field_concentration


def frequency_gap_product_ghz_mm(frequency_ghz, gap_mm):
    """Return the frequency-gap product in GHz.mm."""
    frequency_ghz = _require_positive("frequency_ghz", frequency_ghz)
    gap_mm = _require_positive("gap_mm", gap_mm)
    return frequency_ghz * gap_mm


def normalize_material(material):
    """Map a surface-finish descriptor onto a charted finish family."""
    if not isinstance(material, str) or not material.strip():
        raise ValueError("material must be a non-empty string")
    key = material.strip().lower()
    if key not in MATERIAL_ALIASES:
        raise ValueError("no charted boundary for surface finish %r" % (material,))
    return MATERIAL_ALIASES[key]


def _validated_chart(material, chart):
    if chart is None:
        chart = SUSCEPTIBILITY_CHARTS[normalize_material(material)]
    points = tuple(chart)
    if len(points) < 2:
        raise ValueError("a boundary chart needs at least two points")
    previous_fd = None
    for fd, volts in points:
        fd = _require_positive("chart frequency-gap product", fd)
        _require_positive("chart boundary voltage", volts)
        if previous_fd is not None and fd <= previous_fd:
            raise ValueError("chart points must rise in frequency-gap product")
        previous_fd = fd
    return points


def chart_range(material, chart=None):
    """Return the charted (lowest, highest) frequency-gap product in GHz.mm."""
    points = _validated_chart(material, chart)
    return points[0][0], points[-1][0]


def threshold_voltage(material, fd_ghz_mm, chart=None):
    """Interpolate the boundary voltage at a frequency-gap product.

    Interpolation runs in log-log space, where the boundary is close to a
    straight line. A product outside the charted span raises ValueError rather
    than extrapolating an unsupported number.
    """
    points = _validated_chart(material, chart)
    fd = _require_positive("fd_ghz_mm", fd_ghz_mm)
    low, high = points[0][0], points[-1][0]
    if fd < low and not math.isclose(fd, low, rel_tol=REL_TOL):
        raise ValueError("frequency-gap product %r is below the charted span" % (fd,))
    if fd > high and not math.isclose(fd, high, rel_tol=REL_TOL):
        raise ValueError("frequency-gap product %r is above the charted span" % (fd,))
    fd = min(max(fd, low), high)
    for (fd0, v0), (fd1, v1) in zip(points, points[1:]):
        if fd0 <= fd <= fd1:
            if math.isclose(fd, fd0, rel_tol=REL_TOL):
                return v0
            if math.isclose(fd, fd1, rel_tol=REL_TOL):
                return v1
            span = math.log(fd1) - math.log(fd0)
            weight = (math.log(fd) - math.log(fd0)) / span
            return math.exp(math.log(v0) + weight * (math.log(v1) - math.log(v0)))
    raise ValueError("frequency-gap product %r not covered by the chart" % (fd,))


def margin_db(threshold_v, applied_v):
    """Return the decibel margin of a boundary voltage over an applied voltage."""
    threshold_v = _require_positive("threshold_v", threshold_v)
    applied_v = _require_positive("applied_v", applied_v)
    return 20.0 * math.log10(threshold_v / applied_v)


def required_margin_db(route, overrides=None):
    """Return the decibel margin owed by a verification route."""
    if not isinstance(route, str) or not route.strip():
        raise ValueError("route must be a non-empty string")
    key = route.strip().lower()
    table = dict(ROUTE_MARGIN_DB)
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("overrides must be a mapping of route to decibels")
        for name, value in overrides.items():
            table[str(name).strip().lower()] = _require_number("override margin", value)
    if key not in table:
        raise ValueError("unknown verification route %r" % (route,))
    return table[key]


def verdict_for(achieved_db, required_db):
    """Categorize an achieved margin against the margin owed."""
    achieved_db = _require_number("achieved_db", achieved_db)
    required_db = _require_number("required_db", required_db)
    if achieved_db >= required_db or math.isclose(
        achieved_db, required_db, rel_tol=REL_TOL, abs_tol=1e-12
    ):
        return VERDICT_COMPLIANT
    if achieved_db > 0.0:
        return VERDICT_INSUFFICIENT
    return VERDICT_PREDICTED


def assess_single_carrier(
    power_w,
    frequency_ghz,
    gap_mm,
    material,
    route="analysis-only",
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
    chart=None,
    region_id="unnamed-region",
):
    """Run the whole first-level single-carrier procedure for one region."""
    applied = critical_region_voltage(
        power_w, impedance_ohm, vswr, field_concentration
    )
    fd = frequency_gap_product_ghz_mm(frequency_ghz, gap_mm)
    boundary = threshold_voltage(material, fd, chart)
    achieved = margin_db(boundary, applied)
    owed = required_margin_db(route)
    verdict = verdict_for(achieved, owed)
    record = {
        "region_id": region_id,
        "surface_finish": normalize_material(material),
        "frequency_gap_product_ghz_mm": fd,
        "applied_voltage_v": applied,
        "threshold_voltage_v": boundary,
        "achieved_margin_db": achieved,
        "required_margin_db": owed,
        "verdict": verdict,
        "actions": [],
    }
    if verdict == VERDICT_INSUFFICIENT:
        record["actions"].append(
            "raise the gap, lower the carrier-power, or move to the second "
            "analysis level: margin %.3f dB is under the %.3f dB owed"
            % (achieved, owed)
        )
    elif verdict == VERDICT_PREDICTED:
        record["actions"].append(
            "redesign the critical region: the applied voltage sits on or above "
            "the boundary (%.3f dB)" % (achieved,)
        )
    return record


def maximum_allowable_power_w(
    frequency_ghz,
    gap_mm,
    material,
    route="analysis-only",
    impedance_ohm=DEFAULT_IMPEDANCE_OHM,
    vswr=1.0,
    field_concentration=1.0,
    chart=None,
):
    """Invert the procedure: the largest forward power that still holds margin."""
    fd = frequency_gap_product_ghz_mm(frequency_ghz, gap_mm)
    boundary = threshold_voltage(material, fd, chart)
    owed = required_margin_db(route)
    field_concentration = _require_positive("field_concentration", field_concentration)
    impedance_ohm = _require_positive("impedance_ohm", impedance_ohm)
    gamma = reflection_magnitude(vswr)
    allowed_v = boundary / (10.0 ** (owed / 20.0))
    line_v = allowed_v / (field_concentration * (1.0 + gamma))
    return (line_v * line_v) / (2.0 * impedance_ohm)


def worst_case_region(records):
    """Return the record holding the smallest achieved margin."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence")
    for record in records:
        if not isinstance(record, dict) or "achieved_margin_db" not in record:
            raise ValueError("each record must carry 'achieved_margin_db'")
    return min(records, key=lambda r: (r["achieved_margin_db"], r.get("region_id", "")))
