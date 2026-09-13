#!/usr/bin/env python3
"""Substrate integrity acceptance thresholds from the assembly drawing.

Anchor: ECSS-E-ST-20-08C Rev.2 clause 5.5.3.10.2. The procedure below is
a paraphrase into implementable steps; no standard text is reproduced.

The unusual property of this acceptance decision is that the numbers it
runs on are not in the standard. The standard names where to find them:
the assembly control drawing for the coupon. That single fact drives
everything below.

    no default      an indication kind the drawing declares no threshold
                    for is not passing and not failing. It is
                    undetermined, and the answer is a drawing change or
                    a waiver, never a number borrowed from a similar
                    kind or from a previous programme
    revision bound  a threshold is only a criterion while it is the
                    threshold of the drawing revision the coupon was
                    built and measured against. Grading a revision C
                    coupon on revision D limits is a paperwork pass
    direction       some limits are ceilings -- disbond area, crack
                    length, core crush depth -- and some are floors,
                    such as the bond strength or the core height that
                    has to remain. A comparison that assumes a ceiling
                    everywhere passes a floor failure silently
    cumulative      indications that each clear their own limit can
                    still add up past a total the drawing sets for that
                    kind, which is a separate check and a separate
                    verdict

Margins are reported as a fraction of the limit so that a millimetre, a
square millimetre and a newton can be read side by side, and an
indication landing exactly on its limit is reported as on-limit rather
than silently passed: that coupon has no margin left for measurement
scatter.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

INDICATION_KINDS = (
    "facesheet-crack",
    "facesheet-core-disbond",
    "core-crush",
    "edge-closeout-separation",
    "insert-pullout",
    "dielectric-delamination",
    "residual-bond-strength",
    "remaining-core-height",
)

DIRECTIONS = ("max", "min")

ACCEPT = "accept"
ACCEPT_ON_LIMIT = "accept-on-limit"
REJECT = "reject"
UNDECLARED = "criteria-undeclared"

SUBSTRATE_ACCEPT = "substrate-integrity-accept"
SUBSTRATE_REJECT = "substrate-integrity-reject"
SUBSTRATE_UNDETERMINED = "substrate-integrity-undetermined"

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value.strip()


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _same(value, limit):
    """value == limit, absorbing floating-point representation error."""
    return math.isclose(value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL)


def _validate_threshold(label, entry):
    if not isinstance(entry, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, entry))
    limit = _require_positive("%s limit" % label, entry.get("limit"))
    units = _require_text("%s units" % label, entry.get("units"))
    direction = _require_choice("%s direction" % label, entry.get("direction"), DIRECTIONS)
    return {"limit": limit, "units": units, "direction": direction}


def validate_acd(acd):
    """Check the assembly control drawing can serve as a criteria source."""
    if not isinstance(acd, dict):
        raise ValueError("acd must be a mapping, got %r" % (acd,))
    drawing_id = _require_text("acd drawing_id", acd.get("drawing_id"))
    revision = _require_text("acd revision", acd.get("revision"))
    thresholds = acd.get("thresholds")
    if not isinstance(thresholds, dict) or not thresholds:
        raise ValueError(
            "acd %s rev %s declares no thresholds; a drawing with no criteria "
            "cannot be the source of an acceptance decision" % (drawing_id, revision)
        )
    cleaned = {}
    for kind, entry in thresholds.items():
        _require_choice("acd threshold kind", kind, INDICATION_KINDS)
        cleaned[kind] = _validate_threshold("acd threshold %s" % kind, entry)
    cumulative_raw = acd.get("cumulative_thresholds", {})
    if not isinstance(cumulative_raw, dict):
        raise ValueError("acd cumulative_thresholds must be a mapping")
    cumulative = {}
    for kind, entry in cumulative_raw.items():
        _require_choice("acd cumulative kind", kind, INDICATION_KINDS)
        checked = _validate_threshold("acd cumulative %s" % kind, entry)
        if checked["direction"] != "max":
            raise ValueError(
                "acd cumulative threshold %s must be a ceiling; a total has no "
                "meaningful floor" % (kind,)
            )
        cumulative[kind] = checked
    return {
        "drawing_id": drawing_id,
        "revision": revision,
        "thresholds": cleaned,
        "cumulative_thresholds": cumulative,
    }


def threshold_for(acd, kind):
    """The drawing's threshold for one indication kind, or None."""
    checked = validate_acd(acd)
    _require_choice("kind", kind, INDICATION_KINDS)
    entry = checked["thresholds"].get(kind)
    return dict(entry) if entry is not None else None


def margin_fraction(value, limit, direction):
    """Signed margin against a limit, as a fraction of that limit."""
    measured = _require_number("value", value)
    bound = _require_positive("limit", limit)
    _require_choice("direction", direction, DIRECTIONS)
    if direction == "max":
        return (bound - measured) / bound
    return (measured - bound) / bound


