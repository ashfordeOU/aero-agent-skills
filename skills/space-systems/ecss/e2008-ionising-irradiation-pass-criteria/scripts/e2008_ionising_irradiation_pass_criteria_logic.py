#!/usr/bin/env python3
"""Pass criteria for the ionising irradiation and annealing of blocking diodes.

Anchor: ECSS-E-ST-20-08C clause 12.6.11.1.2. The rules below are a
paraphrase into implementable steps; no standard text is reproduced.

The clause closes a total-dose campaign. A blocking diode is exposed to
ionising radiation, it is then annealed, and what the clause asks for is
a comparison: the characteristics the part shows after irradiation and
after annealing, against the limits its control drawing fixes.

Two readings, one limit set. That is the shape of the job and the reason
a single after-the-fact number is not enough:

    pre-irradiation     the baseline the shift is measured from
    post-irradiation    the worst the part is expected to be
    post-anneal         what the part settles at, which is not always
                        better than the reading before it

The last line is the trap. Recovery is the usual case -- trapped charge
in the oxide detraps and the parameter walks back toward its baseline --
but bipolar junction surfaces can carry the opposite behaviour, where
interface state build-up continues through the soak and the annealed
reading sits further from the baseline than the irradiated one. A rule
that only ever compared the annealed reading would pass a part whose
worst state it never looked at, and a rule that only ever compared the
irradiated reading would reject a part the drawing accepts.

What this module decides, per parameter and then per part and lot:

    traceability    whether the limits came from a controlled drawing
    compliance      both readings against the drawing limit, tie
                    admissible
    recovery        the share of the irradiation shift the anneal
                    gave back
    residual        the shift the mission still carries
    direction       whether the anneal helped or hurt

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

PART_ACCEPTED = "part-accepted"
PART_ACCEPTED_WITH_ADVISORY = "part-accepted-with-advisory"
PART_REJECTED_POST_IRRADIATION = "part-rejected-on-the-irradiated-reading"
PART_REJECTED_POST_ANNEAL = "part-rejected-on-the-annealed-reading"
PART_REJECTED_BOTH_READINGS = "part-rejected-on-both-readings"

LOT_ACCEPTED = "irradiated-lot-accepted"
LOT_ACCEPTED_WITH_ADVISORY = "irradiated-lot-accepted-with-advisory"
LOT_CONTAINS_REJECTS = "irradiated-lot-contains-rejects"
LOT_REJECT_ALLOWANCE_EXCEEDED = "irradiated-lot-reject-allowance-exceeded"

MAXIMUM_LIMIT = "maximum"
MINIMUM_LIMIT = "minimum"
_LIMIT_DIRECTIONS = (MAXIMUM_LIMIT, MINIMUM_LIMIT)

DEFAULT_SENTENCING_POLICY = {
    "advisory_margin_fraction": 0.05,
    "min_recovery_fraction": 0.20,
    "reverse_anneal_tolerance_fraction": 0.01,
    "lot_reject_allowance_fraction": 0.10,
}

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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between 0 and 1, got %r" % (name, value))
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(
            "%s must be a non-empty string; an untraceable limit cannot carry "
            "an acceptance decision" % (name,)
        )
    return value.strip()


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_sentencing_policy(policy):
    """Check the sentencing policy is complete and internally consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_fraction(
        "advisory_margin_fraction", policy.get("advisory_margin_fraction")
    )
    _require_fraction("min_recovery_fraction", policy.get("min_recovery_fraction"))
    _require_fraction(
        "reverse_anneal_tolerance_fraction",
        policy.get("reverse_anneal_tolerance_fraction"),
    )
    _require_fraction(
        "lot_reject_allowance_fraction",
        policy.get("lot_reject_allowance_fraction"),
    )
    return policy


def validate_drawing_limit(limit):
    """Refuse a limit that no controlled drawing and no test condition backs."""
    if not isinstance(limit, dict):
        raise ValueError("limit must be a mapping, got %r" % (limit,))
    _require_text("parameter", limit.get("parameter"))
    _require_text("drawing_reference", limit.get("drawing_reference"))
    _require_text("drawing_issue", limit.get("drawing_issue"))
    _require_text("condition", limit.get("condition"))
    direction = limit.get("direction")
    if direction not in _LIMIT_DIRECTIONS:
        raise ValueError(
            "direction must be one of %s, got %r" % (list(_LIMIT_DIRECTIONS), direction)
        )
    value = _require_number("limit_value", limit.get("limit_value"))
    if value == 0.0:
        raise ValueError(
            "limit_value must not be zero; a margin has nothing to be a "
            "fraction of"
        )
    return limit


def validate_reading(reading):
    """Refuse a readout missing any of the three states the clause compares."""
    if not isinstance(reading, dict):
        raise ValueError("reading must be a mapping, got %r" % (reading,))
    for key in ("pre_irradiation", "post_irradiation", "post_anneal"):
        if key not in reading:
            raise ValueError(
                "reading is missing %s; an absent state is not a repeated one" % (key,)
            )
        _require_number(key, reading[key])
    return reading


