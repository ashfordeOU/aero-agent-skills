"""Closed-loop stability margins for a spacecraft mechanism control system.

Anchor: ECSS-E-ST-33-01C clauses 4.7.8.1 and 4.7.8.2 (a closed-loop mechanism
control system keeps a gain margin of a factor of two, six decibels, and a
phase margin of thirty degrees, at the worst case of its parameter range).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate an open-loop frequency response: strictly increasing frequency,
   positive magnitude, phase in degrees and monotonic enough to cross.
2. Find the gain crossover -- the frequency where the open-loop magnitude
   passes unity -- by log-frequency interpolation on the log magnitude, and
   read the phase there. The phase margin is that phase measured up from the
   half-turn lag.
3. Find the phase crossover -- the frequency where the phase passes the
   half-turn lag -- and read the magnitude there. The gain margin is the
   reciprocal of that magnitude.
4. Repeat for every declared worst-case parameter case (hot and cold, maximum
   and minimum inertia, end-of-life friction) and retain the case with the
   smallest margin of each kind.
5. Grade both retained margins against the required values.
"""

import math

__all__ = [
    "REQUIRED_GAIN_MARGIN",
    "REQUIRED_GAIN_MARGIN_DB",
    "REQUIRED_PHASE_MARGIN_DEG",
    "MARGIN_TOLERANCE",
    "PHASE_TOLERANCE_DEG",
    "HALF_TURN_DEG",
    "validate_response",
    "to_db",
    "from_db",
    "interpolate_at_unity_gain",
    "interpolate_at_phase_crossover",
    "gain_margin",
    "phase_margin_deg",
    "evaluate_case",
    "worst_case_margins",
    "assess_control_margins",
]

# A closed-loop mechanism control system keeps at least this much gain margin
# as a linear factor, and the decibel value it corresponds to.
REQUIRED_GAIN_MARGIN = 2.0
REQUIRED_GAIN_MARGIN_DB = 20.0 * math.log10(2.0)

# ... and at least this much phase margin, in degrees.
REQUIRED_PHASE_MARGIN_DEG = 30.0

# The lag at which the open loop inverts the feedback sign.
HALF_TURN_DEG = -180.0

# Margin comparisons derive from logarithms and interpolation, so an exact
# physical equality can land a few ULPs on the wrong side. Absorb the
# representation error here rather than relaxing the engineering limit.
MARGIN_TOLERANCE = 1e-9
PHASE_TOLERANCE_DEG = 1e-9


