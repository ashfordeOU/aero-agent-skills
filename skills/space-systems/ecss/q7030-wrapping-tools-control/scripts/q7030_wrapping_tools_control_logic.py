"""Control of the tools that make solderless wrapped connections.

Anchor: ECSS-Q-ST-70-30 requirements on wrapping tools -- bit and sleeve
selection for the wire and post in hand, calibration standing, wear life, the
set-up sample taken before production, and the wrap tension the tool delivers.
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Test that the fitted bit and sleeve cover the conductor gauge and the post
   section actually being wrapped, because a bit outside its coverage forms the
   turns without reaching the tension the connection depends on.
2. Return the calibration standing of the tool from the days since its last
   calibration, its interval and the recall grace, as one of in-calibration,
   due, or out-of-calibration.
3. Return the wear consumed as a fraction of the bit's life in wraps, so a bit
   near the end of its life is withdrawn before it starts producing loose turns
   rather than after.
4. Grade the set-up sample the operator makes before production: the turn count,
   overlapping turns, and end play against its allowance.
5. Return the measured wrap tension as a fraction of nominal and test it against
   the acceptance band.
6. Rank the findings by severity and close with one tool disposition.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "DEFAULT_CALIBRATION_INTERVAL_DAYS",
    "DEFAULT_GRACE_DAYS",
    "WEAR_WARNING_FRACTION",
    "TENSION_BAND",
    "CALIBRATION_STATUSES",
    "SEVERITY_ORDER",
    "bit_coverage_findings",
    "calibration_status",
    "calibration_findings",
    "wear_fraction",
    "wear_findings",
    "setup_sample_findings",
    "tension_ratio",
    "tension_findings",
    "tool_disposition",
    "assess_tool_control",
]

# Ratios compared with a bound are quotients of measured numbers; an exact
# equality can land a few ULPs on the wrong side. Absorb the representation
# error here instead of relaxing the control limit.
BOUND_TOLERANCE = 1e-9

DEFAULT_CALIBRATION_INTERVAL_DAYS = 180.0
DEFAULT_GRACE_DAYS = 5.0

# Wear at or above this fraction of the bit's life is an action while the tool
# is still usable; at or above the full life it is a withdrawal.
WEAR_WARNING_FRACTION = 0.9

TENSION_BAND = (0.90, 1.10)

CALIBRATION_STATUSES = ("in-calibration", "due", "out-of-calibration")

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


def _count(label, value):
    """Return a non-negative integer count, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return value


