"""Baseline rules steering a Class 2 commercial EEE part choice.

Anchor: ECSS-Q-ST-60-13C clause 5.2.2.1 (the baseline rule set a candidate
commercial part is measured against before it may enter a design at the
intermediate assurance class). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Put the candidate part through the baseline rules: authentic provenance, a
   certified manufacturer quality system, a controlled procurement route,
   flight lot homogeneity, a rated temperature range enveloping the mission
   range with its declared margin, a change-notification agreement and a
   declared radiation capability.
2. Separate the one rule that is a hard bar from the rules a declared
   mitigation can carry. This graded treatment is what distinguishes the
   intermediate class from the highest one, where a failed baseline rule bars
   the part outright.
3. Accept a mitigation only where it is the measure recognised for that rule,
   and only inside the limit the measure carries -- an uprating assessment
   holds up to a declared kelvin cap on the temperature shortfall and no
   further.
4. Sum the residual risk the mitigated rules leave and compare it with the
   declared ceiling, so that a part carried by four separate mitigations is
   refused even though each one was individually valid.
5. Return every failed rule, the temperature shortfall in kelvin, the residual
   risk and one admissibility verdict.
"""

import math

__all__ = [
    "RISK_TOLERANCE",
    "BASELINE_RULES",
    "CONTROLLED_PROCUREMENT_ROUTES",
    "PROCUREMENT_ROUTES",
    "UPRATING_CAP_K",
    "DEFAULT_RISK_CEILING",
    "VERDICTS",
    "validate_temperature_case",
    "temperature_shortfall",
    "evaluate_rules",
    "validate_mitigation",
    "mitigation_effective",
    "residual_risk",
    "assess_class2_part_admissibility",
]

# Residual risk is a sum of declared shares and the shortfall a difference of
# declared temperatures; an exactly-met limit can land a ULP out. Absorb that
# here, never by moving the limit.
RISK_TOLERANCE = 1e-9

# Rule -> whether a mitigation may carry a failure, the measure recognised for
# it, and the residual risk share a mitigated failure leaves behind.
BASELINE_RULES = {
    "authentic-provenance": {
        "mitigable": False,
        "measure": None,
        "residual": 0.0,
    },
    "manufacturer-quality-system": {
        "mitigable": True,
        "measure": "manufacturer-audit-report",
        "residual": 0.20,
    },
    "controlled-procurement-route": {
        "mitigable": True,
        "measure": "incoming-inspection-and-counterfeit-screening",
        "residual": 0.25,
    },
    "flight-lot-homogeneity": {
        "mitigable": True,
        "measure": "lot-by-lot-acceptance-testing",
        "residual": 0.20,
    },
    "temperature-range-envelope": {
        "mitigable": True,
        "measure": "uprating-assessment",
        "residual": 0.15,
    },
    "change-notification-agreement": {
        "mitigable": True,
        "measure": "periodic-construction-audit",
        "residual": 0.15,
    },
    "radiation-capability-declared": {
        "mitigable": True,
        "measure": "part-level-radiation-test",
        "residual": 0.10,
    },
}

PROCUREMENT_ROUTES = (
    "manufacturer-direct",
    "franchised-distributor",
    "independent-distributor",
    "open-market",
)

CONTROLLED_PROCUREMENT_ROUTES = ("manufacturer-direct", "franchised-distributor")

# An uprating assessment carries a temperature shortfall only this far.
UPRATING_CAP_K = 15.0

DEFAULT_RISK_CEILING = 0.35

VERDICTS = ("admissible", "admissible-with-mitigation", "not-admissible")


def _require_text(value, label):
    """Return a non-blank stripped string, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def _require_bool(value, label):
    """Return a real boolean, or raise. An undeclared fact is unknown, not false."""
    if not isinstance(value, bool):
        raise ValueError("%s must be declared true or false, got %r" % (label, value))
    return value


def _require_real(value, label):
    """Return a finite float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _at_or_below(value, limit):
    """Return True when value does not exceed limit, tolerating representation error."""
    return value < limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=RISK_TOLERANCE
    )


