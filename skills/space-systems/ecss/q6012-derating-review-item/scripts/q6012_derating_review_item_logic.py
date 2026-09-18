"""Derating review item of a device design review.

Anchor: ECSS-Q-ST-60-12C clause 7.3.6 (design review -- the derating review
item). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate the declared stress items and the derating rules they cite.
2. Resolve each rule into a derated limit, moved away from the absolute
   maximum rating in the conservative direction of the bound it guards.
3. Inflate a nominal stress into its worst-case value with the declared
   uncertainty, in the direction that makes the stress worse.
4. Compare the worst-case stress with the derated limit on margin, so the
   comparison survives a scale that carries negative values, and report a
   utilisation ratio whenever the scale admits one.
5. Report a declared stress carrying no derating rule, and a required stress
   that was never declared, as open items rather than as passes.
6. Close the review item only when nothing is open.
"""

import math

__all__ = [
    "LIMIT_TOLERANCE",
    "DIRECTIONS",
    "MODES",
    "validate_rule",
    "derated_limit",
    "worst_case_stress",
    "stress_margin",
    "utilisation_ratio",
    "is_within_derated_limit",
    "assess_stress_item",
    "undeclared_stresses",
    "assess_derating_review",
]

# A margin comparison at the derated limit is a difference of two floating
# point products. Absorb that representation error here instead of relaxing
# the derating rule itself.
LIMIT_TOLERANCE = 1e-9

DIRECTIONS = ("upper", "lower")
MODES = ("fraction", "offset")


def _real(value, label, positive=False, non_negative=False):
    """Return value as a finite float, raising on anything else."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if positive and number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    if non_negative and number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def _name(value, label):
    """Return a non-empty stripped identifier string."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be empty" % label)
    return text


def validate_rule(rule, label="derating rule"):
    """Return the validated (mode, value, direction) of one derating rule."""
    if not isinstance(rule, dict):
        raise ValueError("%s must be a mapping, got %r" % (label, rule))
    for key in ("mode", "value", "direction"):
        if key not in rule:
            raise ValueError("%s missing required key '%s'" % (label, key))
    mode = _name(rule["mode"], "%s mode" % label).lower()
    if mode not in MODES:
        raise ValueError("%s mode must be one of %s, got %r" % (label, MODES, mode))
    direction = _name(rule["direction"], "%s direction" % label).lower()
    if direction not in DIRECTIONS:
        raise ValueError(
            "%s direction must be one of %s, got %r" % (label, DIRECTIONS, direction)
        )
    value = _real(rule["value"], "%s value" % label)
    if mode == "fraction":
        if value <= 0.0 or value > 1.0:
            raise ValueError(
                "%s fraction must lie in (0, 1], got %g" % (label, value)
            )
    elif value < 0.0:
        raise ValueError("%s offset must not be negative, got %g" % (label, value))
    return (mode, value, direction)


def derated_limit(rating, rule, label="derating rule"):
    """Return the derated limit a stress is actually judged against.

    A fraction rule scales the absolute maximum rating; an offset rule steps
    away from it. Either way the limit moves in the conservative direction of
    the bound: down for an upper bound, up for a lower one.
    """
    mode, value, direction = validate_rule(rule, label)
    if mode == "fraction":
        rated = _real(rating, "rating", positive=True)
        return rated * value if direction == "upper" else rated / value
    rated = _real(rating, "rating")
    return rated - value if direction == "upper" else rated + value


def worst_case_stress(nominal, uncertainty=0.0, direction="upper"):
    """Return the worst-case stress obtained by opening up the nominal value.

    The uncertainty is a fraction of the magnitude of the nominal stress, so a
    stress quoted on a scale that runs negative is still widened away from its
    bound rather than towards it.
    """
    bound = _name(direction, "direction").lower()
    if bound not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (DIRECTIONS, bound))
    value = _real(nominal, "nominal stress")
    spread = _real(uncertainty, "uncertainty", non_negative=True)
    if spread > 1.0:
        raise ValueError("uncertainty is a fraction in [0, 1], got %g" % spread)
    delta = abs(value) * spread
    return value + delta if bound == "upper" else value - delta


def stress_margin(stress, limit, direction="upper"):
    """Return the signed margin to the derated limit; negative is an exceedance."""
    bound = _name(direction, "direction").lower()
    if bound not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (DIRECTIONS, bound))
    applied = _real(stress, "stress")
    bound_value = _real(limit, "limit")
    return bound_value - applied if bound == "upper" else applied - bound_value


def utilisation_ratio(stress, limit, direction="upper"):
    """Return how much of the derated limit the stress consumes.

    Above one is an exceedance in both directions. The ratio needs a scale
    whose zero is physical, so it is refused when the denominator is not
    positive rather than being reported as a meaningless number.
    """
    bound = _name(direction, "direction").lower()
    if bound not in DIRECTIONS:
        raise ValueError("direction must be one of %s, got %r" % (DIRECTIONS, bound))
    applied = _real(stress, "stress")
    bound_value = _real(limit, "limit")
    denominator = bound_value if bound == "upper" else applied
    if denominator <= 0.0:
        raise ValueError(
            "utilisation needs a positive denominator; restate the stress on an "
            "absolute scale or judge this item on margin alone"
        )
    numerator = applied if bound == "upper" else bound_value
    return numerator / denominator


