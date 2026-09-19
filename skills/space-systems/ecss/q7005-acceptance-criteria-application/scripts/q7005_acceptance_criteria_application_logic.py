"""Acceptance of an IR organic contamination result against a cleanliness level.

Anchor: ECSS-Q-ST-70-05C, the acceptance clause of infrared detection of
organic contamination on surfaces, read against the cleanliness levels
carried by the contamination and cleanliness control practice
ECSS-Q-ST-70-01C (paraphrased into an implementable procedure; no
standard text is reproduced).

Procedure implemented here:

1. The requirement is an areal organic level on a named surface, and the
   result is an areal organic level on the same surface. Both are mass
   per unit area, so the comparison is only meaningful once the result
   has been brought onto that footing.
2. An indirect result arrives as the mass a rinse or a wipe recovered,
   not as the mass that was on the surface. It is divided by the
   recovery fraction before it is compared; comparing the extracted
   figure understates the surface and passes a dirty part.
3. A measurement carries an uncertainty, and the decision rule says who
   pays for it. Simple acceptance spends none of it, guarded acceptance
   spends all of it against the applicant, and a banded rule leaves a
   region either side of the limit where the measurement decides
   nothing.
4. A non-detect is a bound, not a zero. It demonstrates compliance when
   the quantitation limit itself sits at or under the required level,
   and demonstrates nothing at all when the method is coarser than the
   level being verified.
5. A surface over its level is not automatically out, but the route is
   narrow: an approved deviation plus an assessment of what the excess
   does to the contamination budget. An indeterminate result cannot take
   that route, because nobody yet knows what is being deviated.

Stdlib only, offline, deterministic.
"""

# Areal organic cleanliness levels, in milligrams per square metre. The
# names are local handles for the graded levels a contamination control
# plan allocates to a surface; a plan that uses its own names passes the
# limit in directly.
ORGANIC_CLEANLINESS_LEVELS = {
    "level-a": 1.0,
    "level-b": 2.0,
    "level-c": 5.0,
    "level-d": 10.0,
}

VALID_CLEANLINESS_LEVELS = tuple(sorted(ORGANIC_CLEANLINESS_LEVELS))

RULE_SIMPLE_ACCEPTANCE = "simple-acceptance"
RULE_GUARDED_ACCEPTANCE = "guarded-acceptance"
RULE_BANDED_ACCEPTANCE = "banded-acceptance"

VALID_DECISION_RULES = (
    RULE_SIMPLE_ACCEPTANCE,
    RULE_GUARDED_ACCEPTANCE,
    RULE_BANDED_ACCEPTANCE,
)

METHOD_DIRECT = "direct"
METHOD_INDIRECT = "indirect"
VALID_METHOD_KINDS = (METHOD_DIRECT, METHOD_INDIRECT)

COMPLIANT = "compliant"
COMPLIANT_ON_DEVIATION = "compliant-on-approved-deviation"
NON_COMPLIANT = "non-compliant"
INDETERMINATE = "indeterminate"

# Areal levels are quotients of a weighed residue by a measured area, so
# a value that should sit exactly on a limit can land a few units in the
# last place past it. This absorbs that representation error only; no
# limit is ever widened.
AREAL_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and value > maximum:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return float(value)


def _optional_numeric(label, value, minimum=None, maximum=None):
    if value is None:
        return None
    return _numeric(label, value, minimum, maximum)


def _optional_reference(label, value):
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string when present" % label)
    return value.strip()


def level_limit(level_name):
    """Areal organic limit, in mg/m2, for a named cleanliness level."""
    if level_name not in ORGANIC_CLEANLINESS_LEVELS:
        raise ValueError(
            "unknown cleanliness level %r (expected one of %s)"
            % (level_name, ", ".join(VALID_CLEANLINESS_LEVELS))
        )
    return ORGANIC_CLEANLINESS_LEVELS[level_name]


