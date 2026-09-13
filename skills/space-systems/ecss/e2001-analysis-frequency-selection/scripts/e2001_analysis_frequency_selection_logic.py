"""In-band worst-case frequency selection for multipaction design analysis.

Anchor: ECSS-E-ST-20-01C clause 5.3.1 (design analysis -- choosing the in-band
frequency that yields the lowest breakdown power). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the operating band and the critical gap of the component.
2. Build the candidate frequency set: both band edges, a uniform sweep across
   the band, and every declared in-band singular frequency (filter resonance,
   higher-order-mode cut-on, tuning-screw peak) where the field concentration
   differs from the smooth sweep value.
3. For each candidate, form the frequency-gap product f*d (GHz*mm) of the
   critical gap and read the breakdown-voltage threshold from the surface
   susceptibility curve by log-log interpolation.
4. Convert the voltage threshold into a breakdown power through the local
   characteristic impedance and the voltage-magnification factor of the
   component at that frequency: P = V^2 / (2 * Z * M^2).
5. Select the candidate with the lowest breakdown power (ties broken by the
   lowest frequency) and report the achieved margin against the operating
   power, compared with the required design margin in dB.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE_DB",
    "validate_band",
    "frequency_gap_product",
    "interpolate_log_log",
    "interpolate_linear",
    "threshold_voltage",
    "breakdown_power_w",
    "candidate_frequencies",
    "evaluate_candidate",
    "sweep_band",
    "select_worst_case",
    "margin_db",
    "assess_frequency_selection",
]

# Margin comparisons are a difference of logarithms: a physically exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the engineering limit.
MARGIN_TOLERANCE_DB = 1e-9

# A candidate set that does not bracket the band edges cannot be a worst-case
# search; the sweep must contain at least this many points.
MIN_SWEEP_POINTS = 3


def validate_band(f_min_ghz, f_max_ghz):
    """Return the validated (f_min, f_max) operating band in GHz."""
    for label, value in (("f_min_ghz", f_min_ghz), ("f_max_ghz", f_max_ghz)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
        if float(value) <= 0.0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    f_min = float(f_min_ghz)
    f_max = float(f_max_ghz)
    if f_min > f_max:
        raise ValueError("f_min_ghz %g exceeds f_max_ghz %g" % (f_min, f_max))
    return (f_min, f_max)


def frequency_gap_product(frequency_ghz, gap_mm):
    """Return the frequency-gap product in GHz*mm for the critical gap."""
    if not isinstance(frequency_ghz, (int, float)) or isinstance(frequency_ghz, bool):
        raise ValueError("frequency_ghz must be a real number")
    if not isinstance(gap_mm, (int, float)) or isinstance(gap_mm, bool):
        raise ValueError("gap_mm must be a real number")
    f = float(frequency_ghz)
    d = float(gap_mm)
    if not math.isfinite(f) or f <= 0.0:
        raise ValueError("frequency_ghz must be positive and finite, got %r" % (frequency_ghz,))
    if not math.isfinite(d) or d <= 0.0:
        raise ValueError("gap_mm must be positive and finite, got %r" % (gap_mm,))
    return f * d


def _validate_table(table, name):
    """Return a table of (x, y) pairs, strictly increasing in x, all positive."""
    if not isinstance(table, (list, tuple)) or len(table) < 2:
        raise ValueError("%s needs at least two (x, y) points" % name)
    points = []
    for i, item in enumerate(table):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("%s[%d] must be an (x, y) pair" % (name, i))
        x, y = item
        if not isinstance(x, (int, float)) or isinstance(x, bool):
            raise ValueError("%s[%d] abscissa must be a real number" % (name, i))
        if not isinstance(y, (int, float)) or isinstance(y, bool):
            raise ValueError("%s[%d] ordinate must be a real number" % (name, i))
        x = float(x)
        y = float(y)
        if not math.isfinite(x) or not math.isfinite(y):
            raise ValueError("%s[%d] must be finite" % (name, i))
        if x <= 0.0 or y <= 0.0:
            raise ValueError("%s[%d] must be strictly positive, got (%g, %g)" % (name, i, x, y))
        points.append((x, y))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("%s abscissae must strictly increase (index %d)" % (name, i))
    return points


def interpolate_log_log(table, x, name="curve"):
    """Log-log interpolate the table at x; refuse to extrapolate."""
    points = _validate_table(table, name)
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        raise ValueError("interpolation abscissa must be a real number")
    xv = float(x)
    if not math.isfinite(xv) or xv <= 0.0:
        raise ValueError("interpolation abscissa must be positive and finite, got %r" % (x,))
    lo_x, hi_x = points[0][0], points[-1][0]
    if xv < lo_x or xv > hi_x:
        raise ValueError(
            "%s is tabulated over [%g, %g]; %g is outside it, extrapolation refused"
            % (name, lo_x, hi_x, xv)
        )
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if xv <= x1:
            if xv == x0:
                return y0
            if xv == x1:
                return y1
            t = (math.log(xv) - math.log(x0)) / (math.log(x1) - math.log(x0))
            return math.exp(math.log(y0) + t * (math.log(y1) - math.log(y0)))
    return points[-1][1]


def interpolate_linear(table, x, name="table"):
    """Linearly interpolate the table at x; refuse to extrapolate."""
    points = _validate_table(table, name)
    if not isinstance(x, (int, float)) or isinstance(x, bool):
        raise ValueError("interpolation abscissa must be a real number")
    xv = float(x)
    if not math.isfinite(xv) or xv <= 0.0:
        raise ValueError("interpolation abscissa must be positive and finite, got %r" % (x,))
    lo_x, hi_x = points[0][0], points[-1][0]
    if xv < lo_x or xv > hi_x:
        raise ValueError(
            "%s is tabulated over [%g, %g]; %g is outside it, extrapolation refused"
            % (name, lo_x, hi_x, xv)
        )
    for i in range(1, len(points)):
        x0, y0 = points[i - 1]
        x1, y1 = points[i]
        if xv <= x1:
            if x1 == x0:
                return y0
            t = (xv - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    return points[-1][1]


def threshold_voltage(susceptibility_curve, fd_ghz_mm):
    """Return the breakdown-voltage threshold in volts at a frequency-gap product."""
    return interpolate_log_log(susceptibility_curve, fd_ghz_mm, name="susceptibility-curve")


def breakdown_power_w(voltage_v, impedance_ohm, magnification=1.0):
    """Convert a gap voltage threshold into the equivalent breakdown power."""
    for label, value in (
        ("voltage_v", voltage_v),
        ("impedance_ohm", impedance_ohm),
        ("magnification", magnification),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    v = float(voltage_v)
    z = float(impedance_ohm)
    m = float(magnification)
    return (v * v) / (2.0 * z * m * m)


def candidate_frequencies(f_min_ghz, f_max_ghz, sweep_points=5, singular_frequencies=None):
    """Return the sorted candidate frequency set for the worst-case search."""
    f_min, f_max = validate_band(f_min_ghz, f_max_ghz)
    if not isinstance(sweep_points, int) or isinstance(sweep_points, bool):
        raise ValueError("sweep_points must be an integer")
    if sweep_points < MIN_SWEEP_POINTS:
        raise ValueError(
            "sweep_points must be at least %d to bracket the band, got %d"
            % (MIN_SWEEP_POINTS, sweep_points)
        )
    if f_min == f_max:
        return [f_min]
    step = (f_max - f_min) / (sweep_points - 1)
    values = [f_min + i * step for i in range(sweep_points - 1)]
    values.append(f_max)
    for extra in singular_frequencies or []:
        if not isinstance(extra, (int, float)) or isinstance(extra, bool):
            raise ValueError("singular frequency must be a real number, got %r" % (extra,))
        ev = float(extra)
        if not math.isfinite(ev):
            raise ValueError("singular frequency must be finite")
        if ev < f_min or ev > f_max:
            raise ValueError(
                "singular frequency %g GHz is outside the band [%g, %g]" % (ev, f_min, f_max)
            )
        values.append(ev)
    unique = []
    for value in sorted(values):
        if not unique or not math.isclose(value, unique[-1], rel_tol=1e-12, abs_tol=1e-12):
            unique.append(value)
    return unique


def evaluate_candidate(frequency_ghz, gap_mm, susceptibility_curve,
                       impedance_table, magnification_table=None):
    """Evaluate one candidate frequency and return its breakdown-power record."""
    fd = frequency_gap_product(frequency_ghz, gap_mm)
    v_th = threshold_voltage(susceptibility_curve, fd)
    z = interpolate_linear(impedance_table, float(frequency_ghz), name="impedance-table")
    if magnification_table is None:
        mag = 1.0
    else:
        mag = interpolate_linear(
            magnification_table, float(frequency_ghz), name="magnification-table"
        )
    return {
        "frequency_ghz": float(frequency_ghz),
        "fd_ghz_mm": fd,
        "threshold_voltage_v": v_th,
        "impedance_ohm": z,
        "magnification": mag,
        "breakdown_power_w": breakdown_power_w(v_th, z, mag),
    }


def sweep_band(band, gap_mm, susceptibility_curve, impedance_table,
               magnification_table=None, sweep_points=5, singular_frequencies=None):
    """Return the ordered list of candidate records across the band."""
    f_min, f_max = validate_band(band[0], band[1])
    frequencies = candidate_frequencies(f_min, f_max, sweep_points, singular_frequencies)
    return [
        evaluate_candidate(f, gap_mm, susceptibility_curve, impedance_table, magnification_table)
        for f in frequencies
    ]


def select_worst_case(records):
    """Return the record with the lowest breakdown power (lowest frequency wins ties)."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of candidate records")
    worst = None
    for record in records:
        if not isinstance(record, dict) or "breakdown_power_w" not in record:
            raise ValueError("each record must be a mapping carrying 'breakdown_power_w'")
        if worst is None:
            worst = record
            continue
        power = record["breakdown_power_w"]
        best = worst["breakdown_power_w"]
        if math.isclose(power, best, rel_tol=1e-12, abs_tol=0.0):
            if record["frequency_ghz"] < worst["frequency_ghz"]:
                worst = record
        elif power < best:
            worst = record
    return worst