def disposition_indication(indication, acd):
    """Grade one indication against the drawing's threshold for its kind."""
    checked = validate_acd(acd)
    if not isinstance(indication, dict):
        raise ValueError("indication must be a mapping, got %r" % (indication,))
    indication_id = _require_text("indication_id", indication.get("indication_id"))
    kind = _require_choice("kind", indication.get("kind"), INDICATION_KINDS)
    value = _require_non_negative("value", indication.get("value"))
    units = _require_text("units", indication.get("units"))
    entry = checked["thresholds"].get(kind)
    if entry is None:
        return {
            "indication_id": indication_id,
            "kind": kind,
            "value": value,
            "units": units,
            "limit": None,
            "direction": None,
            "margin_fraction": None,
            "disposition": UNDECLARED,
            "note": "drawing %s rev %s declares no threshold for %s; the decision "
            "needs a drawing change or a waiver, not a borrowed limit"
            % (checked["drawing_id"], checked["revision"], kind),
        }
    if units != entry["units"]:
        raise ValueError(
            "indication %s is measured in %s but the drawing threshold for %s is "
            "in %s" % (indication_id, units, kind, entry["units"])
        )
    margin = margin_fraction(value, entry["limit"], entry["direction"])
    if _same(value, entry["limit"]):
        disposition = ACCEPT_ON_LIMIT
    elif margin > 0.0:
        disposition = ACCEPT
    else:
        disposition = REJECT
    return {
        "indication_id": indication_id,
        "kind": kind,
        "value": value,
        "units": units,
        "limit": entry["limit"],
        "direction": entry["direction"],
        "margin_fraction": margin,
        "disposition": disposition,
        "note": "",
    }


def cumulative_check(dispositions, acd):
    """Totals per kind against the drawing's cumulative ceilings."""
    checked = validate_acd(acd)
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a list of graded indications")
    totals = {}
    for entry in dispositions:
        if not isinstance(entry, dict):
            raise ValueError("graded indication must be a mapping")
        kind = _require_choice("kind", entry.get("kind"), INDICATION_KINDS)
        if kind not in checked["cumulative_thresholds"]:
            continue
        if checked["thresholds"].get(kind, {}).get("direction") == "min":
            continue
        totals[kind] = totals.get(kind, 0.0) + _require_non_negative(
            "value", entry.get("value")
        )
    results = []
    for kind, total in sorted(totals.items()):
        ceiling = checked["cumulative_thresholds"][kind]
        margin = margin_fraction(total, ceiling["limit"], "max")
        if _same(total, ceiling["limit"]):
            disposition = ACCEPT_ON_LIMIT
        elif margin > 0.0:
            disposition = ACCEPT
        else:
            disposition = REJECT
        results.append(
            {
                "kind": kind,
                "total": total,
                "limit": ceiling["limit"],
                "units": ceiling["units"],
                "margin_fraction": margin,
                "disposition": disposition,
            }
        )
    return results


def assess_substrate_integrity(inspection, acd):
    """Full clause 5.5.3.10.2 acceptance decision for a cycled coupon."""
    checked = validate_acd(acd)
    if not isinstance(inspection, dict):
        raise ValueError("inspection must be a mapping, got %r" % (inspection,))
    coupon_id = _require_text("coupon_id", inspection.get("coupon_id"))
    measured_rev = _require_text(
        "inspection acd_revision", inspection.get("acd_revision")
    )
    if measured_rev != checked["revision"]:
        raise ValueError(
            "coupon %s was measured against drawing revision %s but revision %s "
            "was supplied as the criteria source; a coupon is graded on the "
            "revision it was built and measured to"
            % (coupon_id, measured_rev, checked["revision"])
        )
    indications = inspection.get("indications")
    if not isinstance(indications, (list, tuple)):
        raise ValueError("inspection indications must be a list")
    survey_complete = inspection.get("survey_complete", True)
    if not isinstance(survey_complete, bool):
        raise ValueError(
            "inspection survey_complete must be a boolean, got %r" % (survey_complete,)
        )
    graded = []
    seen = set()
    for entry in indications:
        result = disposition_indication(entry, acd)
        if result["indication_id"] in seen:
            raise ValueError(
                "indication_id %r appears twice" % (result["indication_id"],)
            )
        seen.add(result["indication_id"])
        graded.append(result)
    cumulative = cumulative_check(graded, acd)
    findings = []
    undeclared = [e["indication_id"] for e in graded if e["disposition"] == UNDECLARED]
    rejected = [e["indication_id"] for e in graded if e["disposition"] == REJECT]
    on_limit = [e["indication_id"] for e in graded if e["disposition"] == ACCEPT_ON_LIMIT]
    cumulative_rejects = [e["kind"] for e in cumulative if e["disposition"] == REJECT]
    for entry in graded:
        if entry["disposition"] == UNDECLARED:
            findings.append(entry["note"])
    if rejected:
        findings.append(
            "indications past their drawing limit: %s" % ", ".join(rejected)
        )
    if on_limit:
        findings.append(
            "indications exactly on their drawing limit, no margin left for "
            "measurement scatter: %s" % ", ".join(on_limit)
        )
    for kind in cumulative_rejects:
        findings.append(
            "%s totals past the cumulative ceiling the drawing sets, though each "
            "indication passed on its own" % kind
        )
    if not survey_complete:
        findings.append(
            "the survey that produced these indications was not complete; an "
            "acceptance decision on a partial survey is not a decision"
        )
    if not survey_complete or undeclared:
        verdict = SUBSTRATE_UNDETERMINED
    elif rejected or cumulative_rejects:
        verdict = SUBSTRATE_REJECT
    else:
        verdict = SUBSTRATE_ACCEPT
    if verdict == SUBSTRATE_ACCEPT and not graded:
        findings.append(
            "no indications recorded; the coupon is accepted on a complete survey "
            "that found nothing"
        )
    return {
        "coupon_id": coupon_id,
        "drawing_id": checked["drawing_id"],
        "revision": checked["revision"],
        "indications": graded,
        "cumulative": cumulative,
        "undeclared_kinds": sorted(
            {e["kind"] for e in graded if e["disposition"] == UNDECLARED}
        ),
        "verdict": verdict,
        "findings": findings,
    }
