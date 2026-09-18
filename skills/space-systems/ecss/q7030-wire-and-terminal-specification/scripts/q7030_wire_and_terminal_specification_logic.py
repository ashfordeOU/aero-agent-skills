"""Wire and terminal specification control for solderless wrapped connections.

Anchor: ECSS-Q-ST-70-30 requirements on the materials that go into a wrapped
connection -- the conductor gauge and finish, and the terminal post section,
length and finish. Paraphrased into an implementable procedure; no standard text
is reproduced.

Procedure implemented here
--------------------------
1. Derive the bare conductor diameter from the AWG gauge and the turn count that
   gauge owes, because a thicker conductor stores its contact force in fewer
   turns and a thinner one needs more.
2. Derive the post section: its diagonal from width and thickness, and the ratio
   of that diagonal to the conductor diameter, which is what decides whether the
   wire can deform over the corner rather than ride across it.
3. Derive the wrap length one level occupies from the turn count, the conductor
   diameter and any insulated turns, then the post length the planned number of
   levels needs including end clearance.
4. Grade the conductor and post finishes, refusing an unalloyed tin finish on
   either part and naming any finish outside the qualified set.
5. Rank the findings by severity and close with one compatibility disposition.
"""

import math

__all__ = [
    "BOUND_TOLERANCE",
    "REFERENCE_GAUGE",
    "REFERENCE_DIAMETER_MM",
    "GAUGE_DECADE",
    "TURNS_BY_GAUGE",
    "MIN_DIAGONAL_TO_DIAMETER",
    "END_CLEARANCE_MM",
    "PROHIBITED_FINISHES",
    "QUALIFIED_FINISHES",
    "SEVERITY_ORDER",
    "awg_conductor_diameter_mm",
    "required_turns",
    "post_diagonal_mm",
    "diagonal_to_diameter_ratio",
    "wrap_length_per_level_mm",
    "minimum_post_length_mm",
    "finish_findings",
    "assess_wire_and_terminal",
]

# Lengths and ratios are quotients and products of measured numbers; an exact
# equality can land a few ULPs on the wrong side of its bound. Absorb the
# representation error here instead of relaxing the specification.
BOUND_TOLERANCE = 1e-9

# AWG is a geometric series: 39 gauge steps span a diameter ratio of 92.
REFERENCE_GAUGE = 36
REFERENCE_DIAMETER_MM = 0.127
GAUGE_DECADE = 92.0

# Turns owed by gauge band, thickest band first. Each entry is
# (thickest_awg, thinnest_awg, turns).
TURNS_BY_GAUGE = (
    (18, 22, 5),
    (23, 26, 6),
    (27, 32, 7),
)

# The post diagonal has to stand this far above the conductor diameter for the
# wire to deform over the corner instead of riding across it.
MIN_DIAGONAL_TO_DIAMETER = 1.5

# Post length left clear beyond the last level, so the top wrap is not formed
# against the end of the post.
END_CLEARANCE_MM = 0.5

# Unalloyed tin grows whiskers across a wrapped backplane, where the posts sit
# at fixed spacing and the whisker has somewhere to go.
PROHIBITED_FINISHES = ("pure-tin", "bright-tin", "unalloyed-tin")
QUALIFIED_FINISHES = ("gold-over-nickel", "silver", "tin-lead", "nickel")

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


