"""Objective screening for an electrostatic-discharge test on an array coupon.

Anchor: ECSS-E-ST-20-08C clause 5.5.1.5.1 (showing that sound design rules
limit the electrostatic-discharge risk on solar-array coupons). Paraphrased
into an implementable procedure; no standard text is reproduced.

The clause states a purpose, not a measurement, so the job this module does is
the one that purpose implies: deciding whether a planned coupon test can
actually show what it is meant to show. A test that never drives the mechanism
the design rules were written against, or that drives it on a coupon the rules
are not embodied on, produces a clean record and demonstrates nothing.

Procedure implemented here
--------------------------
1. Derive, from the declared environment, which recognized discharge mechanisms
   the coupon can really be driven into; a mechanism the environment cannot
   drive is outside the purpose of the test.
2. Group the declared design-rule provisions by the mechanism each one is meant
   to limit, and keep only those actually embodied on the coupon in a
   representative form.
3. Check the planned test conditions against every driving mechanism: the
   mechanism has to be exercised, and the applied bias and string current have
   to bound the worst case the environment presents.
4. Check the planned discharge population against the minimum the campaign
   declares, since a handful of events shows nothing about a design rule.
5. Report the covered and uncovered mechanisms, the coverage fraction and the
   findings; the purpose is demonstrable only when nothing is uncovered.
"""

import math

__all__ = [
    "ENVELOPE_ABSOLUTE_TOLERANCE",
    "ENVELOPE_RELATIVE_TOLERANCE",
    "RECOGNIZED_MECHANISMS",
    "assess_test_purpose",
    "at_or_above",
    "driving_mechanisms",
    "effective_rules",
    "envelope_shortfalls",
    "group_rules_by_mechanism",
    "normalize_mechanism",
    "validate_design_rules",
    "validate_environment",
    "validate_plan",
]

# Envelope comparisons are made against declared worst-case values that are
# usually sums of contributions, so an exactly-bounding envelope can land a few
# ULPs on the wrong side. Absorb that here rather than relaxing any envelope.
ENVELOPE_RELATIVE_TOLERANCE = 1e-12
ENVELOPE_ABSOLUTE_TOLERANCE = 1e-9

# The discharge mechanisms a coupon-level design rule can be written against.
RECOGNIZED_MECHANISMS = (
    "differential-surface-charging",
    "string-to-string-propagation",
    "triple-junction-inception",
)

_ENVIRONMENT_KEYS = (
    "differential_potential_v",
    "differential_onset_v",
    "exposed_dielectric_area_m2",
    "inception_threshold_v",
    "string_voltage_v",
    "propagation_threshold_v",
    "string_current_a",
    "sustaining_current_a",
)


def _real(value, label):
    """Return value as a finite float, rejecting booleans and non-numbers."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float."""
    out = _real(value, label)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def _flag(value, label):
    """Return a declared boolean flag, rejecting anything else."""
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def at_or_above(value, threshold):
    """Return True when value reaches threshold, tolerating an exact equality."""
    v = _real(value, "value")
    t = _real(threshold, "threshold")
    if v > t:
        return True
    return math.isclose(
        v, t, rel_tol=ENVELOPE_RELATIVE_TOLERANCE, abs_tol=ENVELOPE_ABSOLUTE_TOLERANCE
    )


def normalize_mechanism(name):
    """Return a recognized discharge-mechanism name, refusing anything else."""
    if not isinstance(name, str):
        raise ValueError("mechanism must be a string, got %r" % (name,))
    cleaned = name.strip().lower()
    if cleaned not in RECOGNIZED_MECHANISMS:
        raise ValueError(
            "unrecognized discharge mechanism %r; recognized: %s"
            % (name, ", ".join(RECOGNIZED_MECHANISMS))
        )
    return cleaned


