"""Heritage of previously qualified parts and interchangeability of replaceable items.

Anchor: ECSS-E-ST-33-01 clauses 4.2.4.2 and 4.2.4.3 -- use previously qualified
parts and components, and make replaceable items interchangeable. Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Compare the environment and duty a part was qualified to against the
   environment and duty the new application imposes, parameter by parameter,
   with the sense of each parameter known (hotter is worse, colder is worse,
   more cycles is worse, lower pressure is worse).
2. Turn each comparison into an exceedance and a relative exceedance so a
   marginal overshoot and a gross one are not the same answer.
3. Decide between accepting the heritage, running a delta qualification, and
   requalifying in full, taking a changed configuration or a parameter the
   qualification never covered straight to a full requalification.
4. For a group of replaceable items, prove interchangeability by worst-case
   tolerance stack against every mating feature: any item must fit any mating
   part without selection, shimming or match marking, and without exceeding
   the loosest fit the function tolerates.
"""

import math

__all__ = [
    "PARAMETER_SENSE",
    "HERITAGE_ACCEPTED",
    "HERITAGE_DELTA",
    "HERITAGE_FULL",
    "DEFAULT_DELTA_LIMIT",
    "STACK_TOLERANCE",
    "validate_envelope",
    "severity",
    "envelope_assessment",
    "heritage_verdict",
    "assess_heritage",
    "validate_feature",
    "worst_case_clearance",
    "assess_interchangeability",
    "assess_parts_and_interchangeability",
]

# Which direction of each parameter is the severe one. "upper" means a larger
# number is harsher; "lower" means a smaller number is.
PARAMETER_SENSE = {
    "temperature_max_k": "upper",
    "temperature_min_k": "lower",
    "operating_cycles": "upper",
    "operating_hours": "upper",
    "peak_load_n": "upper",
    "random_vibration_grms": "upper",
    "radiation_dose_krad": "upper",
    "ambient_pressure_pa": "lower",
}

HERITAGE_ACCEPTED = "heritage-accepted"
HERITAGE_DELTA = "delta-qualification"
HERITAGE_FULL = "full-requalification"

# Beyond this relative exceedance a delta qualification is no longer an
# extension of the existing evidence; the part is being used somewhere new.
DEFAULT_DELTA_LIMIT = 0.25

# Stacks that should land exactly on zero clearance land a few ULPs off it.
STACK_TOLERANCE = 1.0e-9


def _require_text(value, label):
    """Return a stripped non-empty string."""
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value.strip()