def validate_temperature_case(case):
    """Return a validated rated-versus-mission temperature case in degrees Celsius."""
    if not isinstance(case, dict):
        raise ValueError("temperature case must be a mapping")
    values = {}
    for key in ("rated_min_c", "rated_max_c", "mission_min_c", "mission_max_c"):
        if key not in case:
            raise ValueError("temperature case missing %s" % key)
        values[key] = _require_real(case[key], key)
    margin = _require_real(case.get("margin_k", 0.0), "margin_k")
    if margin < 0.0:
        raise ValueError("margin_k must not be negative, got %r" % (case.get("margin_k"),))
    if values["rated_min_c"] >= values["rated_max_c"]:
        raise ValueError("rated temperature range is empty or inverted")
    if values["mission_min_c"] >= values["mission_max_c"]:
        raise ValueError("mission temperature range is empty or inverted")
    values["margin_k"] = margin
    return values


def temperature_shortfall(case):
    """Return the total kelvin by which the rated range fails to envelope the mission."""
    values = validate_temperature_case(case)
    margin = values["margin_k"]
    hot = (values["mission_max_c"] + margin) - values["rated_max_c"]
    cold = values["rated_min_c"] - (values["mission_min_c"] - margin)
    total = 0.0
    if hot > 0.0:
        total += hot
    if cold > 0.0:
        total += cold
    return total


def evaluate_rules(candidate):
    """Return the met/unmet outcome of every baseline rule for a candidate part.

    candidate keys: reference, authentic_provenance, quality_system_certified,
    procurement_route, flight_lot_homogeneous, change_notification_agreed,
    radiation_capability_declared, temperature (mapping).
    """
    if not isinstance(candidate, dict):
        raise ValueError("candidate must be a mapping")
    _require_text(candidate.get("reference"), "candidate reference")
    route = _require_text(candidate.get("procurement_route"), "procurement_route")
    if route not in PROCUREMENT_ROUTES:
        raise ValueError("%s is not a declared procurement route" % route)
    if "temperature" not in candidate:
        raise ValueError("candidate missing the temperature case")
    shortfall = temperature_shortfall(candidate["temperature"])
    outcome = {
        "authentic-provenance": _require_bool(
            candidate.get("authentic_provenance"), "authentic_provenance"
        ),
        "manufacturer-quality-system": _require_bool(
            candidate.get("quality_system_certified"), "quality_system_certified"
        ),
        "controlled-procurement-route": route in CONTROLLED_PROCUREMENT_ROUTES,
        "flight-lot-homogeneity": _require_bool(
            candidate.get("flight_lot_homogeneous"), "flight_lot_homogeneous"
        ),
        "temperature-range-envelope": _at_or_below(shortfall, 0.0),
        "change-notification-agreement": _require_bool(
            candidate.get("change_notification_agreed"), "change_notification_agreed"
        ),
        "radiation-capability-declared": _require_bool(
            candidate.get("radiation_capability_declared"),
            "radiation_capability_declared",
        ),
    }
    if set(outcome) != set(BASELINE_RULES):
        raise ValueError("rule outcome set does not match the baseline rule catalogue")
    return outcome, shortfall


def validate_mitigation(record):
    """Return a validated mitigation record attached to one baseline rule."""
    if not isinstance(record, dict):
        raise ValueError("each mitigation record must be a mapping")
    rule = _require_text(record.get("rule"), "mitigation rule")
    if rule not in BASELINE_RULES:
        raise ValueError("%s is not a baseline rule" % rule)
    if not BASELINE_RULES[rule]["mitigable"]:
        raise ValueError(
            "rule %s is a hard bar; no mitigation carries a part past it" % rule
        )
    measure = _require_text(record.get("measure"), "mitigation measure")
    reference = record.get("reference")
    if reference is not None:
        reference = _require_text(reference, "mitigation reference for %s" % rule)
    return {"rule": rule, "measure": measure, "reference": reference}


