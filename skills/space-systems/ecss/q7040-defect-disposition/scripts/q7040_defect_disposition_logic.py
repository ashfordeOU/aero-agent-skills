#!/usr/bin/env python3
"""Disposition of a braze defect that failed acceptance.

Anchor: the acceptance and rework provisions of the ECSS brazing
standard. The procedure below is a paraphrase into implementable steps;
no standard text is reproduced.

Once a brazement is outside its class limit, the question is which
route the assembly can survive:

    accept-as-is            the defect is in fact within its limit
    local-repair            mechanical removal, no thermal cycle spent
    re-braze                a further thermal cycle, from a finite budget
    use-as-is-on-deviation  approved deviation, defect out of the load path
    reject-and-scrap        no route remains

Two defects leave the rework routes outright: a crack that has run into
the parent metal, which re-melting the filler cannot touch, and eroded
parent metal, which a further molten cycle attacks again.

Every route but accept-as-is restarts the inspection: the method that
found the defect is repeated, visual inspection is repeated, and a
hermetic joint owes its leak test again.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FLOOR = "floor"
CEILING = "ceiling"

BRAZE_CLASSES = ("class-a", "class-b", "class-c")
LOCATIONS = ("load-path", "non-load-path", "sealing-surface")

DEFECT_TYPES = (
    "fill-shortfall",
    "oversize-void",
    "linear-void-run",
    "filler-crack",
    "base-metal-crack",
    "base-metal-erosion",
    "flux-entrapment",
    "excess-filler",
)

DEFECT_SENSE = {
    "fill-shortfall": FLOOR,
    "oversize-void": CEILING,
    "linear-void-run": CEILING,
    "filler-crack": CEILING,
    "base-metal-crack": CEILING,
    "base-metal-erosion": CEILING,
    "flux-entrapment": CEILING,
    "excess-filler": CEILING,
}

# Rejected on existence, so never dispositioned as accept-as-is.
REJECTED_ON_EXISTENCE = ("filler-crack", "base-metal-crack")

# Defects a further molten cycle cannot help or actively worsens.
OUTSIDE_THERMAL_REWORK = ("base-metal-crack", "base-metal-erosion")

# Defects removed mechanically, spending no part of the thermal budget.
MECHANICALLY_REPAIRABLE = ("flux-entrapment", "excess-filler")

ACCEPT_AS_IS = "accept-as-is"
LOCAL_REPAIR = "local-repair"
RE_BRAZE = "re-braze"
USE_AS_IS_ON_DEVIATION = "use-as-is-on-deviation"
REJECT_AND_SCRAP = "reject-and-scrap"

# Ordered least to most severe; the worst disposition governs an assembly.
DISPOSITION_ESCALATION = (
    ACCEPT_AS_IS,
    LOCAL_REPAIR,
    RE_BRAZE,
    USE_AS_IS_ON_DEVIATION,
    REJECT_AND_SCRAP,
)

# Severity ratio beyond which rework is not credible: the process ran
# wrong and a further attempt reproduces the defect.
REWORK_BOUND = {"class-a": 2.0, "class-b": 2.5, "class-c": 3.0}

DEFAULT_REBRAZE_LIMIT = 2
DEFAULT_THERMAL_CYCLE_ALLOWANCE = 3

INSPECTION_METHODS = (
    "visual-inspection",
    "radiographic-testing",
    "ultrasonic-testing",
    "leak-testing",
)

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_positive(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return float(value)


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _require_bool(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A severity ratio is a quotient of measured quantities, so a defect
    sitting deliberately on a bound can read a few units in the last
    place above it. The bound is never raised; only the comparison
    tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def severity_ratio(measured, limit, sense):
    """How far past its limit the measurement sits, in its own direction."""
    _require_choice("sense", sense, (FLOOR, CEILING))
    measured_value = _require_positive("measured", measured)
    limit_value = _require_positive("limit", limit)
    if sense == CEILING:
        return measured_value / limit_value
    return limit_value / measured_value


def within_limit(measured, limit, sense):
    """Is the measurement inside its limit, tolerating the last bit."""
    return _at_most(severity_ratio(measured, limit, sense), 1.0)


def rework_bound(braze_class):
    """Severity ratio past which rework stops being credible."""
    _require_choice("braze_class", braze_class, BRAZE_CLASSES)
    return REWORK_BOUND[braze_class]


def remaining_rebraze_attempts(rebraze_count, rebraze_limit=DEFAULT_REBRAZE_LIMIT):
    """Thermal rework attempts the joint still has in its budget."""
    used = _require_count("rebraze_count", rebraze_count)
    limit = _require_count("rebraze_limit", rebraze_limit)
    if used > limit:
        raise ValueError(
            "rebraze_count %d already exceeds the limit of %d" % (used, limit)
        )
    return limit - used


def thermal_exposure_remaining(
    cycles_used, cycle_allowance=DEFAULT_THERMAL_CYCLE_ALLOWANCE
):
    """Thermal cycles the assembly may still take on its declared allowance."""
    used = _require_count("thermal_cycles_used", cycles_used)
    allowance = _require_count("thermal_cycle_allowance", cycle_allowance)
    return max(0, allowance - used)


def reinspection_for(disposition, detected_by, hermetic):
    """Re-inspection the chosen route owes before the joint is released."""
    _require_choice("disposition", disposition, DISPOSITION_ESCALATION)
    _require_choice("detected_by", detected_by, INSPECTION_METHODS)
    _require_bool("hermetic", hermetic)
    if disposition in (ACCEPT_AS_IS, REJECT_AND_SCRAP):
        return []
    methods = ["visual-inspection"]
    if detected_by not in methods:
        methods.append(detected_by)
    if hermetic and "leak-testing" not in methods:
        methods.append("leak-testing")
    return methods


def dispose_defect(defect):
    """Pick the disposition route for one braze defect and say why."""
    if not isinstance(defect, dict):
        raise ValueError("defect must be a mapping, got %r" % (defect,))
    defect_type = _require_choice(
        "defect_type", defect.get("defect_type"), DEFECT_TYPES
    )
    location = _require_choice("location", defect.get("location"), LOCATIONS)
    braze_class = _require_choice(
        "braze_class", defect.get("braze_class"), BRAZE_CLASSES
    )
    detected_by = _require_choice(
        "detected_by", defect.get("detected_by", "visual-inspection"),
        INSPECTION_METHODS,
    )
    hermetic = _require_bool("hermetic", defect.get("hermetic", False))
    deviation_approved = _require_bool(
        "deviation_approved", defect.get("deviation_approved", False)
    )
    sense = DEFECT_SENSE[defect_type]
    ratio = severity_ratio(defect.get("measured"), defect.get("limit"), sense)
    bound = rework_bound(braze_class)
    attempts_left = remaining_rebraze_attempts(
        defect.get("rebraze_count", 0),
        defect.get("rebraze_limit", DEFAULT_REBRAZE_LIMIT),
    )
    cycles_left = thermal_exposure_remaining(
        defect.get("thermal_cycles_used", 0),
        defect.get("thermal_cycle_allowance", DEFAULT_THERMAL_CYCLE_ALLOWANCE),
    )

    findings = []

    def _finish(disposition, reason):
        return {
            "id": defect.get("id"),
            "defect_type": defect_type,
            "location": location,
            "braze_class": braze_class,
            "severity_ratio": ratio,
            "rework_bound": bound,
            "within_limit": _at_most(ratio, 1.0),
            "remaining_rebraze_attempts": attempts_left,
            "remaining_thermal_cycles": cycles_left,
            "disposition": disposition,
            "reason": reason,
            "reinspection": reinspection_for(disposition, detected_by, hermetic),
            "findings": findings,
        }

    if _at_most(ratio, 1.0) and defect_type not in REJECTED_ON_EXISTENCE:
        return _finish(ACCEPT_AS_IS, "measurement is inside its class limit")

    if defect_type == "base-metal-crack":
        findings.append(
            "a crack in the parent metal is not a braze defect; re-melting the "
            "filler cannot reach it and adds heat to the crack tip"
        )
        return _finish(REJECT_AND_SCRAP, "crack has run into the parent metal")

    if defect_type == "base-metal-erosion":
        if location == "load-path":
            findings.append(
                "eroded parent metal in the load path has no rework route; a "
                "further molten cycle removes more of the remaining wall"
            )
            return _finish(REJECT_AND_SCRAP, "parent metal eroded in the load path")
        if _at_most(ratio, bound):
            return _finish(
                LOCAL_REPAIR, "erosion is repaired mechanically, never by more heat"
            )
        findings.append(
            "erosion at %.3f times its limit is past the %.3f rework bound"
            % (ratio, bound)
        )
        return _finish(REJECT_AND_SCRAP, "erosion beyond the rework bound")

    if defect_type in MECHANICALLY_REPAIRABLE:
        if _at_most(ratio, bound):
            return _finish(
                LOCAL_REPAIR, "removed mechanically, spending no thermal cycle"
            )
        findings.append(
            "%s at %.3f times its limit is past the %.3f rework bound"
            % (defect_type, ratio, bound)
        )
        return _finish(REJECT_AND_SCRAP, "mechanical defect beyond the rework bound")

    if not _at_most(ratio, bound):
        findings.append(
            "%s at %.3f times its limit is past the %.3f rework bound; the "
            "process ran wrong and a further attempt reproduces the defect"
            % (defect_type, ratio, bound)
        )
    elif attempts_left < 1:
        findings.append("the re-braze budget for this joint is spent")
    elif cycles_left < 1:
        findings.append(
            "the assembly has no cumulative thermal exposure allowance left"
        )
    else:
        return _finish(RE_BRAZE, "a thermal rework attempt is still available")

    if deviation_approved and location == "non-load-path":
        return _finish(
            USE_AS_IS_ON_DEVIATION,
            "approved deviation covers a defect out of the load path",
        )
    if deviation_approved:
        findings.append(
            "a deviation cannot cover a defect in the %s; the route is closed"
            % location
        )
    else:
        findings.append("no approved deviation is on file for a use-as-is")
    return _finish(REJECT_AND_SCRAP, "no rework or deviation route remains")


def dispose_all(defects):
    """Dispose a set of defects and report the route that governs the part."""
    if not isinstance(defects, (list, tuple)) or not defects:
        raise ValueError("defects must be a non-empty sequence")
    results = [dispose_defect(defect) for defect in defects]
    governing = max(
        results, key=lambda r: DISPOSITION_ESCALATION.index(r["disposition"])
    )["disposition"]
    reinspection = []
    for result in results:
        for method in result["reinspection"]:
            if method not in reinspection:
                reinspection.append(method)
    return {
        "results": results,
        "governing_disposition": governing,
        "scrapped": governing == REJECT_AND_SCRAP,
        "combined_reinspection": [] if governing == REJECT_AND_SCRAP else reinspection,
        "counts": {
            disposition: sum(
                1 for r in results if r["disposition"] == disposition
            )
            for disposition in DISPOSITION_ESCALATION
        },
    }