def required_limit(required_level):
    """Resolve a required level given either as a name or as a number."""
    if isinstance(required_level, str):
        return level_limit(required_level)
    return _numeric("required_level", required_level, 0.0)


def recovery_corrected_level(extracted_level_mg_m2, recovery_fraction):
    """Surface level implied by an extracted level and its recovery."""
    extracted = _numeric("extracted_level_mg_m2", extracted_level_mg_m2, 0.0)
    recovery = _numeric("recovery_fraction", recovery_fraction, 0.0, 1.0)
    if recovery <= 0.0:
        raise ValueError("recovery_fraction must be greater than zero")
    return extracted / recovery


def within_level(value, limit):
    """True when an areal value sits at or under its level limit."""
    val = _numeric("value", value)
    lim = _numeric("limit", limit)
    return val <= lim + AREAL_TOLERANCE


def decision_interval(value, expanded_uncertainty, decision_rule):
    """Interval the decision rule compares against the level limit."""
    val = _numeric("value", value, 0.0)
    if decision_rule not in VALID_DECISION_RULES:
        raise ValueError(
            "unknown decision rule %r (expected one of %s)"
            % (decision_rule, ", ".join(VALID_DECISION_RULES))
        )
    unc = _optional_numeric("expanded_uncertainty", expanded_uncertainty, 0.0)
    if decision_rule == RULE_SIMPLE_ACCEPTANCE:
        return (val, val)
    if unc is None:
        raise ValueError(
            "decision rule %r needs an expanded uncertainty" % decision_rule
        )
    if decision_rule == RULE_GUARDED_ACCEPTANCE:
        return (val, val + unc)
    return (max(val - unc, 0.0), val + unc)