def _at_or_below(value, bound):
    """True when value is below bound or lands on it within tolerance."""
    return value < bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def _at_or_above(value, bound):
    """True when value is above bound or lands on it within tolerance."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def bit_coverage_findings(bit, gauge_awg, post_diagonal_mm):
    """Return the findings raised by the fitted bit and sleeve."""
    if not isinstance(bit, dict):
        raise ValueError("bit must be a mapping")
    for key in ("part_number", "gauge_span", "post_diagonal_span_mm", "certified"):
        if key not in bit:
            raise ValueError("bit missing required key '%s'" % key)
    part = bit["part_number"]
    if not isinstance(part, str) or not part.strip():
        raise ValueError("bit['part_number'] must be a non-empty string")
    span = bit["gauge_span"]
    if not isinstance(span, (list, tuple)) or len(span) != 2:
        raise ValueError("bit['gauge_span'] must be a (thickest_awg, thinnest_awg) pair")
    thickest, thinnest = span
    for label, value in (("thickest", thickest), ("thinnest", thinnest)):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("bit gauge_span %s must be an integer" % label)
    if thickest > thinnest:
        raise ValueError("bit gauge_span must read (thickest_awg, thinnest_awg)")
    if isinstance(gauge_awg, bool) or not isinstance(gauge_awg, int):
        raise ValueError("gauge_awg must be an integer, got %r" % (gauge_awg,))
    diagonal_span = bit["post_diagonal_span_mm"]
    if not isinstance(diagonal_span, (list, tuple)) or len(diagonal_span) != 2:
        raise ValueError("bit['post_diagonal_span_mm'] must be a (low, high) pair")
    low = _positive("post_diagonal_span_mm low", diagonal_span[0])
    high = _positive("post_diagonal_span_mm high", diagonal_span[1])
    if low > high:
        raise ValueError("bit post_diagonal_span_mm must read (low, high)")
    diagonal = _positive("post_diagonal_mm", post_diagonal_mm)
    certified = bit["certified"]
    if not isinstance(certified, bool):
        raise ValueError("bit['certified'] must be a boolean")
    findings = []
    if not certified:
        findings.append({
            "severity": "critical",
            "control": "bit-certification",
            "detail": "bit %s is not on the certified tool list" % part.strip(),
        })
    if gauge_awg < thickest or gauge_awg > thinnest:
        findings.append({
            "severity": "critical",
            "control": "bit-gauge-coverage",
            "detail": "bit %s covers AWG %d to AWG %d, the wire is AWG %d"
                      % (part.strip(), thickest, thinnest, gauge_awg),
        })
    if not (_at_or_above(diagonal, low) and _at_or_below(diagonal, high)):
        findings.append({
            "severity": "critical",
            "control": "bit-post-coverage",
            "detail": "bit %s covers post diagonals %.4f to %.4f mm, the post is %.4f mm"
                      % (part.strip(), low, high, diagonal),
        })
    return findings


def calibration_status(days_since_calibration, interval_days, grace_days=DEFAULT_GRACE_DAYS):
    """Return the calibration standing of the tool."""
    age = _non_negative("days_since_calibration", days_since_calibration)
    interval = _positive("interval_days", interval_days)
    grace = _non_negative("grace_days", grace_days)
    if _at_or_below(age, interval):
        return "in-calibration"
    if _at_or_below(age, interval + grace):
        return "due"
    return "out-of-calibration"


def calibration_findings(days_since_calibration, interval_days, grace_days=DEFAULT_GRACE_DAYS):
    """Return the findings raised by the calibration standing."""
    status = calibration_status(days_since_calibration, interval_days, grace_days)
    if status == "in-calibration":
        return []
    if status == "due":
        return [{
            "severity": "major",
            "control": "calibration-recall",
            "detail": "tool is inside its recall grace and owes a calibration",
        }]
    return [{
        "severity": "critical",
        "control": "calibration-expired",
        "detail": "tool is past its calibration interval and its recall grace",
    }]


def wear_fraction(wraps_since_change, life_limit_wraps):
    """Return the bit life consumed as a fraction of its limit."""
    done = _count("wraps_since_change", wraps_since_change)
    limit = _count("life_limit_wraps", life_limit_wraps)
    if limit <= 0:
        raise ValueError("life_limit_wraps must be at least 1, got %d" % limit)
    return done / float(limit)


def wear_findings(wraps_since_change, life_limit_wraps):
    """Return the findings raised by the bit wear record."""
    fraction = wear_fraction(wraps_since_change, life_limit_wraps)
    if _at_or_above(fraction, 1.0):
        return [{
            "severity": "critical",
            "control": "bit-life",
            "detail": "bit has consumed %.4f of its life in wraps" % fraction,
        }]
    if _at_or_above(fraction, WEAR_WARNING_FRACTION):
        return [{
            "severity": "major",
            "control": "bit-life-warning",
            "detail": "bit has consumed %.4f of its life and owes a change" % fraction,
        }]
    return []


def setup_sample_findings(sample, required_turns):
    """Return the findings raised by the set-up sample wrap."""
    if not isinstance(sample, dict):
        raise ValueError("sample must be a mapping")
    for key in ("turns", "overlapping_turns", "end_play_mm", "allowable_end_play_mm"):
        if key not in sample:
            raise ValueError("sample missing required key '%s'" % key)
    owed = _count("required_turns", required_turns)
    if owed < 1:
        raise ValueError("required_turns must be at least 1")
    turns = _count("sample['turns']", sample["turns"])
    overlapping = sample["overlapping_turns"]
    if not isinstance(overlapping, bool):
        raise ValueError("sample['overlapping_turns'] must be a boolean")
    play = _non_negative("sample['end_play_mm']", sample["end_play_mm"])
    allowance = _positive("sample['allowable_end_play_mm']", sample["allowable_end_play_mm"])
    findings = []
    if turns < owed:
        findings.append({
            "severity": "critical",
            "control": "sample-turn-count",
            "detail": "set-up sample made %d turns against the %d owed" % (turns, owed),
        })
    if overlapping:
        findings.append({
            "severity": "critical",
            "control": "sample-overlap",
            "detail": "set-up sample shows overlapping turns, so the sleeve is not "
                      "indexing the wire down the post",
        })
    if not _at_or_below(play, allowance):
        findings.append({
            "severity": "major",
            "control": "sample-end-play",
            "detail": "set-up sample end play %.4f mm against a %.4f mm allowance"
                      % (play, allowance),
        })
    return findings


def tension_ratio(measured_n, nominal_n):
    """Return the delivered wrap tension as a fraction of nominal."""
    measured = _non_negative("measured_n", measured_n)
    nominal = _positive("nominal_n", nominal_n)
    return measured / nominal


def tension_findings(measured_n, nominal_n, band=TENSION_BAND):
    """Return the findings raised by the delivered wrap tension."""
    if not isinstance(band, (list, tuple)) or len(band) != 2:
        raise ValueError("band must be a (low, high) pair")
    low = _positive("band low", band[0])
    high = _positive("band high", band[1])
    if low > high:
        raise ValueError("band must read (low, high)")
    ratio = tension_ratio(measured_n, nominal_n)
    if _at_or_above(ratio, low) and _at_or_below(ratio, high):
        return []
    return [{
        "severity": "critical",
        "control": "wrap-tension",
        "detail": "tool delivers %.4f of nominal tension, outside %.2f to %.2f"
                  % (ratio, low, high),
    }]


def tool_disposition(findings):
    """Return the tool disposition implied by the ranked findings."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    severities = set()
    for item in findings:
        if not isinstance(item, dict) or item.get("severity") not in SEVERITY_ORDER:
            raise ValueError("each finding must carry a known severity")
        severities.add(item["severity"])
    if "critical" in severities:
        return "withdraw-from-service"
    if severities:
        return "release-with-actions"
    return "release-for-use"