def _require_real(value, label):
    """Return a finite float, refusing booleans and non-numerics."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _require_positive(value, label):
    """Return a strictly positive finite float."""
    number = _require_real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_non_negative(value, label):
    """Return a non-negative finite float."""
    number = _require_real(value, label)
    if number < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, number))
    return number


def validate_envelope(envelope, name="envelope"):
    """Return a validated environment and duty envelope.

    Every parameter must be one the sense table knows, and every value must be
    a positive magnitude: temperatures in kelvin, pressures in pascal, counts
    and durations as themselves.
    """
    if not isinstance(envelope, dict) or not envelope:
        raise ValueError("%s must be a non-empty mapping of parameter to value" % name)
    validated = {}
    for parameter, value in envelope.items():
        key = _require_text(parameter, "%s parameter name" % name)
        if key not in PARAMETER_SENSE:
            raise ValueError(
                "%s carries unknown parameter %r; the known set is %s"
                % (name, key, ", ".join(sorted(PARAMETER_SENSE)))
            )
        validated[key] = _require_positive(value, "%s[%s]" % (name, key))
    return validated


def severity(parameter, qualified, applied):
    """Return the exceedance of an applied value over a qualified bound."""
    if parameter not in PARAMETER_SENSE:
        raise ValueError("unknown parameter %r" % (parameter,))
    bound = _require_positive(qualified, "qualified %s" % parameter)
    value = _require_positive(applied, "applied %s" % parameter)
    if PARAMETER_SENSE[parameter] == "upper":
        exceedance = value - bound
    else:
        exceedance = bound - value
    relative = exceedance / bound
    within = exceedance < 0.0 or math.isclose(
        exceedance, 0.0, rel_tol=0.0, abs_tol=STACK_TOLERANCE * bound
    )
    return {
        "parameter": parameter,
        "qualified": bound,
        "applied": value,
        "exceedance": exceedance,
        "relative_exceedance": relative,
        "within_envelope": within,
    }


def envelope_assessment(qualified_envelope, application_envelope):
    """Compare an application envelope against a qualification envelope."""
    qualified = validate_envelope(qualified_envelope, "qualified_envelope")
    applied = validate_envelope(application_envelope, "application_envelope")
    records = []
    uncovered = []
    for parameter in sorted(applied):
        if parameter not in qualified:
            uncovered.append(parameter)
            continue
        records.append(severity(parameter, qualified[parameter], applied[parameter]))
    return {
        "records": records,
        "uncovered_parameters": uncovered,
        "exceeded_parameters": [
            record["parameter"] for record in records if not record["within_envelope"]
        ],
        "worst_relative_exceedance": max(
            [record["relative_exceedance"] for record in records], default=0.0
        ),
    }


def heritage_verdict(assessment, configuration_identical=True,
                     delta_limit=DEFAULT_DELTA_LIMIT):
    """Return the qualification route a heritage claim leads to."""
    if not isinstance(assessment, dict) or "records" not in assessment:
        raise ValueError("assessment must be the mapping envelope_assessment returns")
    if not isinstance(configuration_identical, bool):
        raise ValueError("configuration_identical must be a boolean")
    limit = _require_positive(delta_limit, "delta_limit")
    if not configuration_identical:
        return HERITAGE_FULL
    if assessment["uncovered_parameters"]:
        return HERITAGE_FULL
    if not assessment["exceeded_parameters"]:
        return HERITAGE_ACCEPTED
    worst = assessment["worst_relative_exceedance"]
    if worst > limit and not math.isclose(
        worst, limit, rel_tol=0.0, abs_tol=STACK_TOLERANCE
    ):
        return HERITAGE_FULL
    return HERITAGE_DELTA


def assess_heritage(part):
    """Assess one heritage claim.

    part keys: id, qualified_envelope, application_envelope; optional
    configuration_identical and delta_limit.
    """
    if not isinstance(part, dict):
        raise ValueError("part must be a mapping")
    for key in ("id", "qualified_envelope", "application_envelope"):
        if key not in part:
            raise ValueError("part missing required key '%s'" % key)
    identifier = _require_text(part["id"], "part id")
    assessment = envelope_assessment(
        part["qualified_envelope"], part["application_envelope"]
    )
    identical = part.get("configuration_identical", True)
    verdict = heritage_verdict(
        assessment, identical, part.get("delta_limit", DEFAULT_DELTA_LIMIT)
    )
    findings = []
    for parameter in assessment["uncovered_parameters"]:
        findings.append(
            "part %s is applied against %s, which its qualification never covered"
            % (identifier, parameter)
        )
    for record in assessment["records"]:
        if not record["within_envelope"]:
            findings.append(
                "part %s exceeds its qualified %s by %.4g (%.1f%% of the bound)"
                % (identifier, record["parameter"], record["exceedance"],
                   100.0 * record["relative_exceedance"])
            )
    if not identical:
        findings.append(
            "part %s is not in the configuration it was qualified in" % identifier
        )
    return {
        "id": identifier,
        "verdict": verdict,
        "records": assessment["records"],
        "uncovered_parameters": assessment["uncovered_parameters"],
        "exceeded_parameters": assessment["exceeded_parameters"],
        "worst_relative_exceedance": assessment["worst_relative_exceedance"],
        "findings": findings,
        "reusable_as_is": verdict == HERITAGE_ACCEPTED,
    }


def validate_feature(feature, label="feature"):
    """Return a validated dimensional feature: nominal with plus and minus limits."""
    if not isinstance(feature, dict):
        raise ValueError("%s must be a mapping" % label)
    for key in ("nominal_mm", "plus_tol_mm", "minus_tol_mm"):
        if key not in feature:
            raise ValueError("%s missing required key '%s'" % (label, key))
    nominal = _require_positive(feature["nominal_mm"], "%s nominal_mm" % label)
    plus = _require_non_negative(feature["plus_tol_mm"], "%s plus_tol_mm" % label)
    minus = _require_non_negative(feature["minus_tol_mm"], "%s minus_tol_mm" % label)
    if minus >= nominal:
        raise ValueError("%s minus tolerance consumes the whole nominal" % label)
    return {"nominal_mm": nominal, "plus_tol_mm": plus, "minus_tol_mm": minus}


def worst_case_clearance(hole, shaft):
    """Return the tightest and loosest clearance of a hole and shaft pair."""
    bore = validate_feature(hole, "hole")
    pin = validate_feature(shaft, "shaft")
    tightest = (bore["nominal_mm"] - bore["minus_tol_mm"]) - (
        pin["nominal_mm"] + pin["plus_tol_mm"]
    )
    loosest = (bore["nominal_mm"] + bore["plus_tol_mm"]) - (
        pin["nominal_mm"] - pin["minus_tol_mm"]
    )
    return {"min_clearance_mm": tightest, "max_clearance_mm": loosest}


def assess_interchangeability(group):
    """Assess whether every replaceable item fits every mating feature.

    group keys: id, items (each with id, shaft, optional selective_fit and
    match_marked), mating_features (each with id and hole), max_clearance_mm.
    """
    if not isinstance(group, dict):
        raise ValueError("group must be a mapping")
    for key in ("id", "items", "mating_features", "max_clearance_mm"):
        if key not in group:
            raise ValueError("group missing required key '%s'" % key)
    identifier = _require_text(group["id"], "group id")
    items = group["items"]
    features = group["mating_features"]
    if not isinstance(items, (list, tuple)) or len(items) < 2:
        raise ValueError("an interchangeable group needs at least two items")
    if not isinstance(features, (list, tuple)) or not features:
        raise ValueError("an interchangeable group needs at least one mating feature")
    ceiling = _require_positive(group["max_clearance_mm"], "max_clearance_mm")

    findings = []
    pairs = []
    item_ids = []
    for item in items:
        if not isinstance(item, dict) or "id" not in item or "shaft" not in item:
            raise ValueError("each item needs an 'id' and a 'shaft' feature")
        item_id = _require_text(item["id"], "item id")
        item_ids.append(item_id)
        for flag in ("selective_fit", "match_marked"):
            value = item.get(flag, False)
            if not isinstance(value, bool):
                raise ValueError("'%s' must be a boolean" % flag)
            if value:
                findings.append(
                    "item %s in group %s relies on %s, so it is not interchangeable"
                    % (item_id, identifier, flag.replace("_", " "))
                )
        for feature in features:
            if not isinstance(feature, dict) or "id" not in feature or "hole" not in feature:
                raise ValueError("each mating feature needs an 'id' and a 'hole' feature")
            feature_id = _require_text(feature["id"], "mating feature id")
            clearance = worst_case_clearance(feature["hole"], item["shaft"])
            interferes = clearance["min_clearance_mm"] < 0.0 and not math.isclose(
                clearance["min_clearance_mm"], 0.0, rel_tol=0.0, abs_tol=STACK_TOLERANCE
            )
            too_loose = clearance["max_clearance_mm"] > ceiling and not math.isclose(
                clearance["max_clearance_mm"], ceiling, rel_tol=0.0, abs_tol=STACK_TOLERANCE
            )
            if interferes:
                findings.append(
                    "item %s in mating feature %s stacks to %.4f mm interference"
                    % (item_id, feature_id, -clearance["min_clearance_mm"])
                )
            if too_loose:
                findings.append(
                    "item %s in mating feature %s stacks to %.4f mm clearance, past "
                    "the %.4f mm the function allows"
                    % (item_id, feature_id, clearance["max_clearance_mm"], ceiling)
                )
            pairs.append({
                "item_id": item_id,
                "feature_id": feature_id,
                "min_clearance_mm": clearance["min_clearance_mm"],
                "max_clearance_mm": clearance["max_clearance_mm"],
                "fits": not interferes and not too_loose,
            })
    if len(set(item_ids)) != len(item_ids):
        raise ValueError("the item list repeats an identifier")
    fitting = sum(1 for pair in pairs if pair["fits"])
    return {
        "group_id": identifier,
        "pairs": pairs,
        "pair_count": len(pairs),
        "fitting_pair_count": fitting,
        "fitting_fraction": fitting / float(len(pairs)),
        "findings": findings,
        "interchangeable": not findings,
    }


def assess_parts_and_interchangeability(spec):
    """Assess a set of heritage claims together with the interchangeable groups.

    spec keys: parts (heritage claims), groups (interchangeable groups); either
    may be an empty sequence but not both.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    parts = spec.get("parts", [])
    groups = spec.get("groups", [])
    if not isinstance(parts, (list, tuple)) or not isinstance(groups, (list, tuple)):
        raise ValueError("'parts' and 'groups' must be sequences")
    if not parts and not groups:
        raise ValueError("supply at least one heritage claim or one group")
    part_records = [assess_heritage(part) for part in parts]
    group_records = [assess_interchangeability(group) for group in groups]
    findings = []
    for record in part_records:
        findings.extend(record["findings"])
    for record in group_records:
        findings.extend(record["findings"])
    reusable = sum(1 for record in part_records if record["reusable_as_is"])
    return {
        "parts": part_records,
        "groups": group_records,
        "reusable_part_count": reusable,
        "part_count": len(part_records),
        "heritage_fraction": (reusable / float(len(part_records))) if part_records else 0.0,
        "findings": findings,
        "compliant": not findings,
    }