def validate_environment(environment):
    """Return the declared environment as validated non-negative magnitudes."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    validated = {}
    for key in _ENVIRONMENT_KEYS:
        if key not in environment:
            raise ValueError("environment missing required key '%s'" % key)
        validated[key] = _non_negative(environment[key], "environment['%s']" % key)
    return validated


def driving_mechanisms(environment):
    """Return the mechanisms the declared environment can actually drive."""
    env = validate_environment(environment)
    driving = []
    if env["exposed_dielectric_area_m2"] > 0.0 and at_or_above(
        env["differential_potential_v"], env["differential_onset_v"]
    ):
        driving.append("differential-surface-charging")
    if at_or_above(env["differential_potential_v"], env["inception_threshold_v"]):
        driving.append("triple-junction-inception")
    if at_or_above(env["string_voltage_v"], env["propagation_threshold_v"]) and at_or_above(
        env["string_current_a"], env["sustaining_current_a"]
    ):
        driving.append("string-to-string-propagation")
    return tuple(sorted(driving))


def validate_design_rules(design_rules):
    """Return the declared design-rule provisions as validated records."""
    if not isinstance(design_rules, (list, tuple)) or not design_rules:
        raise ValueError("design_rules must be a non-empty sequence of rule records")
    seen = set()
    records = []
    for index, rule in enumerate(design_rules):
        if not isinstance(rule, dict):
            raise ValueError("design_rules[%d] must be a mapping" % index)
        for key in ("rule_id", "mechanism", "embodied_on_coupon", "representative"):
            if key not in rule:
                raise ValueError("design_rules[%d] missing required key '%s'" % (index, key))
        rule_id = rule["rule_id"]
        if not isinstance(rule_id, str) or not rule_id.strip():
            raise ValueError("design_rules[%d] rule_id must be a non-empty string" % index)
        rule_id = rule_id.strip()
        if rule_id in seen:
            raise ValueError("duplicate rule_id %r in design_rules" % rule_id)
        seen.add(rule_id)
        records.append({
            "rule_id": rule_id,
            "mechanism": normalize_mechanism(rule["mechanism"]),
            "embodied_on_coupon": _flag(
                rule["embodied_on_coupon"], "design_rules[%d] embodied_on_coupon" % index
            ),
            "representative": _flag(
                rule["representative"], "design_rules[%d] representative" % index
            ),
        })
    return records


def group_rules_by_mechanism(design_rules):
    """Return the validated rule records grouped under the mechanism each limits."""
    grouped = dict((mechanism, []) for mechanism in RECOGNIZED_MECHANISMS)
    for record in validate_design_rules(design_rules):
        grouped[record["mechanism"]].append(record)
    return grouped


def effective_rules(design_rules, mechanism):
    """Return the rules for one mechanism that the coupon really carries."""
    wanted = normalize_mechanism(mechanism)
    return [
        record
        for record in group_rules_by_mechanism(design_rules)[wanted]
        if record["embodied_on_coupon"] and record["representative"]
    ]


def validate_plan(plan):
    """Return the planned test conditions as a validated record."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    for key in ("mechanisms_exercised", "applied_bias_v", "applied_string_current_a",
                "discharge_count", "required_discharge_count"):
        if key not in plan:
            raise ValueError("plan missing required key '%s'" % key)
    exercised = plan["mechanisms_exercised"]
    if not isinstance(exercised, (list, tuple)):
        raise ValueError("plan['mechanisms_exercised'] must be a sequence")
    normalized = []
    for item in exercised:
        name = normalize_mechanism(item)
        if name not in normalized:
            normalized.append(name)
    for key in ("discharge_count", "required_discharge_count"):
        value = plan[key]
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("plan['%s'] must be an integer, got %r" % (key, value))
        if value < 0:
            raise ValueError("plan['%s'] must be non-negative, got %d" % (key, value))
    return {
        "mechanisms_exercised": tuple(sorted(normalized)),
        "applied_bias_v": _non_negative(plan["applied_bias_v"], "plan['applied_bias_v']"),
        "applied_string_current_a": _non_negative(
            plan["applied_string_current_a"], "plan['applied_string_current_a']"
        ),
        "discharge_count": int(plan["discharge_count"]),
        "required_discharge_count": int(plan["required_discharge_count"]),
    }