def assess_tool_control(spec):
    """Grade one wrapping tool set before it is released to production.

    spec keys: bit, gauge_awg, post_diagonal_mm, days_since_calibration,
    wraps_since_change, life_limit_wraps, sample, required_turns,
    measured_tension_n, nominal_tension_n, optional interval_days, grace_days.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("bit", "gauge_awg", "post_diagonal_mm", "days_since_calibration",
                "wraps_since_change", "life_limit_wraps", "sample", "required_turns",
                "measured_tension_n", "nominal_tension_n"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    findings = []
    findings.extend(bit_coverage_findings(
        spec["bit"], spec["gauge_awg"], spec["post_diagonal_mm"]
    ))
    interval = spec.get("interval_days", DEFAULT_CALIBRATION_INTERVAL_DAYS)
    grace = spec.get("grace_days", DEFAULT_GRACE_DAYS)
    status = calibration_status(spec["days_since_calibration"], interval, grace)
    findings.extend(calibration_findings(spec["days_since_calibration"], interval, grace))
    wear = wear_fraction(spec["wraps_since_change"], spec["life_limit_wraps"])
    findings.extend(wear_findings(spec["wraps_since_change"], spec["life_limit_wraps"]))
    findings.extend(setup_sample_findings(spec["sample"], spec["required_turns"]))
    findings.extend(tension_findings(spec["measured_tension_n"], spec["nominal_tension_n"]))
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {
        "calibration_status": status,
        "wear_fraction": wear,
        "tension_ratio": tension_ratio(
            spec["measured_tension_n"], spec["nominal_tension_n"]
        ),
        "findings": findings,
        "disposition": tool_disposition(findings),
    }