def _finite(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(label, value):
    """Return value as a positive finite float or raise ValueError."""
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def to_db(magnitude):
    """Return a linear magnitude expressed in decibels."""
    return 20.0 * math.log10(_positive("magnitude", magnitude))


def from_db(magnitude_db):
    """Return a decibel magnitude expressed as a linear factor."""
    return 10.0 ** (_finite("magnitude_db", magnitude_db) / 20.0)


def validate_response(response, name="response"):
    """Return a validated open-loop response as a list of (f, mag, phase_deg)."""
    if not isinstance(response, (list, tuple)) or len(response) < 2:
        raise ValueError("%s needs at least two frequency points" % name)
    points = []
    for index, point in enumerate(response):
        if not isinstance(point, (list, tuple)) or len(point) != 3:
            raise ValueError(
                "%s[%d] must be a (frequency_hz, magnitude, phase_deg) triple" % (name, index)
            )
        frequency = _positive("%s[%d] frequency_hz" % (name, index), point[0])
        magnitude = _positive("%s[%d] magnitude" % (name, index), point[1])
        phase = _finite("%s[%d] phase_deg" % (name, index), point[2])
        points.append((frequency, magnitude, phase))
    for index in range(1, len(points)):
        if points[index][0] <= points[index - 1][0]:
            raise ValueError("%s frequencies must strictly increase (index %d)" % (name, index))
    return points


def _log_interpolate(x0, y0, x1, y1, target_y):
    """Return the log-x abscissa where a log-x/linear-y segment reaches target_y."""
    if y1 == y0:
        return x0
    fraction = (target_y - y0) / (y1 - y0)
    return math.exp(math.log(x0) + fraction * (math.log(x1) - math.log(x0)))


def interpolate_at_unity_gain(response, name="response"):
    """Return (frequency, phase_deg) where the open-loop magnitude passes unity."""
    points = validate_response(response, name)
    for index in range(1, len(points)):
        f0, m0, p0 = points[index - 1]
        f1, m1, p1 = points[index]
        db0, db1 = to_db(m0), to_db(m1)
        # A tabulated point sitting exactly on the crossing is returned as it
        # stands: interpolating onto a point we already have would replace an
        # exact value with a rounded one.
        if db0 == 0.0:
            return (f0, p0)
        if db1 == 0.0:
            return (f1, p1)
        if db0 * db1 < 0.0:
            frequency = _log_interpolate(f0, db0, f1, db1, 0.0)
            fraction = (0.0 - db0) / (db1 - db0)
            return (frequency, p0 + fraction * (p1 - p0))
    raise ValueError("%s never crosses unity gain over the tabulated band" % name)


def interpolate_at_phase_crossover(response, name="response"):
    """Return (frequency, magnitude) where the open-loop phase passes the half turn."""
    points = validate_response(response, name)
    for index in range(1, len(points)):
        f0, m0, p0 = points[index - 1]
        f1, m1, p1 = points[index]
        d0 = p0 - HALF_TURN_DEG
        d1 = p1 - HALF_TURN_DEG
        # As above: an exactly tabulated crossing keeps its own magnitude.
        if d0 == 0.0:
            return (f0, m0)
        if d1 == 0.0:
            return (f1, m1)
        if d0 * d1 < 0.0:
            frequency = _log_interpolate(f0, d0, f1, d1, 0.0)
            fraction = (0.0 - d0) / (d1 - d0)
            db = to_db(m0) + fraction * (to_db(m1) - to_db(m0))
            return (frequency, from_db(db))
    raise ValueError("%s never crosses the half-turn phase lag over the tabulated band" % name)


def gain_margin(response, name="response"):
    """Return the gain margin as a linear factor and its frequency."""
    frequency, magnitude = interpolate_at_phase_crossover(response, name)
    return {"frequency_hz": frequency, "magnitude": magnitude,
            "margin": 1.0 / magnitude, "margin_db": -to_db(magnitude)}


def phase_margin_deg(response, name="response"):
    """Return the phase margin in degrees and its frequency."""
    frequency, phase = interpolate_at_unity_gain(response, name)
    return {"frequency_hz": frequency, "phase_deg": phase,
            "margin_deg": phase - HALF_TURN_DEG}


def evaluate_case(case):
    """Return the stability margins of one worst-case parameter case.

    Required keys: id, response (a sequence of (f_hz, magnitude, phase_deg)).
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    for key in ("id", "response"):
        if key not in case:
            raise ValueError("case missing required key '%s'" % key)
    identifier = case["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("case id must be a non-empty string")
    name = identifier.strip()
    gain = gain_margin(case["response"], name)
    phase = phase_margin_deg(case["response"], name)
    return {
        "id": name,
        "gain_margin": gain["margin"],
        "gain_margin_db": gain["margin_db"],
        "gain_crossover_hz": phase["frequency_hz"],
        "phase_crossover_hz": gain["frequency_hz"],
        "phase_margin_deg": phase["margin_deg"],
    }


def worst_case_margins(cases):
    """Return the smallest gain and phase margin across the parameter cases."""
    if not isinstance(cases, (list, tuple)) or not cases:
        raise ValueError("cases must be a non-empty sequence")
    records = []
    seen = set()
    for case in cases:
        record = evaluate_case(case)
        if record["id"] in seen:
            raise ValueError("duplicate case id '%s'" % record["id"])
        seen.add(record["id"])
        records.append(record)
    worst_gain = records[0]
    worst_phase = records[0]
    for record in records[1:]:
        if math.isclose(record["gain_margin"], worst_gain["gain_margin"],
                        rel_tol=1e-12, abs_tol=0.0):
            if record["id"] < worst_gain["id"]:
                worst_gain = record
        elif record["gain_margin"] < worst_gain["gain_margin"]:
            worst_gain = record
        if math.isclose(record["phase_margin_deg"], worst_phase["phase_margin_deg"],
                        rel_tol=1e-12, abs_tol=0.0):
            if record["id"] < worst_phase["id"]:
                worst_phase = record
        elif record["phase_margin_deg"] < worst_phase["phase_margin_deg"]:
            worst_phase = record
    return {"records": records, "worst_gain": worst_gain, "worst_phase": worst_phase}


def assess_control_margins(spec):
    """Run the full clause 4.7.8.1 / 4.7.8.2 stability-margin assessment.

    spec keys: cases (non-empty sequence). Optional: required_gain_margin,
    required_phase_margin_deg.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "cases" not in spec:
        raise ValueError("spec missing required key 'cases'")
    required_gain = _positive(
        "required_gain_margin", spec.get("required_gain_margin", REQUIRED_GAIN_MARGIN)
    )
    required_phase = _finite(
        "required_phase_margin_deg",
        spec.get("required_phase_margin_deg", REQUIRED_PHASE_MARGIN_DEG),
    )
    if required_phase <= 0.0:
        raise ValueError("required_phase_margin_deg must be positive")
    summary = worst_case_margins(spec["cases"])
    gain = summary["worst_gain"]["gain_margin"]
    phase = summary["worst_phase"]["phase_margin_deg"]
    gain_ok = gain > required_gain or math.isclose(
        gain, required_gain, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE
    )
    phase_ok = phase > required_phase or math.isclose(
        phase, required_phase, rel_tol=0.0, abs_tol=PHASE_TOLERANCE_DEG
    )
    findings = []
    if not gain_ok:
        findings.append(
            "worst case '%s' leaves a gain margin of %.4f (%.3f dB) against the required "
            "%.4f (%.3f dB)"
            % (summary["worst_gain"]["id"], gain, to_db(gain), required_gain,
               to_db(required_gain))
        )
    if not phase_ok:
        findings.append(
            "worst case '%s' leaves a phase margin of %.3f deg against the required %.3f deg"
            % (summary["worst_phase"]["id"], phase, required_phase)
        )
    if len(summary["records"]) < 2:
        findings.append(
            "only one parameter case supplied; a worst-case margin cannot be identified "
            "from a single case"
        )
    return {
        "records": summary["records"],
        "worst_gain_case": summary["worst_gain"]["id"],
        "worst_phase_case": summary["worst_phase"]["id"],
        "gain_margin": gain,
        "gain_margin_db": to_db(gain),
        "phase_margin_deg": phase,
        "required_gain_margin": required_gain,
        "required_phase_margin_deg": required_phase,
        "gain_ok": gain_ok,
        "phase_ok": phase_ok,
        "findings": findings,
        "compliant": not findings,
    }