def mitigation_effective(rule, measure, shortfall=0.0):
    """Return True when the measure is the one recognised for the rule and inside its limit."""
    if rule not in BASELINE_RULES:
        raise ValueError("%s is not a baseline rule" % rule)
    spec = BASELINE_RULES[rule]
    if not spec["mitigable"]:
        return False
    if _require_text(measure, "mitigation measure") != spec["measure"]:
        return False
    if rule == "temperature-range-envelope":
        gap = _require_real(shortfall, "temperature shortfall")
        if gap < 0.0:
            raise ValueError("temperature shortfall must not be negative")
        return _at_or_below(gap, UPRATING_CAP_K)
    return True


def residual_risk(rules):
    """Return the residual risk left by the mitigated rules."""
    if not isinstance(rules, (list, tuple)):
        raise ValueError("rules must be a sequence of baseline rule names")
    seen = []
    for entry in rules:
        rule = _require_text(entry, "baseline rule")
        if rule not in BASELINE_RULES:
            raise ValueError("%s is not a baseline rule" % rule)
        if rule in seen:
            raise ValueError("rule %s counted more than once" % rule)
        seen.append(rule)
    return math.fsum(BASELINE_RULES[rule]["residual"] for rule in seen)


def assess_class2_part_admissibility(spec):
    """Run the full clause 5.2.2.1 intermediate-class baseline rule assessment.

    spec keys: candidate (mapping), optional mitigations (sequence), optional
    risk_ceiling (default 0.35).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    if "candidate" not in spec:
        raise ValueError("spec missing required key 'candidate'")
    ceiling = _require_real(spec.get("risk_ceiling", DEFAULT_RISK_CEILING), "risk_ceiling")
    if ceiling < 0.0 or ceiling > 1.0:
        raise ValueError("risk_ceiling must lie in [0, 1], got %r" % (ceiling,))

    candidate = spec["candidate"]
    outcome, shortfall = evaluate_rules(candidate)
    raw = spec.get("mitigations", ())
    if not isinstance(raw, (list, tuple)):
        raise ValueError("mitigations must be a sequence of records")
    attached = {}
    for record in raw:
        checked = validate_mitigation(record)
        if checked["rule"] in attached:
            raise ValueError("more than one mitigation attached to %s" % checked["rule"])
        attached[checked["rule"]] = checked

    failed = tuple(sorted(rule for rule, met in outcome.items() if not met))
    mitigated = []
    unmitigated = []
    for rule in failed:
        record = attached.get(rule)
        if record is None:
            unmitigated.append(rule)
            continue
        if mitigation_effective(rule, record["measure"], shortfall):
            mitigated.append(rule)
        else:
            unmitigated.append(rule)

    unused = tuple(sorted(rule for rule in attached if rule not in failed))
    risk = residual_risk(mitigated)
    within = _at_or_below(risk, ceiling)

    findings = []
    for rule in unmitigated:
        findings.append(
            {
                "severity": 0,
                "rule": rule,
                "detail": "%s fails with no effective mitigation" % rule,
            }
        )
    for rule in mitigated:
        findings.append(
            {
                "severity": 1,
                "rule": rule,
                "detail": "%s fails, carried by %s, residual %.2f"
                % (rule, attached[rule]["measure"], BASELINE_RULES[rule]["residual"]),
            }
        )
    for rule in unused:
        findings.append(
            {
                "severity": 2,
                "rule": rule,
                "detail": "mitigation attached to %s, which the part already meets" % rule,
            }
        )
    if not within:
        findings.append(
            {
                "severity": 0,
                "rule": "residual-risk-ceiling",
                "detail": "residual risk %.2f exceeds the ceiling %.2f" % (risk, ceiling),
            }
        )
    findings.sort(key=lambda entry: (entry["severity"], entry["rule"]))

    if unmitigated or not within:
        verdict = "not-admissible"
    elif mitigated:
        verdict = "admissible-with-mitigation"
    else:
        verdict = "admissible"
    return {
        "reference": candidate["reference"],
        "rule_outcome": outcome,
        "failed_rules": failed,
        "mitigated_rules": tuple(mitigated),
        "unmitigated_rules": tuple(unmitigated),
        "unused_mitigations": unused,
        "temperature_shortfall_k": shortfall,
        "residual_risk": risk,
        "risk_ceiling": ceiling,
        "findings": findings,
        "verdict": verdict,
    }
