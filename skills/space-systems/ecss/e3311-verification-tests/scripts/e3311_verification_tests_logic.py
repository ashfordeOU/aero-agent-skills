"""Verification-test programme for explosive hardware.

Anchor: ECSS-E-ST-33-11C Rev.1 clause 4.14.3 (verification tests for explosive
subsystems and devices). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Build the owed test matrix for the item and report the categories the
   declared programme never covers.
2. Grade a no-fire test: the specified no-fire current has to be held for the
   full dwell and the unit must not function, and the unit must not go on to
   fly.
3. Grade a firing demonstration: the unit must function while driven at or
   below the specified all-fire current, because a demonstration made by
   over-driving proves nothing about the stated level.
4. Grade an electrostatic-discharge exposure: both the pin-to-pin and the
   pin-to-case path at or above the specified threshold, with neither
   functioning nor degradation afterwards.
5. Grade an environmental test level against the mission environment raised by
   the qualification factor.
6. Track the disposition of every unit the programme exposed, so an exposed
   unit is never returned to flight stock.
"""

import math

__all__ = [
    "LEVEL_TOLERANCE",
    "REQUIRED_CATEGORIES",
    "normalize_category",
    "validate_positive",
    "at_least",
    "at_most",
    "qualification_level",
    "no_fire_verdict",
    "firing_demonstration_verdict",
    "esd_verdict",
    "environmental_verdict",
    "category_coverage",
    "unit_disposition",
    "assess_verification_programme",
]

# Levels are compared after a multiplication, so an exactly-on-limit case can
# land a few ULP on the wrong side. Absorb the representation error here rather
# than relaxing the engineering level.
LEVEL_TOLERANCE = 1e-9

# The four test categories an explosive device owes before it is verified.
REQUIRED_CATEGORIES = ("functional", "environmental", "esd", "no-fire")

_CATEGORY_ALIASES = {
    "functional": "functional",
    "firing": "functional",
    "firing-demonstration": "functional",
    "environmental": "environmental",
    "environment": "environmental",
    "esd": "esd",
    "electrostatic-discharge": "esd",
    "no-fire": "no-fire",
    "nofire": "no-fire",
    "no_fire": "no-fire",
}


def normalize_category(name):
    """Return the canonical test-category name for a declared test."""
    if not isinstance(name, str):
        raise ValueError("test category must be a string, got %r" % (name,))
    key = name.strip().lower().replace(" ", "-")
    if key not in _CATEGORY_ALIASES:
        raise ValueError(
            "unknown test category %r; known categories are %s"
            % (name, ", ".join(sorted(set(_CATEGORY_ALIASES.values()))))
        )
    return _CATEGORY_ALIASES[key]


