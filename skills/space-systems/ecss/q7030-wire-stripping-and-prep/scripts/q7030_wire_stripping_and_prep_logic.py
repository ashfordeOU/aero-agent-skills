"""Wire stripping and end preparation for solderless wrapped connections.

Anchor: ECSS-Q-ST-70-30 requirements on preparing the wire end before it is
wrapped -- the strip length the planned turns need, and the condition the bared
conductor has to be in. Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Derive the strip length the connection needs from the conductor diameter, the
   bare turns, any insulated turns and the tail allowance, because the strip
   length is what decides how many turns can actually be laid on the post.
2. Compare the measured strip length against that requirement with a symmetric
   tolerance: a short strip cannot reach the turn count, and a long one leaves
   bare conductor standing above the wrap.
3. Return any nick or scrape as a fraction of the conductor diameter, because a
   fixed depth means something different on a fine wire than on a thick one.
4. Return the reduction in conductor diameter the stripping jaws left, which is
   deformation the wrap will later be asked to carry the tension through.
5. Grade the insulation: the set-back at the strip point and whether the
   insulation itself was cut, melted or dragged.
6. Count the re-strips this end has already had, rank the findings by severity,
   and close with accept, re-strip, or reject the wire end.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "REFERENCE_GAUGE",
    "REFERENCE_DIAMETER_MM",
    "GAUGE_DECADE",
    "WRAPPABLE_GAUGE_SPAN",
    "STRIP_LENGTH_TOLERANCE_MM",
    "DEFAULT_TAIL_ALLOWANCE_MM",
    "MAX_NICK_FRACTION",
    "MAX_DIAMETER_REDUCTION",
    "MAX_RESTRIPS",
    "SEVERITY_ORDER",
    "awg_conductor_diameter_mm",
    "required_strip_length_mm",
    "strip_length_findings",
    "nick_depth_fraction",
    "nick_findings",
    "diameter_reduction_fraction",
    "deformation_findings",
    "insulation_findings",
    "restrips_remaining",
    "preparation_disposition",
    "assess_wire_preparation",
]

# Lengths and fractions here are products and quotients of measured numbers; an
# exact equality can land a few ULPs on the wrong side of its bound. Absorb the
# representation error here instead of relaxing the preparation limit.
BOUND_TOLERANCE = 1e-9

REFERENCE_GAUGE = 36
REFERENCE_DIAMETER_MM = 0.127
GAUGE_DECADE = 92.0
WRAPPABLE_GAUGE_SPAN = (18, 32)

# Symmetric tolerance on the strip length. Short cannot reach the turns; long
# leaves bare conductor standing above the finished wrap.
STRIP_LENGTH_TOLERANCE_MM = 0.5

# Conductor left beyond the last turn so the wrap can be started and finished.
DEFAULT_TAIL_ALLOWANCE_MM = 1.0

# A nick is measured against the conductor it is in, not in absolute depth.
MAX_NICK_FRACTION = 0.05

# Diameter the stripping jaws may take out of the conductor, as a fraction.
MAX_DIAMETER_REDUCTION = 0.03

# Re-strips one wire end may have before the remaining slack is spent.
MAX_RESTRIPS = 2

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


def awg_conductor_diameter_mm(gauge_awg):
    """Return the bare conductor diameter of an AWG gauge in millimetres."""
    if isinstance(gauge_awg, bool) or not isinstance(gauge_awg, int):
        raise ValueError("gauge_awg must be an integer, got %r" % (gauge_awg,))
    thickest, thinnest = WRAPPABLE_GAUGE_SPAN
    if gauge_awg < thickest or gauge_awg > thinnest:
        raise ValueError(
            "AWG %d is outside the wrappable span AWG %d to AWG %d"
            % (gauge_awg, thickest, thinnest)
        )
    return REFERENCE_DIAMETER_MM * (GAUGE_DECADE ** ((REFERENCE_GAUGE - gauge_awg) / 39.0))


def required_strip_length_mm(gauge_awg, turns, insulation_turns=0,
                             insulated_diameter_mm=None,
                             tail_allowance_mm=DEFAULT_TAIL_ALLOWANCE_MM):
    """Return the strip length the planned wrap needs."""
    diameter = awg_conductor_diameter_mm(gauge_awg)
    bare = _count("turns", turns)
    if bare < 1:
        raise ValueError("turns must be at least 1, got %d" % bare)
    insulated = _count("insulation_turns", insulation_turns)
    tail = _non_negative("tail_allowance_mm", tail_allowance_mm)
    length = bare * diameter + tail
    if insulated:
        if insulated_diameter_mm is None:
            raise ValueError(
                "insulated_diameter_mm is needed when insulation turns are wrapped"
            )
        outer = _positive("insulated_diameter_mm", insulated_diameter_mm)
        if outer <= diameter:
            raise ValueError(
                "insulated_diameter_mm %g must exceed the bare conductor diameter %g"
                % (outer, diameter)
            )
        length += insulated * outer
    return length


def strip_length_findings(measured_mm, required_mm, tolerance_mm=STRIP_LENGTH_TOLERANCE_MM):
    """Return the findings raised by the measured strip length."""
    measured = _non_negative("measured_mm", measured_mm)
    required = _positive("required_mm", required_mm)
    tolerance = _non_negative("tolerance_mm", tolerance_mm)
    deviation = measured - required
    if _at_or_below(abs(deviation), tolerance):
        return []
    if deviation < 0.0:
        return [{
            "severity": "critical",
            "control": "strip-length-short",
            "detail": "stripped %.4f mm against %.4f mm needed; the turn count "
                      "cannot be laid" % (measured, required),
        }]
    return [{
        "severity": "major",
        "control": "strip-length-long",
        "detail": "stripped %.4f mm against %.4f mm needed; bare conductor would "
                  "stand above the wrap" % (measured, required),
    }]


def nick_depth_fraction(depth_mm, gauge_awg):
    """Return a nick or scrape depth as a fraction of the conductor diameter."""
    depth = _non_negative("depth_mm", depth_mm)
    diameter = awg_conductor_diameter_mm(gauge_awg)
    return depth / diameter


def nick_findings(depth_mm, gauge_awg):
    """Return the findings raised by conductor nicks, scrapes or gouges."""
    fraction = nick_depth_fraction(depth_mm, gauge_awg)
    if fraction <= 0.0:
        return []
    if _at_or_below(fraction, MAX_NICK_FRACTION):
        return [{
            "severity": "major",
            "control": "conductor-nick",
            "detail": "conductor nicked to %.4f of its diameter" % fraction,
        }]
    return [{
        "severity": "critical",
        "control": "conductor-nick-deep",
        "detail": "conductor nicked to %.4f of its diameter, above the %.4f limit"
                  % (fraction, MAX_NICK_FRACTION),
    }]


def diameter_reduction_fraction(measured_diameter_mm, gauge_awg):
    """Return the diameter the stripping jaws took out, as a fraction."""
    measured = _positive("measured_diameter_mm", measured_diameter_mm)
    nominal = awg_conductor_diameter_mm(gauge_awg)
    reduction = (nominal - measured) / nominal
    return reduction if reduction > 0.0 else 0.0


def deformation_findings(measured_diameter_mm, gauge_awg):
    """Return the findings raised by conductor deformation at the strip point."""
    fraction = diameter_reduction_fraction(measured_diameter_mm, gauge_awg)
    if _at_or_below(fraction, MAX_DIAMETER_REDUCTION):
        return []
    return [{
        "severity": "critical",
        "control": "conductor-deformation",
        "detail": "stripping reduced the conductor by %.4f of its diameter, above "
                  "the %.4f limit" % (fraction, MAX_DIAMETER_REDUCTION),
    }]


def insulation_findings(setback_mm, allowable_setback_mm, insulation_damaged):
    """Return the findings raised by the insulation at the strip point."""
    setback = _non_negative("setback_mm", setback_mm)
    allowance = _positive("allowable_setback_mm", allowable_setback_mm)
    if not isinstance(insulation_damaged, bool):
        raise ValueError("insulation_damaged must be a boolean")
    findings = []
    if not _at_or_below(setback, allowance):
        findings.append({
            "severity": "major",
            "control": "insulation-setback",
            "detail": "insulation set back %.4f mm against a %.4f mm allowance"
                      % (setback, allowance),
        })
    if insulation_damaged:
        findings.append({
            "severity": "major",
            "control": "insulation-damage",
            "detail": "insulation was cut, melted or dragged at the strip point",
        })
    return findings


def restrips_remaining(restrip_count, limit=MAX_RESTRIPS):
    """Return how many re-strips this wire end still has."""
    used = _count("restrip_count", restrip_count)
    allowed = _count("limit", limit)
    remaining = allowed - used
    return remaining if remaining > 0 else 0


def preparation_disposition(findings, remaining):
    """Return the disposition implied by the findings and the re-strip budget."""
    if not isinstance(findings, (list, tuple)):
        raise ValueError("findings must be a sequence")
    for item in findings:
        if not isinstance(item, dict) or item.get("severity") not in SEVERITY_ORDER:
            raise ValueError("each finding must carry a known severity")
    left = _count("remaining", remaining)
    if not findings:
        return "accept"
    if left >= 1:
        return "restrip-required"
    return "reject-wire-end"


def assess_wire_preparation(spec):
    """Grade one prepared wire end before it goes on the post.

    spec keys: gauge_awg, turns, measured_strip_length_mm, nick_depth_mm,
    measured_diameter_mm, insulation_setback_mm, allowable_setback_mm,
    insulation_damaged, restrip_count, optional insulation_turns,
    insulated_diameter_mm, tail_allowance_mm, strip_tolerance_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("gauge_awg", "turns", "measured_strip_length_mm", "nick_depth_mm",
                "measured_diameter_mm", "insulation_setback_mm",
                "allowable_setback_mm", "insulation_damaged", "restrip_count"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    gauge = spec["gauge_awg"]
    required = required_strip_length_mm(
        gauge,
        spec["turns"],
        spec.get("insulation_turns", 0),
        spec.get("insulated_diameter_mm"),
        spec.get("tail_allowance_mm", DEFAULT_TAIL_ALLOWANCE_MM),
    )
    findings = []
    findings.extend(strip_length_findings(
        spec["measured_strip_length_mm"],
        required,
        spec.get("strip_tolerance_mm", STRIP_LENGTH_TOLERANCE_MM),
    ))
    findings.extend(nick_findings(spec["nick_depth_mm"], gauge))
    findings.extend(deformation_findings(spec["measured_diameter_mm"], gauge))
    findings.extend(insulation_findings(
        spec["insulation_setback_mm"],
        spec["allowable_setback_mm"],
        spec["insulation_damaged"],
    ))
    remaining = restrips_remaining(spec["restrip_count"])
    if findings and remaining < 1:
        findings.append({
            "severity": "critical",
            "control": "restrip-budget",
            "detail": "wire end has used its re-strip allowance and has no slack left",
        })
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    return {
        "required_strip_length_mm": required,
        "nick_depth_fraction": nick_depth_fraction(spec["nick_depth_mm"], gauge),
        "diameter_reduction_fraction": diameter_reduction_fraction(
            spec["measured_diameter_mm"], gauge
        ),
        "restrips_remaining": remaining,
        "findings": findings,
        "disposition": preparation_disposition(findings, remaining),
    }
