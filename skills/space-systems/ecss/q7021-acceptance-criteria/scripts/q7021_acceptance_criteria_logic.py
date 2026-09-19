"""Acceptance of a flammability screening run against its application-class limits.

Anchor: ECSS-Q-ST-70-21C, acceptance (deciding whether the burn length, the
dripping behaviour and the after-flame of a burned specimen set clear the limits
the application of the material carries). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Resolve the application class and read its burn-length limit, after-flame
   limit, dripping allowance and minimum specimen count. The limits belong to
   where the material will be installed, not to the material.
2. Validate each burned specimen: a burn length that cannot exceed the exposed
   specimen length, a non-negative after-flame time, a drip count, and whether
   any drip ignited the indicator placed under the specimen.
3. Grade each specimen, counting a value sitting exactly on a limit as
   compliant through a named tolerance rather than by moving the limit.
4. Grade the set: one failing specimen fails the set, and a set smaller than the
   class minimum is inconclusive, which is a different answer from a pass.
"""

import math

__all__ = [
    "APPLICATION_CLASSES",
    "LIMIT_TOLERANCE",
    "class_limits",
    "validate_specimen",
    "evaluate_specimen",
    "worst_case_burn_length",
    "evaluate_set",
    "assess_acceptance",
]

# Paraphrased acceptance limits by where the material is installed. The band
# tightens as the surroundings get less forgiving: a vented equipment bay, a
# volume the crew occupies, and an oxygen-enriched volume.
APPLICATION_CLASSES = {
    "vented-equipment-bay": {
        "burn_length_limit_mm": 150.0,
        "after_flame_limit_s": 10.0,
        "flaming_drips_allowed": True,
        "min_specimens": 3,
    },
    "habitable-volume": {
        "burn_length_limit_mm": 100.0,
        "after_flame_limit_s": 5.0,
        "flaming_drips_allowed": False,
        "min_specimens": 5,
    },
    "oxygen-enriched-volume": {
        "burn_length_limit_mm": 60.0,
        "after_flame_limit_s": 2.0,
        "flaming_drips_allowed": False,
        "min_specimens": 5,
    },
}

# A burn length is read off a scale and a limit is a round number; equality at
# the limit is a representation question absorbed here, never by moving the
# limit itself.
LIMIT_TOLERANCE = 1e-9