def is_within_derated_limit(stress, limit, direction="upper"):
    """Return True when the stress sits inside the derated limit."""
    margin = stress_margin(stress, limit, direction)
    tolerance = LIMIT_TOLERANCE * max(1.0, abs(_real(limit, "limit")))
    return margin >= -tolerance


def assess_stress_item(item, rules):
    """Assess one declared device stress against the derating rule it cites.

    item keys: device, parameter, rating, nominal_stress, optional uncertainty.
    rules maps a parameter name to a derating rule mapping.
    """
    if not isinstance(item, dict):
        raise ValueError("stress item must be a mapping, got %r" % (item,))
    if not isinstance(rules, dict):
        raise ValueError("rules must be a mapping of parameter to derating rule")
    for key in ("device", "parameter", "rating", "nominal_stress"):
        if key not in item:
            raise ValueError("stress item missing required key '%s'" % key)
    device = _name(item["device"], "device")
    parameter = _name(item["parameter"], "parameter").lower()
    if parameter not in rules:
        return {
            "device": device,
            "parameter": parameter,
            "covered": False,
            "compliant": False,
            "advisories": ["no derating rule declared for this stress"],
        }
    label = "derating rule for %s" % parameter
    mode, value, direction = validate_rule(rules[parameter], label)
    limit = derated_limit(item["rating"], rules[parameter], label)
    stress = worst_case_stress(
        item["nominal_stress"], item.get("uncertainty", 0.0), direction
    )
    advisories = []
    if mode == "fraction" and value == 1.0:
        advisories.append("rule applies no reduction to the absolute maximum rating")
    try:
        ratio = utilisation_ratio(stress, limit, direction)
    except ValueError:
        ratio = None
        advisories.append("scale admits no utilisation ratio; judged on margin")
    margin = stress_margin(stress, limit, direction)
    scale = max(1.0, abs(limit))
    return {
        "device": device,
        "parameter": parameter,
        "direction": direction,
        "mode": mode,
        "rating": _real(item["rating"], "rating"),
        "derated_limit": limit,
        "worst_case_stress": stress,
        "margin": margin,
        "normalised_margin": margin / scale,
        "utilisation": ratio,
        "covered": True,
        "compliant": is_within_derated_limit(stress, limit, direction),
        "advisories": advisories,
    }


def undeclared_stresses(items, required_parameters):
    """Return (device, parameter) pairs a device owes the review but never declared."""
    if not isinstance(items, (list, tuple)):
        raise ValueError("items must be a sequence of stress item mappings")
    if not isinstance(required_parameters, (list, tuple)):
        raise ValueError("required_parameters must be a sequence of parameter names")
    required = [_name(p, "required parameter").lower() for p in required_parameters]
    declared = {}
    order = []
    for item in items:
        if not isinstance(item, dict):
            raise ValueError("each stress item must be a mapping")
        device = _name(item.get("device", ""), "device")
        parameter = _name(item.get("parameter", ""), "parameter").lower()
        if device not in declared:
            declared[device] = set()
            order.append(device)
        declared[device].add(parameter)
    gaps = []
    for device in order:
        for parameter in required:
            if parameter not in declared[device]:
                gaps.append((device, parameter))
    return gaps


def assess_derating_review(spec):
    """Run the clause 7.3.6 derating review item end to end.

    spec keys: items (sequence of stress items), rules (parameter -> rule),
    optional required_parameters (parameters every listed device must declare).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("items", "rules"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    items = spec["items"]
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("spec['items'] must be a non-empty sequence")
    rules = spec["rules"]
    if not isinstance(rules, dict) or not rules:
        raise ValueError("spec['rules'] must be a non-empty mapping")
    normalised_rules = {}
    for parameter, rule in rules.items():
        key = _name(parameter, "rule parameter").lower()
        validate_rule(rule, "derating rule for %s" % key)
        normalised_rules[key] = rule
    records = [assess_stress_item(item, normalised_rules) for item in items]
    exceedances = [r for r in records if r["covered"] and not r["compliant"]]
    uncovered = [r for r in records if not r["covered"]]
    gaps = undeclared_stresses(items, spec.get("required_parameters", []))
    findings = []
    for record in exceedances:
        findings.append(
            "%s %s reaches %.6g against a derated limit of %.6g"
            % (
                record["device"],
                record["parameter"],
                record["worst_case_stress"],
                record["derated_limit"],
            )
        )
    for record in uncovered:
        findings.append(
            "%s declares %s with no derating rule to judge it against"
            % (record["device"], record["parameter"])
        )
    for device, parameter in gaps:
        findings.append("%s never declared a %s stress for the review" % (device, parameter))
    judged = [r for r in records if r["covered"]]
    worst = None
    if judged:
        worst = min(judged, key=lambda r: r["normalised_margin"])
    return {
        "records": records,
        "exceedances": exceedances,
        "uncovered": uncovered,
        "undeclared": gaps,
        "worst_case_item": worst,
        "findings": findings,
        "disposition": "closed" if not findings else "open",
    }