def validate_positive(label, value):
    """Return value as a strictly positive finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def _validate_flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be a boolean, got %r" % (label, value))
    return value


def at_least(value, bound):
    """True when value reaches bound, tolerating representation error."""
    return value > bound or math.isclose(
        value, bound, rel_tol=LEVEL_TOLERANCE, abs_tol=LEVEL_TOLERANCE
    )


def at_most(value, bound):
    """True when value stays at or under bound, tolerating representation error."""
    return value < bound or math.isclose(
        value, bound, rel_tol=LEVEL_TOLERANCE, abs_tol=LEVEL_TOLERANCE
    )


def qualification_level(mission_level, qualification_factor):
    """Return the level a qualification test has to reach for a mission level."""
    mission = validate_positive("mission_level", mission_level)
    factor = validate_positive("qualification_factor", qualification_factor)
    if factor < 1.0:
        raise ValueError(
            "qualification_factor must not reduce the mission level, got %r"
            % (qualification_factor,)
        )
    return mission * factor


def no_fire_verdict(no_fire_current_a, applied_current_a, required_dwell_s,
                    applied_dwell_s, functioned):
    """Grade one no-fire test of an initiator or cartridge."""
    specified = validate_positive("no_fire_current_a", no_fire_current_a)
    applied = validate_positive("applied_current_a", applied_current_a)
    required_dwell = validate_positive("required_dwell_s", required_dwell_s)
    applied_dwell = validate_positive("applied_dwell_s", applied_dwell_s)
    fired = _validate_flag("functioned", functioned)
    findings = []
    if not at_least(applied, specified):
        findings.append(
            "no-fire current applied %.6g A is below the specified %.6g A"
            % (applied, specified)
        )
    if not at_least(applied_dwell, required_dwell):
        findings.append(
            "no-fire dwell %.6g s is shorter than the required %.6g s"
            % (applied_dwell, required_dwell)
        )
    if fired:
        findings.append("unit functioned during the no-fire exposure")
    return {
        "category": "no-fire",
        "specified_current_a": specified,
        "applied_current_a": applied,
        "required_dwell_s": required_dwell,
        "applied_dwell_s": applied_dwell,
        "functioned": fired,
        "passed": not findings,
        "findings": findings,
    }


def firing_demonstration_verdict(all_fire_current_a, applied_current_a, functioned,
                                 measured_output, required_output):
    """Grade one firing demonstration against the specified all-fire current."""
    specified = validate_positive("all_fire_current_a", all_fire_current_a)
    applied = validate_positive("applied_current_a", applied_current_a)
    fired = _validate_flag("functioned", functioned)
    measured = validate_positive("measured_output", measured_output)
    required = validate_positive("required_output", required_output)
    findings = []
    if not at_most(applied, specified):
        findings.append(
            "firing current %.6g A exceeds the specified all-fire %.6g A, so the "
            "stated level is not demonstrated" % (applied, specified)
        )
    if not fired:
        findings.append("unit did not function at the all-fire current")
    if not at_least(measured, required):
        findings.append(
            "delivered output %.6g is below the required %.6g" % (measured, required)
        )
    return {
        "category": "functional",
        "specified_current_a": specified,
        "applied_current_a": applied,
        "functioned": fired,
        "measured_output": measured,
        "required_output": required,
        "passed": not findings,
        "findings": findings,
    }


def esd_verdict(threshold_v, applied_v, paths, functioned, degraded):
    """Grade one electrostatic-discharge exposure of an initiator."""
    specified = validate_positive("threshold_v", threshold_v)
    applied = validate_positive("applied_v", applied_v)
    fired = _validate_flag("functioned", functioned)
    hurt = _validate_flag("degraded", degraded)
    if not isinstance(paths, (list, tuple, set, frozenset)):
        raise ValueError("paths must be a sequence of discharge-path names")
    seen = set()
    for item in paths:
        if not isinstance(item, str):
            raise ValueError("discharge path must be a string, got %r" % (item,))
        key = item.strip().lower().replace(" ", "-").replace("_", "-")
        if key not in ("pin-to-pin", "pin-to-case"):
            raise ValueError("unknown discharge path %r" % (item,))
        seen.add(key)
    findings = []
    missing = sorted({"pin-to-pin", "pin-to-case"} - seen)
    if missing:
        findings.append("discharge path not exercised: %s" % ", ".join(missing))
    if not at_least(applied, specified):
        findings.append(
            "discharge applied %.6g V is below the specified %.6g V" % (applied, specified)
        )
    if fired:
        findings.append("unit functioned during the discharge exposure")
    if hurt:
        findings.append("unit degraded after the discharge exposure")
    return {
        "category": "esd",
        "threshold_v": specified,
        "applied_v": applied,
        "paths": sorted(seen),
        "passed": not findings,
        "findings": findings,
    }


def environmental_verdict(mission_level, test_level, qualification_factor,
                          functioned_after):
    """Grade one environmental test level against the qualification requirement."""
    required = qualification_level(mission_level, qualification_factor)
    applied = validate_positive("test_level", test_level)
    works = _validate_flag("functioned_after", functioned_after)
    findings = []
    if not at_least(applied, required):
        findings.append(
            "environmental level %.6g is below the required qualification level %.6g"
            % (applied, required)
        )
    if not works:
        findings.append("unit did not function after the environmental exposure")
    return {
        "category": "environmental",
        "mission_level": float(mission_level),
        "required_level": required,
        "test_level": applied,
        "passed": not findings,
        "findings": findings,
    }


def category_coverage(declared_categories):
    """Return the covered and missing verification-test categories."""
    if not isinstance(declared_categories, (list, tuple, set, frozenset)):
        raise ValueError("declared_categories must be a sequence")
    covered = set()
    for item in declared_categories:
        covered.add(normalize_category(item))
    missing = [name for name in REQUIRED_CATEGORIES if name not in covered]
    return {
        "covered": sorted(covered),
        "missing": missing,
        "complete": not missing,
    }


def unit_disposition(unit_id, exposed_categories, returned_to_flight):
    """Decide whether a test-exposed unit may go back into flight stock."""
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("unit_id must be a non-empty string")
    if not isinstance(exposed_categories, (list, tuple, set, frozenset)):
        raise ValueError("exposed_categories must be a sequence")
    returned = _validate_flag("returned_to_flight", returned_to_flight)
    exposed = sorted({normalize_category(item) for item in exposed_categories})
    findings = []
    if exposed and returned:
        findings.append(
            "unit %s was exposed to %s and is still carried as flight stock"
            % (unit_id.strip(), ", ".join(exposed))
        )
    return {
        "unit_id": unit_id.strip(),
        "exposed": exposed,
        "returned_to_flight": returned,
        "acceptable": not findings,
        "findings": findings,
    }


def assess_verification_programme(spec):
    """Run the full clause 4.14.3 verification-test assessment.

    spec keys: no_fire, firing, esd, environmental (each a mapping of the
    arguments of the matching verdict function), optional units (a sequence of
    mappings for unit_disposition).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("no_fire", "firing", "esd", "environmental"):
        if key not in spec:
            raise ValueError("spec missing required test block '%s'" % key)
        if not isinstance(spec[key], dict):
            raise ValueError("spec['%s'] must be a mapping" % key)
    verdicts = [
        no_fire_verdict(**spec["no_fire"]),
        firing_demonstration_verdict(**spec["firing"]),
        esd_verdict(**spec["esd"]),
        environmental_verdict(**spec["environmental"]),
    ]
    coverage = category_coverage([v["category"] for v in verdicts])
    dispositions = []
    units = spec.get("units") or []
    if not isinstance(units, (list, tuple)):
        raise ValueError("spec['units'] must be a sequence of mappings")
    for entry in units:
        if not isinstance(entry, dict):
            raise ValueError("each unit entry must be a mapping")
        dispositions.append(unit_disposition(**entry))
    findings = []
    for verdict in verdicts:
        findings.extend(verdict["findings"])
    for item in dispositions:
        findings.extend(item["findings"])
    if not coverage["complete"]:
        findings.append(
            "verification programme never covers: %s" % ", ".join(coverage["missing"])
        )
    return {
        "verdicts": verdicts,
        "coverage": coverage,
        "dispositions": dispositions,
        "compliant": not findings,
        "findings": findings,
    }
