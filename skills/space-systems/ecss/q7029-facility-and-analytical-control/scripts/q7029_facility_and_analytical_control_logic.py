"""Facility blank, analytical calibration and contamination control for a
crew-compartment offgassing determination.

Anchor: ECSS-Q-ST-70-29 quality-assurance controls that decide whether the
numbers coming out of an offgassing run may be used at all. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the run record: the gross reading for each reported compound, the
   facility blank measured on the empty chamber through the same analytical
   train, and the quantitation limit of that train.
2. Subtract the blank from every reported compound, floor the net at zero, and
   mark a net that has fallen under the quantitation limit as not-quantified
   rather than carrying it forward as a small positive number.
3. Return the blank contribution as a fraction of the gross reading so a blank
   that dominates a result is visible before the net is used.
4. Grade the calibration: the number of curve points, the relative spread of
   the response factors across the curve, the age of the curve against its
   validity window, and the recovery of the check standard against nominal.
5. Test the chamber for carryover from the previous specimen.
6. Rank the findings by severity and close with one run disposition.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "MAX_BLANK_FRACTION",
    "MIN_CALIBRATION_POINTS",
    "MAX_RESPONSE_FACTOR_SPREAD",
    "CHECK_STANDARD_BAND",
    "MAX_CARRYOVER_FRACTION",
    "SEVERITY_ORDER",
    "blank_fraction",
    "net_of_blank",
    "response_factor_spread",
    "calibration_validity_fraction",
    "check_standard_recovery",
    "carryover_fraction",
    "calibration_findings",
    "contamination_findings",
    "run_disposition",
    "assess_facility_and_analytical_control",
]

# A ratio compared with its bound is a quotient of measured numbers: an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the control limit.
BOUND_TOLERANCE = 1e-9

# The blank is background, not signal. Above this fraction of the gross reading
# the reported compound is mostly the facility and the net is not usable.
MAX_BLANK_FRACTION = 0.10

# A curve drawn through fewer points than this cannot show its own curvature.
MIN_CALIBRATION_POINTS = 5

# Relative spread of the response factors across the calibration points.
MAX_RESPONSE_FACTOR_SPREAD = 0.20

# Acceptance band on the recovered check standard, as a fraction of nominal.
CHECK_STANDARD_BAND = (0.85, 1.15)

# Residue found in the chamber blank run after a specimen, as a fraction of
# that specimen's gross reading.
MAX_CARRYOVER_FRACTION = 0.01

SEVERITY_ORDER = {"critical": 0, "major": 1, "minor": 2}


def _real(label, value):
    """Return value as a finite float, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(label, value):
    """Return value as a strictly positive finite float, or raise ValueError."""
    out = _real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _non_negative(label, value):
    """Return value as a non-negative finite float, or raise ValueError."""
    out = _real(label, value)
    if out < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return out


