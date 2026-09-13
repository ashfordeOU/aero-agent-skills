"""Individual shielding of externally mounted units and cable runs.

Anchor: ECSS-E-ST-20-07C clause 4.2.12.2 (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. Categorize every hardware item in the electromagnetic-effects
   inventory by its mounting location and kind: an item outside the
   main-structure envelope is either an external-unit or an
   external-cable-run and is in scope; an item inside the envelope is
   out of scope because the primary structure already acts as its
   enclosure.
2. Derive the attenuation each in-scope item needs from the local
   field strength and the item's own field-susceptibility threshold.
3. Derive the attenuation the declared individual shield actually
   provides at the assessment frequency, starting from the shield's
   measured attenuation-versus-frequency points and derating for
   braid optical coverage and for the shield-termination technique.
4. Compare provided against required and record the margin.
5. Verify the shield is individual: a shield identifier shared by two
   or more in-scope items is a finding, because the clause calls for
   each externally mounted item to carry its own shield.

Stdlib only, offline, deterministic.
"""

import math

LOCATION_EXTERNAL = "outside-main-structure"
LOCATION_INTERNAL = "inside-main-structure"
VALID_LOCATIONS = (LOCATION_EXTERNAL, LOCATION_INTERNAL)

KIND_UNIT = "unit"
KIND_CABLE_RUN = "cable-run"
VALID_KINDS = (KIND_UNIT, KIND_CABLE_RUN)

CATEGORY_EXTERNAL_UNIT = "external-unit"
CATEGORY_EXTERNAL_CABLE_RUN = "external-cable-run"
CATEGORY_OUT_OF_SCOPE = "internal-out-of-scope"

# Termination derates, in dB, applied to the measured attenuation of a
# shield. A circumferential (360-degree backshell) termination keeps the
# measured performance; a pigtail adds a wire inductance in the return
# path and costs a large fixed penalty; an unterminated shield is an
# open-ended conductor and is credited with nothing.
TERMINATION_DERATE_DB = {
    "circumferential": 0.0,
    "partial-backshell": 10.0,
    "pigtail": 20.0,
    "unterminated": None,
}

# Optical coverage of a braid below this reference value leaks through
# the braid apertures; the house derate is linear in the coverage gap.
COVERAGE_REFERENCE_PERCENT = 95.0
COVERAGE_DERATE_DB_PER_PERCENT = 0.5

# A margin is a difference of two decibel figures, so an exactly
# satisfied requirement can land a few ULPs below zero. The tolerance
# absorbs that representation error without relaxing the requirement.
MARGIN_TOLERANCE_DB = 1e-9


def categorize_item(item):
    """Return the scope category of one inventory item.

    Raises ValueError for a malformed item, an unknown mounting
    location or an unknown item kind.
    """
    if not isinstance(item, dict):
        raise ValueError("inventory item must be a mapping")
    item_id = item.get("id")
    if not isinstance(item_id, str) or not item_id.strip():
        raise ValueError("inventory item needs a non-empty string id")
    location = item.get("location")
    if location not in VALID_LOCATIONS:
        raise ValueError(
            "item %s has unknown location %r (expected one of %s)"
            % (item_id, location, ", ".join(VALID_LOCATIONS))
        )
    kind = item.get("kind")
    if kind not in VALID_KINDS:
        raise ValueError(
            "item %s has unknown kind %r (expected one of %s)"
            % (item_id, kind, ", ".join(VALID_KINDS))
        )
    if location == LOCATION_INTERNAL:
        return CATEGORY_OUT_OF_SCOPE
    if kind == KIND_UNIT:
        return CATEGORY_EXTERNAL_UNIT
    return CATEGORY_EXTERNAL_CABLE_RUN


def interpolate_attenuation_db(points, frequency_hz):
    """Attenuation of a shield at one frequency, in dB.

    ``points`` is a sequence of (frequency_hz, attenuation_db) pairs.
    Interpolation is linear in log10 of frequency, which is how a
    measured shield curve is normally read off. Outside the measured
    span the nearest endpoint is held, never extrapolated.
    """
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("shield attenuation curve needs at least one point")
    if not isinstance(frequency_hz, (int, float)) or isinstance(frequency_hz, bool):
        raise ValueError("frequency_hz must be numeric")
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive, got %r" % (frequency_hz,))
    cleaned = []
    seen = set()
    for point in points:
        if not isinstance(point, (list, tuple)) or len(point) != 2:
            raise ValueError("attenuation point must be a (frequency_hz, db) pair")
        freq, att = point
        if not isinstance(freq, (int, float)) or isinstance(freq, bool):
            raise ValueError("attenuation point frequency must be numeric")
        if not isinstance(att, (int, float)) or isinstance(att, bool):
            raise ValueError("attenuation point value must be numeric")
        if freq <= 0:
            raise ValueError("attenuation point frequency must be positive")
        if att < 0:
            raise ValueError("attenuation point value must not be negative")
        if freq in seen:
            raise ValueError("duplicate attenuation point frequency %r" % (freq,))
        seen.add(freq)
        cleaned.append((float(freq), float(att)))
    cleaned.sort()
    if len(cleaned) == 1:
        return cleaned[0][1]
    if frequency_hz <= cleaned[0][0]:
        return cleaned[0][1]
    if frequency_hz >= cleaned[-1][0]:
        return cleaned[-1][1]
    for (f_lo, a_lo), (f_hi, a_hi) in zip(cleaned, cleaned[1:]):
        if f_lo <= frequency_hz <= f_hi:
            span = math.log10(f_hi) - math.log10(f_lo)
            frac = (math.log10(frequency_hz) - math.log10(f_lo)) / span
            return a_lo + frac * (a_hi - a_lo)
    raise ValueError("frequency %r fell outside the curve bracket" % (frequency_hz,))