def meets_limit(value, limit):
    """True when a reading sits inside its drawing limit. A tie is admissible."""
    validate_drawing_limit(limit)
    reading = _require_number("value", value)
    bound = float(limit["limit_value"])
    if limit["direction"] == MAXIMUM_LIMIT:
        return _at_most(reading, bound)
    return _at_least(reading, bound)


def limit_margin_fraction(value, limit):
    """Signed margin as a fraction of the limit. Positive means inside it."""
    validate_drawing_limit(limit)
    reading = _require_number("value", value)
    bound = float(limit["limit_value"])
    if limit["direction"] == MAXIMUM_LIMIT:
        return (bound - reading) / abs(bound)
    return (reading - bound) / abs(bound)


def irradiation_shift(reading):
    """How far the ionising exposure moved the parameter off its baseline."""
    validate_reading(reading)
    return float(reading["post_irradiation"]) - float(reading["pre_irradiation"])


def residual_shift(reading):
    """How far the parameter still sits off baseline once the anneal is done."""
    validate_reading(reading)
    return float(reading["post_anneal"]) - float(reading["pre_irradiation"])


def annealing_recovery_fraction(reading):
    """Share of the irradiation-induced shift the anneal gave back.

    1.0 is a full return to the pre-irradiation baseline, 0.0 is a soak
    that changed nothing, and a negative value is a part that moved
    further away during the anneal than the irradiation left it.
    """
    validate_reading(reading)
    shift = irradiation_shift(reading)
    if math.isclose(shift, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        raise ValueError(
            "the irradiation left no shift to recover, so a recovery fraction "
            "has no denominator"
        )
    return (float(reading["post_irradiation"]) - float(reading["post_anneal"])) / shift


def is_reverse_annealing(reading, policy=DEFAULT_SENTENCING_POLICY):
    """True when the soak left the parameter worse than the irradiation did."""
    validate_sentencing_policy(policy)
    validate_reading(reading)
    tolerance = float(policy["reverse_anneal_tolerance_fraction"])
    shift = abs(irradiation_shift(reading))
    residual = abs(residual_shift(reading))
    if math.isclose(shift, 0.0, rel_tol=_REL_TOL, abs_tol=_ABS_TOL):
        return residual > tolerance * max(
            abs(float(reading["pre_irradiation"])), 1.0
        )
    return residual > shift * (1.0 + tolerance)


def worst_reading(reading):
    """The state a limit has to be judged against when both are compared.

    For a maximum-limited parameter that is the larger of the two
    post-exposure readings; for a minimum-limited one the smaller. The
    caller supplies the direction through assess_parameter, so this
    helper simply hands back both states in a fixed order.
    """
    validate_reading(reading)
    return (float(reading["post_irradiation"]), float(reading["post_anneal"]))


def assess_parameter(limit, reading, policy=DEFAULT_SENTENCING_POLICY):
    """Judge one parameter's irradiated and annealed readings against the drawing."""
    validate_sentencing_policy(policy)
    validate_drawing_limit(limit)
    validate_reading(reading)

    advisory_band = float(policy["advisory_margin_fraction"])
    min_recovery = float(policy["min_recovery_fraction"])

    post_irradiation = float(reading["post_irradiation"])
    post_anneal = float(reading["post_anneal"])

    irradiated_ok = meets_limit(post_irradiation, limit)
    annealed_ok = meets_limit(post_anneal, limit)
    irradiated_margin = limit_margin_fraction(post_irradiation, limit)
    annealed_margin = limit_margin_fraction(post_anneal, limit)

    try:
        recovery = annealing_recovery_fraction(reading)
    except ValueError:
        recovery = None

    findings = []
    result = {
        "parameter": limit["parameter"],
        "drawing_reference": limit["drawing_reference"],
        "drawing_issue": limit["drawing_issue"],
        "post_irradiation_meets_limit": irradiated_ok,
        "post_anneal_meets_limit": annealed_ok,
        "post_irradiation_margin_fraction": irradiated_margin,
        "post_anneal_margin_fraction": annealed_margin,
        "irradiation_shift": irradiation_shift(reading),
        "residual_shift": residual_shift(reading),
        "recovery_fraction": recovery,
        "reverse_annealing": is_reverse_annealing(reading, policy),
        "findings": findings,
    }

    if not irradiated_ok:
        findings.append(
            "%s breaches its %s drawing limit on the irradiated reading by %.4f "
            "of the limit" % (limit["parameter"], limit["direction"], -irradiated_margin)
        )
    if not annealed_ok:
        findings.append(
            "%s breaches its %s drawing limit on the annealed reading by %.4f "
            "of the limit" % (limit["parameter"], limit["direction"], -annealed_margin)
        )
    if result["reverse_annealing"]:
        findings.append(
            "%s sits further off baseline after the anneal than after the "
            "irradiation; the soak did not recover this parameter"
            % (limit["parameter"],)
        )
    elif recovery is not None and recovery < min_recovery:
        findings.append(
            "%s recovered %.4f of its irradiation shift against the %.4f the "
            "policy expects" % (limit["parameter"], recovery, min_recovery)
        )

    if not irradiated_ok and not annealed_ok:
        result["disposition"] = PART_REJECTED_BOTH_READINGS
        return result
    if not irradiated_ok:
        result["disposition"] = PART_REJECTED_POST_IRRADIATION
        return result
    if not annealed_ok:
        result["disposition"] = PART_REJECTED_POST_ANNEAL
        return result

    tighter = min(irradiated_margin, annealed_margin)
    if _at_most(tighter, advisory_band) and not math.isclose(
        tighter, advisory_band, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    ):
        findings.append(
            "%s passes with only %.4f of the limit left and the mission has "
            "degradation still to add" % (limit["parameter"], tighter)
        )
        result["disposition"] = PART_ACCEPTED_WITH_ADVISORY
        return result
    if findings:
        result["disposition"] = PART_ACCEPTED_WITH_ADVISORY
        return result

    result["disposition"] = PART_ACCEPTED
    return result


def assess_part(part, limits, policy=DEFAULT_SENTENCING_POLICY):
    """Roll every parameter of one irradiated part into a single disposition."""
    validate_sentencing_policy(policy)
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping, got %r" % (part,))
    if not isinstance(limits, (list, tuple)) or not limits:
        raise ValueError("limits must be a non-empty sequence of drawing limits")
    serial = _require_text("serial", part.get("serial"))
    readings = part.get("readings")
    if not isinstance(readings, dict) or not readings:
        raise ValueError("part %s carries no readings mapping" % (serial,))

    parameter_results = []
    findings = []
    for limit in limits:
        validate_drawing_limit(limit)
        name = limit["parameter"]
        if name not in readings:
            raise ValueError(
                "part %s has no reading for %s; an unmeasured parameter is not "
                "a passing one" % (serial, name)
            )
        outcome = assess_parameter(limit, readings[name], policy)
        parameter_results.append(outcome)
        findings.extend(outcome["findings"])

    dispositions = [outcome["disposition"] for outcome in parameter_results]
    if PART_REJECTED_BOTH_READINGS in dispositions:
        disposition = PART_REJECTED_BOTH_READINGS
    elif (
        PART_REJECTED_POST_IRRADIATION in dispositions
        and PART_REJECTED_POST_ANNEAL in dispositions
    ):
        disposition = PART_REJECTED_BOTH_READINGS
    elif PART_REJECTED_POST_IRRADIATION in dispositions:
        disposition = PART_REJECTED_POST_IRRADIATION
    elif PART_REJECTED_POST_ANNEAL in dispositions:
        disposition = PART_REJECTED_POST_ANNEAL
    elif PART_ACCEPTED_WITH_ADVISORY in dispositions:
        disposition = PART_ACCEPTED_WITH_ADVISORY
    else:
        disposition = PART_ACCEPTED

    return {
        "serial": serial,
        "parameters": tuple(parameter_results),
        "disposition": disposition,
        "findings": findings,
    }


def is_rejected(disposition):
    """True for any of the three reject dispositions."""
    if not isinstance(disposition, str):
        raise ValueError("disposition must be a string, got %r" % (disposition,))
    return disposition in (
        PART_REJECTED_POST_IRRADIATION,
        PART_REJECTED_POST_ANNEAL,
        PART_REJECTED_BOTH_READINGS,
    )


def assess_irradiated_lot(case, policy=DEFAULT_SENTENCING_POLICY):
    """Full clause 12.6.11.1.2 judgement for one irradiated and annealed lot."""
    validate_sentencing_policy(policy)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    limits = case.get("drawing_limits")
    if not isinstance(limits, (list, tuple)) or not limits:
        raise ValueError(
            "case is missing drawing_limits; the control drawing is where the "
            "pass criteria come from"
        )
    parts = case.get("parts")
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError(
            "case is missing parts; an empty lot is not an accepted one"
        )

    allowance = float(policy["lot_reject_allowance_fraction"])
    part_results = [assess_part(part, limits, policy) for part in parts]
    rejected = [r for r in part_results if is_rejected(r["disposition"])]
    advisory = [
        r for r in part_results if r["disposition"] == PART_ACCEPTED_WITH_ADVISORY
    ]
    reject_share = len(rejected) / float(len(part_results))

    findings = []
    for outcome in part_results:
        for text in outcome["findings"]:
            findings.append("%s: %s" % (outcome["serial"], text))

    result = {
        "part_count": len(part_results),
        "parts": tuple(part_results),
        "rejected_serials": tuple(r["serial"] for r in rejected),
        "advisory_serials": tuple(r["serial"] for r in advisory),
        "reject_share": reject_share,
        "reject_allowance_fraction": allowance,
        "findings": findings,
    }

    if not _at_most(reject_share, allowance):
        result["verdict"] = LOT_REJECT_ALLOWANCE_EXCEEDED
        return result
    if rejected:
        result["verdict"] = LOT_CONTAINS_REJECTS
        return result
    if advisory or findings:
        result["verdict"] = LOT_ACCEPTED_WITH_ADVISORY
        return result
    result["verdict"] = LOT_ACCEPTED
    return result