def _at_or_below(value, bound):
    """True when value is below bound or lands on it within tolerance."""
    return value < bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def _at_or_above(value, bound):
    """True when value is above bound or lands on it within tolerance."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def blank_fraction(gross_ug, blank_ug):
    """Return the facility blank as a fraction of the gross reading."""
    gross = _positive("gross_ug", gross_ug)
    blank = _non_negative("blank_ug", blank_ug)
    return blank / gross


def net_of_blank(gross_ug, blank_ug, quantitation_limit_ug):
    """Subtract the facility blank and report whether the net is quantifiable."""
    gross = _positive("gross_ug", gross_ug)
    blank = _non_negative("blank_ug", blank_ug)
    limit = _positive("quantitation_limit_ug", quantitation_limit_ug)
    raw = gross - blank
    net = raw if raw > 0.0 else 0.0
    quantified = _at_or_above(net, limit)
    return {
        "gross_ug": gross,
        "blank_ug": blank,
        "net_ug": net,
        "blank_fraction": blank / gross,
        "quantitation_limit_ug": limit,
        "quantified": quantified,
        "reported_ug": net if quantified else 0.0,
    }


def response_factor_spread(response_factors):
    """Return the relative spread of the calibration response factors."""
    if not isinstance(response_factors, (list, tuple)):
        raise ValueError("response_factors must be a sequence")
    if len(response_factors) < 2:
        raise ValueError("response_factors needs at least two points")
    values = [
        _positive("response_factors[%d]" % i, v) for i, v in enumerate(response_factors)
    ]
    mean = sum(values) / len(values)
    variance = sum((v - mean) ** 2 for v in values) / (len(values) - 1)
    return math.sqrt(variance) / mean


def calibration_validity_fraction(days_since_calibration, validity_days):
    """Return the age of the curve as a fraction of its validity window."""
    age = _non_negative("days_since_calibration", days_since_calibration)
    window = _positive("validity_days", validity_days)
    return age / window


def check_standard_recovery(measured_ug, nominal_ug):
    """Return the recovered check standard as a fraction of its nominal."""
    measured = _non_negative("measured_ug", measured_ug)
    nominal = _positive("nominal_ug", nominal_ug)
    return measured / nominal


def carryover_fraction(residue_ug, previous_gross_ug):
    """Return chamber residue as a fraction of the previous specimen reading."""
    residue = _non_negative("residue_ug", residue_ug)
    previous = _positive("previous_gross_ug", previous_gross_ug)
    return residue / previous


def calibration_findings(curve):
    """Return the findings raised by one calibration record."""
    if not isinstance(curve, dict):
        raise ValueError("curve must be a mapping")
    for key in ("response_factors", "days_since_calibration", "validity_days",
                "check_standard_measured_ug", "check_standard_nominal_ug"):
        if key not in curve:
            raise ValueError("curve missing required key '%s'" % key)
    findings = []
    factors = curve["response_factors"]
    spread = response_factor_spread(factors)
    if len(factors) < MIN_CALIBRATION_POINTS:
        findings.append({
            "severity": "major",
            "control": "calibration-points",
            "detail": "curve drawn through %d points, fewer than the %d owed"
                      % (len(factors), MIN_CALIBRATION_POINTS),
        })
    if not _at_or_below(spread, MAX_RESPONSE_FACTOR_SPREAD):
        findings.append({
            "severity": "critical",
            "control": "response-factor-spread",
            "detail": "response factors spread %.4f, above the %.4f limit"
                      % (spread, MAX_RESPONSE_FACTOR_SPREAD),
        })
    age = calibration_validity_fraction(
        curve["days_since_calibration"], curve["validity_days"]
    )
    if not _at_or_below(age, 1.0):
        findings.append({
            "severity": "critical",
            "control": "calibration-validity",
            "detail": "curve is %.3f of its validity window old" % age,
        })
    recovery = check_standard_recovery(
        curve["check_standard_measured_ug"], curve["check_standard_nominal_ug"]
    )
    low, high = CHECK_STANDARD_BAND
    if not (_at_or_above(recovery, low) and _at_or_below(recovery, high)):
        findings.append({
            "severity": "critical",
            "control": "check-standard-recovery",
            "detail": "check standard recovered at %.4f of nominal, outside %.2f-%.2f"
                      % (recovery, low, high),
        })
    return findings


def contamination_findings(residue_ug, previous_gross_ug, chamber_cleaned):
    """Return the findings raised by the carryover and cleanliness record."""
    if not isinstance(chamber_cleaned, bool):
        raise ValueError("chamber_cleaned must be a boolean")
    findings = []
    ratio = carryover_fraction(residue_ug, previous_gross_ug)
    if not _at_or_below(ratio, MAX_CARRYOVER_FRACTION):
        findings.append({
            "severity": "critical",
            "control": "chamber-carryover",
            "detail": "residue is %.4f of the previous specimen reading, above %.4f"
                      % (ratio, MAX_CARRYOVER_FRACTION),
        })
    if not chamber_cleaned:
        findings.append({
            "severity": "major",
            "control": "chamber-cleaning",
            "detail": "chamber was not cleaned and baked out before the run",
        })
    return findings


def run_disposition(findings):
    """Return the run disposition implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for item in findings:
        if not isinstance(item, dict) or "severity" not in item:
            raise ValueError("each finding must be a mapping carrying 'severity'")
        severity = item["severity"]
        if severity not in SEVERITY_ORDER:
            raise ValueError("unknown severity %r" % (severity,))
        severities.add(severity)
    if "critical" in severities:
        return "run-invalid"
    if severities:
        return "run-valid-with-actions"
    return "run-valid"


def assess_facility_and_analytical_control(spec):
    """Grade one offgassing run's facility, calibration and contamination controls.

    spec keys: compounds (list of {name, gross_ug, blank_ug}),
    quantitation_limit_ug, calibration (mapping), residue_ug,
    previous_gross_ug, chamber_cleaned.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("compounds", "quantitation_limit_ug", "calibration",
                "residue_ug", "previous_gross_ug", "chamber_cleaned"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    compounds = spec["compounds"]
    if not isinstance(compounds, (list, tuple)) or not compounds:
        raise ValueError("spec['compounds'] must be a non-empty sequence")
    limit = spec["quantitation_limit_ug"]
    findings = []
    records = []
    for index, compound in enumerate(compounds):
        if not isinstance(compound, dict):
            raise ValueError("compounds[%d] must be a mapping" % index)
        for key in ("name", "gross_ug", "blank_ug"):
            if key not in compound:
                raise ValueError("compounds[%d] missing '%s'" % (index, key))
        name = compound["name"]
        if not isinstance(name, str) or not name.strip():
            raise ValueError("compounds[%d]['name'] must be a non-empty string" % index)
        record = net_of_blank(compound["gross_ug"], compound["blank_ug"], limit)
        record["name"] = name.strip()
        records.append(record)
        if not _at_or_below(record["blank_fraction"], MAX_BLANK_FRACTION):
            findings.append({
                "severity": "major",
                "control": "facility-blank",
                "detail": "%s is %.3f facility blank, above the %.3f limit"
                          % (record["name"], record["blank_fraction"], MAX_BLANK_FRACTION),
            })
    findings.extend(calibration_findings(spec["calibration"]))
    findings.extend(contamination_findings(
        spec["residue_ug"], spec["previous_gross_ug"], spec["chamber_cleaned"]
    ))
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {
        "compounds": records,
        "quantified": [r["name"] for r in records if r["quantified"]],
        "not_quantified": [r["name"] for r in records if not r["quantified"]],
        "findings": findings,
        "disposition": run_disposition(findings),
    }