def coverage_derate_db(coverage_percent):
    """Derate a braid shield for optical coverage below the reference."""
    if not isinstance(coverage_percent, (int, float)) or isinstance(coverage_percent, bool):
        raise ValueError("coverage_percent must be numeric")
    if not 0 < coverage_percent <= 100:
        raise ValueError(
            "coverage_percent must be in (0, 100], got %r" % (coverage_percent,)
        )
    if coverage_percent >= COVERAGE_REFERENCE_PERCENT:
        return 0.0
    gap = COVERAGE_REFERENCE_PERCENT - coverage_percent
    return gap * COVERAGE_DERATE_DB_PER_PERCENT


def termination_derate_db(termination):
    """Derate for the shield-termination technique.

    Returns None for an unterminated shield, meaning no attenuation may
    be credited at all.
    """
    if termination not in TERMINATION_DERATE_DB:
        raise ValueError(
            "unknown shield termination %r (expected one of %s)"
            % (termination, ", ".join(sorted(TERMINATION_DERATE_DB)))
        )
    return TERMINATION_DERATE_DB[termination]


def effective_attenuation_db(shield, frequency_hz):
    """Attenuation actually creditable to one individual shield, in dB."""
    if not isinstance(shield, dict):
        raise ValueError("shield must be a mapping")
    shield_id = shield.get("id")
    if not isinstance(shield_id, str) or not shield_id.strip():
        raise ValueError("shield needs a non-empty string id")
    base = interpolate_attenuation_db(shield.get("attenuation_points"), frequency_hz)
    term = termination_derate_db(shield.get("termination"))
    if term is None:
        return 0.0
    derate = term + coverage_derate_db(shield.get("braid_coverage_percent"))
    return max(0.0, base - derate)


def required_attenuation_db(incident_field_v_per_m, susceptibility_threshold_v_per_m):
    """Attenuation an item needs so the field it sees stays under its threshold."""
    for label, value in (
        ("incident_field_v_per_m", incident_field_v_per_m),
        ("susceptibility_threshold_v_per_m", susceptibility_threshold_v_per_m),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be numeric" % label)
        if value <= 0:
            raise ValueError("%s must be positive, got %r" % (label, value))
    ratio = float(incident_field_v_per_m) / float(susceptibility_threshold_v_per_m)
    return max(0.0, 20.0 * math.log10(ratio))


def validate_environment(environment):
    """Validate the assessment environment and return a normalized copy."""
    if not isinstance(environment, dict):
        raise ValueError("environment must be a mapping")
    freq = environment.get("frequency_hz")
    field = environment.get("incident_field_v_per_m")
    for label, value in (
        ("frequency_hz", freq),
        ("incident_field_v_per_m", field),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("environment %s must be numeric" % label)
        if value <= 0:
            raise ValueError("environment %s must be positive, got %r" % (label, value))
    return {"frequency_hz": float(freq), "incident_field_v_per_m": float(field)}


def evaluate_item(item, environment):
    """Evaluate the individual-shield adequacy of one inventory item."""
    env = validate_environment(environment)
    category = categorize_item(item)
    result = {
        "id": item["id"],
        "category": category,
        "in_scope": category != CATEGORY_OUT_OF_SCOPE,
        "findings": [],
        "required_attenuation_db": None,
        "provided_attenuation_db": None,
        "margin_db": None,
        "compliant": True,
    }
    if not result["in_scope"]:
        return result
    threshold = item.get("susceptibility_threshold_v_per_m")
    required = required_attenuation_db(env["incident_field_v_per_m"], threshold)
    result["required_attenuation_db"] = required
    shield = item.get("shield")
    if shield is None:
        result["findings"].append("no-individual-shield-declared")
        result["compliant"] = False
        return result
    provided = effective_attenuation_db(shield, env["frequency_hz"])
    result["provided_attenuation_db"] = provided
    result["shield_id"] = shield["id"]
    margin = provided - required
    result["margin_db"] = margin
    if margin < -MARGIN_TOLERANCE_DB:
        result["findings"].append("attenuation-shortfall")
        result["compliant"] = False
    return result


def check_shield_individuality(results):
    """Flag any shield identifier credited to more than one in-scope item."""
    owners = {}
    for res in results:
        if not res["in_scope"]:
            continue
        shield_id = res.get("shield_id")
        if shield_id is None:
            continue
        owners.setdefault(shield_id, []).append(res["id"])
    shared = {sid: ids for sid, ids in owners.items() if len(ids) > 1}
    for res in results:
        shield_id = res.get("shield_id")
        if shield_id in shared:
            res["findings"].append("shield-shared-with-another-external-item")
            res["compliant"] = False
    return shared


def assess_external_shielding(inventory, environment):
    """Run the full clause 4.2.12.2 assessment over an inventory."""
    if not isinstance(inventory, list) or not inventory:
        raise ValueError("inventory must be a non-empty list of items")
    env = validate_environment(environment)
    seen_ids = set()
    results = []
    for item in inventory:
        res = evaluate_item(item, env)
        if res["id"] in seen_ids:
            raise ValueError("duplicate inventory item id %r" % (res["id"],))
        seen_ids.add(res["id"])
        results.append(res)
    shared = check_shield_individuality(results)
    in_scope = [r for r in results if r["in_scope"]]
    non_compliant = [r["id"] for r in in_scope if not r["compliant"]]
    return {
        "environment": env,
        "items": results,
        "in_scope_count": len(in_scope),
        "out_of_scope_count": len(results) - len(in_scope),
        "shared_shields": shared,
        "non_compliant_ids": non_compliant,
        "compliant": not non_compliant,
    }