def _token(label, value):
    """Return a lowercase, stripped token, or raise ValueError."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip().lower()


def _at_or_above(value, bound):
    """True when value is above bound or lands on it within tolerance."""
    return value > bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=BOUND_TOLERANCE)


def awg_conductor_diameter_mm(gauge_awg):
    """Return the bare conductor diameter of an AWG gauge in millimetres."""
    if isinstance(gauge_awg, bool) or not isinstance(gauge_awg, int):
        raise ValueError("gauge_awg must be an integer, got %r" % (gauge_awg,))
    thickest = TURNS_BY_GAUGE[0][0]
    thinnest = TURNS_BY_GAUGE[-1][1]
    if gauge_awg < thickest or gauge_awg > thinnest:
        raise ValueError(
            "AWG %d is outside the wrappable span AWG %d to AWG %d"
            % (gauge_awg, thickest, thinnest)
        )
    exponent = (REFERENCE_GAUGE - gauge_awg) / 39.0
    return REFERENCE_DIAMETER_MM * (GAUGE_DECADE ** exponent)


def required_turns(gauge_awg):
    """Return the number of bare turns the gauge owes."""
    if isinstance(gauge_awg, bool) or not isinstance(gauge_awg, int):
        raise ValueError("gauge_awg must be an integer, got %r" % (gauge_awg,))
    for thickest, thinnest, turns in TURNS_BY_GAUGE:
        if thickest <= gauge_awg <= thinnest:
            return turns
    raise ValueError("AWG %d has no turn count in the wrappable span" % gauge_awg)


def post_diagonal_mm(width_mm, thickness_mm):
    """Return the diagonal of a rectangular post section."""
    width = _positive("width_mm", width_mm)
    thickness = _positive("thickness_mm", thickness_mm)
    return math.hypot(width, thickness)


def diagonal_to_diameter_ratio(width_mm, thickness_mm, gauge_awg):
    """Return the post diagonal as a multiple of the conductor diameter."""
    diagonal = post_diagonal_mm(width_mm, thickness_mm)
    return diagonal / awg_conductor_diameter_mm(gauge_awg)


def wrap_length_per_level_mm(gauge_awg, turns, insulation_turns=0,
                             insulated_diameter_mm=None):
    """Return the post length one wrap level occupies."""
    diameter = awg_conductor_diameter_mm(gauge_awg)
    bare = _count("turns", turns)
    insulated = _count("insulation_turns", insulation_turns)
    if insulated and insulated_diameter_mm is None:
        raise ValueError("insulated_diameter_mm is needed when insulation turns are wrapped")
    length = bare * diameter
    if insulated:
        outer = _positive("insulated_diameter_mm", insulated_diameter_mm)
        if outer <= diameter:
            raise ValueError(
                "insulated_diameter_mm %g must exceed the bare conductor diameter %g"
                % (outer, diameter)
            )
        length += insulated * outer
    return length


def minimum_post_length_mm(gauge_awg, turns, levels=1, insulation_turns=0,
                           insulated_diameter_mm=None,
                           end_clearance_mm=END_CLEARANCE_MM):
    """Return the post length the planned levels need, including end clearance."""
    per_level = wrap_length_per_level_mm(
        gauge_awg, turns, insulation_turns, insulated_diameter_mm
    )
    stacked = _count("levels", levels)
    if stacked < 1:
        raise ValueError("levels must be at least 1, got %d" % stacked)
    clearance = _non_negative("end_clearance_mm", end_clearance_mm)
    return stacked * per_level + clearance


def finish_findings(wire_finish, post_finish):
    """Return the findings raised by the conductor and post finishes."""
    findings = []
    for label, value in (("wire", wire_finish), ("post", post_finish)):
        finish = _token("%s_finish" % label, value)
        if finish in PROHIBITED_FINISHES:
            findings.append({
                "severity": "critical",
                "control": "prohibited-finish",
                "detail": "%s carries a %s finish, which grows whiskers across a "
                          "wrapped backplane" % (label, finish),
            })
        elif finish not in QUALIFIED_FINISHES:
            findings.append({
                "severity": "major",
                "control": "unqualified-finish",
                "detail": "%s finish %s is outside the qualified set" % (label, finish),
            })
    return findings


def assess_wire_and_terminal(spec):
    """Grade one wire and terminal pairing against the wrapping specification.

    spec keys: gauge_awg, planned_turns, post_width_mm, post_thickness_mm,
    available_post_length_mm, wire_finish, post_finish, optional levels,
    insulation_turns, insulated_diameter_mm, end_clearance_mm.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("gauge_awg", "planned_turns", "post_width_mm", "post_thickness_mm",
                "available_post_length_mm", "wire_finish", "post_finish"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    gauge = spec["gauge_awg"]
    diameter = awg_conductor_diameter_mm(gauge)
    owed_turns = required_turns(gauge)
    planned = _count("planned_turns", spec["planned_turns"])
    ratio = diagonal_to_diameter_ratio(
        spec["post_width_mm"], spec["post_thickness_mm"], gauge
    )
    needed_length = minimum_post_length_mm(
        gauge,
        planned,
        spec.get("levels", 1),
        spec.get("insulation_turns", 0),
        spec.get("insulated_diameter_mm"),
        spec.get("end_clearance_mm", END_CLEARANCE_MM),
    )
    available = _positive("available_post_length_mm", spec["available_post_length_mm"])
    findings = []
    if planned < owed_turns:
        findings.append({
            "severity": "critical",
            "control": "turn-count",
            "detail": "AWG %d owes %d bare turns, %d planned" % (gauge, owed_turns, planned),
        })
    if not _at_or_above(ratio, MIN_DIAGONAL_TO_DIAMETER):
        findings.append({
            "severity": "major",
            "control": "post-section",
            "detail": "post diagonal is %.4f conductor diameters, below the %.2f owed"
                      % (ratio, MIN_DIAGONAL_TO_DIAMETER),
        })
    if not _at_or_above(available, needed_length):
        findings.append({
            "severity": "critical",
            "control": "post-length",
            "detail": "post offers %.4f mm, the planned wrap needs %.4f mm"
                      % (available, needed_length),
        })
    findings.extend(finish_findings(spec["wire_finish"], spec["post_finish"]))
    findings.sort(key=lambda f: SEVERITY_ORDER[f["severity"]])
    if any(f["severity"] == "critical" for f in findings):
        disposition = "not-compatible"
    elif findings:
        disposition = "compatible-with-actions"
    else:
        disposition = "compatible"
    return {
        "conductor_diameter_mm": diameter,
        "required_turns": owed_turns,
        "planned_turns": planned,
        "post_diagonal_mm": post_diagonal_mm(
            spec["post_width_mm"], spec["post_thickness_mm"]
        ),
        "diagonal_to_diameter_ratio": ratio,
        "minimum_post_length_mm": needed_length,
        "available_post_length_mm": available,
        "findings": findings,
        "disposition": disposition,
    }