def envelope_shortfalls(environment, plan, mechanism):
    """Return the envelope findings for one mechanism, empty when it is bounded."""
    env = validate_environment(environment)
    conditions = validate_plan(plan)
    wanted = normalize_mechanism(mechanism)
    findings = []
    if wanted == "string-to-string-propagation":
        if not at_or_above(conditions["applied_bias_v"], env["string_voltage_v"]):
            findings.append(
                "applied bias %g V does not bound the worst-case string voltage %g V "
                "for %s" % (conditions["applied_bias_v"], env["string_voltage_v"], wanted)
            )
        if not at_or_above(
            conditions["applied_string_current_a"], env["string_current_a"]
        ):
            findings.append(
                "applied string current %g A does not bound the worst-case string "
                "current %g A for %s"
                % (conditions["applied_string_current_a"], env["string_current_a"], wanted)
            )
    else:
        if not at_or_above(conditions["applied_bias_v"], env["differential_potential_v"]):
            findings.append(
                "applied bias %g V does not bound the worst-case differential potential "
                "%g V for %s"
                % (conditions["applied_bias_v"], env["differential_potential_v"], wanted)
            )
    return findings


def assess_test_purpose(spec):
    """Run the full clause 5.5.1.5.1 test-objective screening.

    spec keys: environment, design_rules, plan.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("environment", "design_rules", "plan"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    environment = spec["environment"]
    design_rules = spec["design_rules"]
    conditions = validate_plan(spec["plan"])
    driving = driving_mechanisms(environment)
    grouped = group_rules_by_mechanism(design_rules)
    findings = []
    covered = []
    uncovered = []
    for mechanism in driving:
        mechanism_findings = []
        carried = effective_rules(design_rules, mechanism)
        if not carried:
            declared = grouped[mechanism]
            if declared:
                mechanism_findings.append(
                    "every design rule against %s is declared but not embodied on the "
                    "coupon in a representative form" % mechanism
                )
            else:
                mechanism_findings.append(
                    "no design rule against %s is declared, so the test cannot show one "
                    "limits the risk" % mechanism
                )
        if mechanism not in conditions["mechanisms_exercised"]:
            mechanism_findings.append(
                "the planned conditions never drive %s, which the environment does"
                % mechanism
            )
        mechanism_findings.extend(envelope_shortfalls(environment, spec["plan"], mechanism))
        if mechanism_findings:
            uncovered.append(mechanism)
            findings.extend(mechanism_findings)
        else:
            covered.append(mechanism)
    for mechanism in RECOGNIZED_MECHANISMS:
        for record in grouped[mechanism]:
            if record["embodied_on_coupon"] and not record["representative"]:
                findings.append(
                    "design rule %s is embodied on the coupon in a form that is not "
                    "representative of the flight array" % record["rule_id"]
                )
    if conditions["discharge_count"] < conditions["required_discharge_count"]:
        findings.append(
            "planned discharge population of %d falls short of the %d the campaign "
            "requires" % (conditions["discharge_count"], conditions["required_discharge_count"])
        )
    if not driving:
        findings.append(
            "the declared environment drives no recognized discharge mechanism, so a "
            "coupon test would demonstrate nothing about the design rules"
        )
        coverage = 0.0
    else:
        coverage = len(covered) / float(len(driving))
    return {
        "driving_mechanisms": driving,
        "covered_mechanisms": tuple(covered),
        "uncovered_mechanisms": tuple(uncovered),
        "coverage_fraction": coverage,
        "findings": findings,
        "purpose_demonstrable": not findings,
    }