def _real(value, label, minimum=None):
    """Return value as a finite float, optionally bounded below."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None and number < minimum:
        raise ValueError("%s must be at least %g, got %g" % (label, minimum, number))
    return number


def _at_most(value, bound):
    """True when value stays under bound, counting an on-the-bound value as under."""
    return value < bound or math.isclose(value, bound, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE)


def class_limits(application_class):
    """Return the acceptance limits of one application class."""
    if not isinstance(application_class, str) or not application_class.strip():
        raise ValueError("application_class must be a non-empty string")
    key = application_class.strip()
    if key not in APPLICATION_CLASSES:
        raise ValueError("unknown application class %r; known classes are %s"
                         % (key, ", ".join(sorted(APPLICATION_CLASSES))))
    return dict(APPLICATION_CLASSES[key], name=key)


def validate_specimen(record):
    """Return one normalised burned-specimen record."""
    if not isinstance(record, dict):
        raise ValueError("a specimen record must be a mapping")
    ident = record.get("specimen_id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("specimen_id must be a non-empty string")
    exposed = _real(record.get("specimen_length_mm"),
                    "specimen %s exposed length" % ident, minimum=0.0)
    if exposed <= 0.0:
        raise ValueError("specimen %s exposed length must be positive" % ident)
    burn = _real(record.get("burn_length_mm"), "specimen %s burn length" % ident,
                 minimum=0.0)
    if burn > exposed + LIMIT_TOLERANCE:
        raise ValueError("specimen %s reports a burn length %g mm longer than its "
                         "exposed length %g mm" % (ident, burn, exposed))
    after_flame = _real(record.get("after_flame_s", 0.0),
                        "specimen %s after-flame time" % ident, minimum=0.0)
    drips = record.get("flaming_drips", 0)
    if isinstance(drips, bool) or not isinstance(drips, int):
        raise ValueError("specimen %s flaming drip count must be an integer" % ident)
    if drips < 0:
        raise ValueError("specimen %s flaming drip count must not be negative" % ident)
    ignited = record.get("drip_ignited_indicator", False)
    if not isinstance(ignited, bool):
        raise ValueError("specimen %s drip-ignition flag must be boolean" % ident)
    if ignited and drips == 0:
        raise ValueError("specimen %s reports an ignited indicator with no drip "
                         "to have ignited it" % ident)
    consumed = record.get("fully_consumed", False)
    if not isinstance(consumed, bool):
        raise ValueError("specimen %s consumption flag must be boolean" % ident)
    return {
        "specimen_id": ident.strip(),
        "specimen_length_mm": exposed,
        "burn_length_mm": burn,
        "after_flame_s": after_flame,
        "flaming_drips": drips,
        "drip_ignited_indicator": ignited,
        "fully_consumed": consumed,
    }


def evaluate_specimen(record, limits):
    """Grade one burned specimen against the acceptance limits of its class."""
    specimen = validate_specimen(record)
    if not isinstance(limits, dict):
        raise ValueError("limits must be the mapping returned by class_limits")
    for key in ("burn_length_limit_mm", "after_flame_limit_s", "flaming_drips_allowed"):
        if key not in limits:
            raise ValueError("limits mapping is missing '%s'" % key)
    reasons = []
    burn_limit = _real(limits["burn_length_limit_mm"], "burn-length limit", minimum=0.0)
    if not _at_most(specimen["burn_length_mm"], burn_limit):
        reasons.append("burn length %g mm past the %g mm limit"
                       % (specimen["burn_length_mm"], burn_limit))
    flame_limit = _real(limits["after_flame_limit_s"], "after-flame limit", minimum=0.0)
    if not _at_most(specimen["after_flame_s"], flame_limit):
        reasons.append("after-flame %g s past the %g s limit"
                       % (specimen["after_flame_s"], flame_limit))
    if specimen["fully_consumed"]:
        reasons.append("specimen burned to its full exposed length; it did not "
                       "self-extinguish")
    if specimen["drip_ignited_indicator"]:
        reasons.append("a flaming drip ignited the indicator below the specimen")
    elif specimen["flaming_drips"] > 0 and not limits["flaming_drips_allowed"]:
        reasons.append("%d flaming drip(s) in a class that allows none"
                       % specimen["flaming_drips"])
    specimen["burn_length_margin_mm"] = burn_limit - specimen["burn_length_mm"]
    specimen["status"] = "fail" if reasons else "pass"
    specimen["reasons"] = reasons
    return specimen


def worst_case_burn_length(records):
    """Return the longest burn length across a graded specimen set."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of specimen records")
    worst = None
    for record in records:
        if not isinstance(record, dict) or "burn_length_mm" not in record:
            raise ValueError("each record must carry 'burn_length_mm'")
        value = float(record["burn_length_mm"])
        if worst is None or value > worst:
            worst = value
    return worst


def evaluate_set(records, application_class):
    """Grade a whole specimen set against one application class."""
    limits = class_limits(application_class)
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("a specimen set needs at least one burned specimen")
    graded = [evaluate_specimen(record, limits) for record in records]
    seen = set()
    for specimen in graded:
        if specimen["specimen_id"] in seen:
            raise ValueError("duplicate specimen id %r in the set"
                             % specimen["specimen_id"])
        seen.add(specimen["specimen_id"])
    failing = [s["specimen_id"] for s in graded if s["status"] == "fail"]
    worst = worst_case_burn_length(graded)
    findings = []
    short = len(graded) < limits["min_specimens"]
    if short:
        findings.append("%d specimen(s) burned; class %s needs %d before a verdict "
                        "can be given" % (len(graded), limits["name"],
                                          limits["min_specimens"]))
    if failing:
        status = "fail"
        findings.append("failing specimen(s): %s" % ", ".join(failing))
    elif short:
        status = "inconclusive"
    else:
        status = "pass"
    return {
        "application_class": limits["name"],
        "limits": limits,
        "specimens": graded,
        "failing": failing,
        "worst_case_burn_length_mm": worst,
        "margin_mm": limits["burn_length_limit_mm"] - worst,
        "status": status,
        "findings": findings,
    }


def assess_acceptance(spec):
    """Run the full acceptance assessment for one material.

    spec keys: material, application_class, specimens (list of burned-specimen
    records).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("material", "application_class", "specimens"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    material = spec["material"]
    if not isinstance(material, str) or not material.strip():
        raise ValueError("spec['material'] must be a non-empty string")
    result = evaluate_set(spec["specimens"], spec["application_class"])
    result["material"] = material.strip()
    result["screened_in"] = result["status"] == "pass"
    return result