def validate_result(record):
    """Validate one surface result record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("result must be a mapping")
    surface = record.get("surface")
    if not isinstance(surface, str) or not surface.strip():
        raise ValueError("result needs a non-empty string surface")
    surface = surface.strip()

    method_kind = record.get("method_kind", METHOD_DIRECT)
    if method_kind not in VALID_METHOD_KINDS:
        raise ValueError(
            "%s method_kind %r must be one of %s"
            % (surface, method_kind, ", ".join(VALID_METHOD_KINDS))
        )

    detected = record.get("detected", True)
    if not isinstance(detected, bool):
        raise ValueError("%s detected must be a boolean" % surface)

    measured = _optional_numeric(
        "%s measured_level_mg_m2" % surface, record.get("measured_level_mg_m2"), 0.0
    )
    quant = _optional_numeric(
        "%s quantitation_limit_mg_m2" % surface,
        record.get("quantitation_limit_mg_m2"),
        0.0,
    )
    if detected and measured is None:
        raise ValueError("%s reports a detection with no measured level" % surface)
    if not detected and quant is None:
        raise ValueError(
            "%s reports a non-detect with no quantitation limit to bound it" % surface
        )
    if not detected and measured is not None:
        raise ValueError(
            "%s reports a non-detect and a measured level at once" % surface
        )

    recovery = _optional_numeric(
        "%s recovery_fraction" % surface, record.get("recovery_fraction"), 0.0, 1.0
    )
    if method_kind == METHOD_INDIRECT and recovery is None:
        raise ValueError(
            "%s is an indirect result with no recovery fraction to correct it"
            % surface
        )
    if method_kind == METHOD_INDIRECT and recovery == 0.0:
        raise ValueError("%s recovery_fraction must be greater than zero" % surface)

    uncertainty = _optional_numeric(
        "%s expanded_uncertainty_mg_m2" % surface,
        record.get("expanded_uncertainty_mg_m2"),
        0.0,
    )
    return {
        "surface": surface,
        "method_kind": method_kind,
        "detected": detected,
        "measured_level_mg_m2": measured,
        "quantitation_limit_mg_m2": quant,
        "recovery_fraction": recovery,
        "expanded_uncertainty_mg_m2": uncertainty,
        "deviation_reference": _optional_reference(
            "%s deviation_reference" % surface, record.get("deviation_reference")
        ),
        "effects_assessment_reference": _optional_reference(
            "%s effects_assessment_reference" % surface,
            record.get("effects_assessment_reference"),
        ),
    }


def surface_level(record):
    """Areal surface level implied by a result, recovery included."""
    norm = validate_result(record)
    if not norm["detected"]:
        return None
    value = norm["measured_level_mg_m2"]
    if norm["method_kind"] == METHOD_INDIRECT:
        return recovery_corrected_level(value, norm["recovery_fraction"])
    return value


def evaluate_surface(record, required_level, decision_rule=RULE_GUARDED_ACCEPTANCE):
    """Grade one surface result against the level it has to meet."""
    norm = validate_result(record)
    limit = required_limit(required_level)
    if decision_rule not in VALID_DECISION_RULES:
        raise ValueError(
            "unknown decision rule %r (expected one of %s)"
            % (decision_rule, ", ".join(VALID_DECISION_RULES))
        )

    findings = []
    graded_value = None
    interval = None

    if not norm["detected"]:
        bound = norm["quantitation_limit_mg_m2"]
        if norm["method_kind"] == METHOD_INDIRECT:
            bound = recovery_corrected_level(bound, norm["recovery_fraction"])
        graded_value = bound
        interval = (0.0, bound)
        if within_level(bound, limit):
            verdict = COMPLIANT
        else:
            verdict = INDETERMINATE
            findings.append("quantitation-limit-coarser-than-the-required-level")
    else:
        graded_value = surface_level(norm)
        interval = decision_interval(
            graded_value, norm["expanded_uncertainty_mg_m2"], decision_rule
        )
        if within_level(interval[1], limit):
            verdict = COMPLIANT
        elif decision_rule == RULE_BANDED_ACCEPTANCE and within_level(
            interval[0], limit
        ):
            verdict = INDETERMINATE
            findings.append("uncertainty-band-straddles-the-required-level")
        else:
            verdict = NON_COMPLIANT
            findings.append("surface-level-above-the-required-level")

    if verdict == NON_COMPLIANT:
        if norm["deviation_reference"] and norm["effects_assessment_reference"]:
            verdict = COMPLIANT_ON_DEVIATION
        elif norm["deviation_reference"]:
            findings.append("deviation-cited-without-an-effects-assessment")
        elif norm["effects_assessment_reference"]:
            findings.append("effects-assessment-cited-without-a-deviation")
    elif verdict == INDETERMINATE and norm["deviation_reference"]:
        findings.append("deviation-offered-against-an-indeterminate-result")

    return {
        "surface": norm["surface"],
        "method_kind": norm["method_kind"],
        "detected": norm["detected"],
        "graded_level_mg_m2": graded_value,
        "decision_interval_mg_m2": interval,
        "required_limit_mg_m2": limit,
        "decision_rule": decision_rule,
        "verdict": verdict,
        "findings": findings,
    }


def assess_acceptance(records, required_level,
                      decision_rule=RULE_GUARDED_ACCEPTANCE):
    """Grade a list of surface results against one required level."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    limit = required_limit(required_level)
    graded = []
    seen = set()
    for record in records:
        row = evaluate_surface(record, required_level, decision_rule)
        if row["surface"] in seen:
            raise ValueError("duplicate surface %r" % (row["surface"],))
        seen.add(row["surface"])
        graded.append(row)
    return {
        "required_limit_mg_m2": limit,
        "decision_rule": decision_rule,
        "surfaces": graded,
        "compliant": [r["surface"] for r in graded if r["verdict"] == COMPLIANT],
        "on_deviation": [
            r["surface"] for r in graded if r["verdict"] == COMPLIANT_ON_DEVIATION
        ],
        "indeterminate": [
            r["surface"] for r in graded if r["verdict"] == INDETERMINATE
        ],
        "non_compliant": [
            r["surface"] for r in graded if r["verdict"] == NON_COMPLIANT
        ],
        "clear": all(r["verdict"] == COMPLIANT for r in graded),
    }