def margin_db(breakdown_power_value, operating_power_w):
    """Return the achieved multipaction margin in dB."""
    for label, value in (
        ("breakdown_power", breakdown_power_value),
        ("operating_power_w", operating_power_w),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return 10.0 * math.log10(float(breakdown_power_value) / float(operating_power_w))


def assess_frequency_selection(spec):
    """Run the full clause 5.3.1 frequency-selection assessment.

    spec keys: band (pair, GHz), gap_mm, susceptibility_curve, impedance_table,
    optional magnification_table, sweep_points, singular_frequencies,
    operating_power_w, required_margin_db.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("band", "gap_mm", "susceptibility_curve", "impedance_table",
                "operating_power_w", "required_margin_db"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    band = spec["band"]
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("spec['band'] must be a (f_min_ghz, f_max_ghz) pair")
    required = spec["required_margin_db"]
    if not isinstance(required, (int, float)) or isinstance(required, bool):
        raise ValueError("required_margin_db must be a real number")
    if not math.isfinite(float(required)) or float(required) < 0.0:
        raise ValueError("required_margin_db must be non-negative and finite")
    records = sweep_band(
        band,
        spec["gap_mm"],
        spec["susceptibility_curve"],
        spec["impedance_table"],
        spec.get("magnification_table"),
        spec.get("sweep_points", 5),
        spec.get("singular_frequencies"),
    )
    worst = select_worst_case(records)
    achieved = margin_db(worst["breakdown_power_w"], spec["operating_power_w"])
    required = float(required)
    compliant = achieved > required or math.isclose(
        achieved, required, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE_DB
    )
    findings = []
    if not compliant:
        findings.append(
            "breakdown power at the worst-case frequency %.4f GHz gives %.3f dB, "
            "below the required %.3f dB" % (worst["frequency_ghz"], achieved, required)
        )
    edge_only = len(records) <= 2
    if edge_only:
        findings.append("candidate set covers the band edges only; no in-band sweep performed")
    return {
        "records": records,
        "worst_case": worst,
        "achieved_margin_db": achieved,
        "required_margin_db": required,
        "compliant": compliant and not edge_only,
        "findings": findings,
    }
