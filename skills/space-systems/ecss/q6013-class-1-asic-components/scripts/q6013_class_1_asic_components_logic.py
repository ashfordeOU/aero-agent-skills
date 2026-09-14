"""Assurance routing and heritage reuse grading for class 1 ASICs.

Anchor: ECSS-Q-ST-60-13C clause 4.6.2 (an application-specific integrated
circuit is developed and reused under the dedicated microelectronics assurance
standard, not under the generic commercial-component flow). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Categorise the device. A full-custom, standard-cell, gate-array or
   structured device, and a hard-macro programmed part, are application
   specific and take the microelectronics route. Anything else stays on the
   generic component route and this clause has nothing to say about it.
2. With no heritage record, the device is a new development and every
   development activity is open.
3. With a heritage record, compare it attribute by attribute with the new
   application: foundry, process node, package, operating temperature range
   and qualified total dose. Every difference re-opens the named development
   activity behind that attribute.
4. Apply the dose margin factor to the mission dose before comparing, and
   absorb the representation error at an exact equality rather than relaxing
   the factor.
5. Report the reuse credit -- the share of heritage activities that carry over
   -- and decide whether the reuse claim stands, stands with re-opened
   activities, or collapses into a new development.
"""

import math

__all__ = [
    "ASIC_KINDS",
    "GENERIC_KINDS",
    "HERITAGE_ACTIVITIES",
    "DEFAULT_REUSE_POLICY",
    "DOSE_TOLERANCE",
    "MICROELECTRONICS_STANDARD_ROUTE",
    "GENERIC_COMPONENT_ROUTE",
    "NOT_AN_ASIC",
    "NEW_DEVELOPMENT_REQUIRED",
    "REUSE_WITH_REOPENED_ACTIVITIES",
    "REUSE_ACCEPTED",
    "validate_reuse_policy",
    "route_for_kind",
    "required_dose_krad",
    "dose_margin_ratio",
    "dose_adequate",
    "temperature_envelope_covered",
    "validate_design_record",
    "heritage_deltas",
    "reopened_activities",
    "reuse_credit",
    "assess_asic_route",
]

# Devices whose function is fixed by a design the project owns or specifies.
ASIC_KINDS = (
    "full-custom-asic",
    "standard-cell-asic",
    "gate-array",
    "structured-asic",
    "programmed-hard-macro",
)

# Devices that stay on the generic commercial-component procurement route.
GENERIC_KINDS = (
    "standard-microcircuit",
    "discrete-semiconductor",
    "hybrid-microcircuit",
    "passive-component",
)

MICROELECTRONICS_STANDARD_ROUTE = "microelectronics-assurance-standard"
GENERIC_COMPONENT_ROUTE = "generic-component-route"

NOT_AN_ASIC = "not-an-asic"
NEW_DEVELOPMENT_REQUIRED = "new-development-required"
REUSE_WITH_REOPENED_ACTIVITIES = "reuse-with-reopened-activities"
REUSE_ACCEPTED = "reuse-accepted"

# The development activities a heritage record can carry over, in the order
# they are reported. Each attribute below re-opens exactly one of them.
HERITAGE_ACTIVITIES = (
    "process-qualification",
    "timing-characterization",
    "package-qualification",
    "design-verification",
    "electrical-characterization",
    "radiation-verification",
)

# A dose comparison is a ratio of two declared numbers. An exact equality can
# land a few units in the last place on the wrong side; absorb that here
# instead of softening the margin factor.
DOSE_TOLERANCE = 1e-9

DEFAULT_REUSE_POLICY = {
    # Factor applied to the mission dose before the heritage dose is compared.
    "dose_margin_factor": 2.0,
    # Above this many re-opened activities the reuse claim is not a reuse.
    "max_reopened_activities_for_reuse": 2,
    # Slack admitted on a temperature envelope, in kelvin-equivalent degrees.
    "temperature_tolerance_c": 0.0,
}

_ATTRIBUTE_ACTIVITY = (
    ("foundry", "process-qualification"),
    ("process_node_nm", "timing-characterization"),
    ("package", "package-qualification"),
    ("design_revision", "design-verification"),
)


def validate_reuse_policy(policy=None):
    """Return a complete reuse policy, defaults filled in."""
    if policy is None:
        return dict(DEFAULT_REUSE_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("reuse policy must be a mapping")
    merged = dict(DEFAULT_REUSE_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_REUSE_POLICY:
            raise ValueError("unknown reuse policy key %r" % (key,))
        merged[key] = value
    factor = merged["dose_margin_factor"]
    if not isinstance(factor, (int, float)) or isinstance(factor, bool):
        raise ValueError("dose_margin_factor must be a real number")
    if not math.isfinite(float(factor)) or float(factor) < 1.0:
        raise ValueError("dose_margin_factor must be finite and at least 1.0")
    merged["dose_margin_factor"] = float(factor)
    cap = merged["max_reopened_activities_for_reuse"]
    if not isinstance(cap, int) or isinstance(cap, bool) or cap < 0:
        raise ValueError("max_reopened_activities_for_reuse must be a non-negative integer")
    tolerance = merged["temperature_tolerance_c"]
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ValueError("temperature_tolerance_c must be a real number")
    if not math.isfinite(float(tolerance)) or float(tolerance) < 0.0:
        raise ValueError("temperature_tolerance_c must be finite and non-negative")
    merged["temperature_tolerance_c"] = float(tolerance)
    return merged


def route_for_kind(kind):
    """Return the assurance route a declared device kind falls on."""
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("device kind must be a non-empty string")
    name = kind.strip().lower()
    if name in ASIC_KINDS:
        return MICROELECTRONICS_STANDARD_ROUTE
    if name in GENERIC_KINDS:
        return GENERIC_COMPONENT_ROUTE
    raise ValueError(
        "unknown device kind %r; declare one of %s"
        % (kind, ", ".join(ASIC_KINDS + GENERIC_KINDS))
    )


def required_dose_krad(mission_dose_krad, margin_factor):
    """Return the dose a heritage qualification has to cover."""
    for label, value in (("mission_dose_krad", mission_dose_krad),
                         ("margin_factor", margin_factor)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return float(mission_dose_krad) * float(margin_factor)


def dose_margin_ratio(heritage_dose_krad, mission_dose_krad):
    """Return how many times the mission dose the heritage qualification covers."""
    for label, value in (("heritage_dose_krad", heritage_dose_krad),
                         ("mission_dose_krad", mission_dose_krad)):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)) or float(value) <= 0.0:
            raise ValueError("%s must be positive and finite, got %r" % (label, value))
    return float(heritage_dose_krad) / float(mission_dose_krad)


def dose_adequate(heritage_dose_krad, mission_dose_krad, margin_factor):
    """Return whether the heritage dose reaches the mission dose times the factor."""
    needed = required_dose_krad(mission_dose_krad, margin_factor)
    have = float(heritage_dose_krad)
    if not math.isfinite(have) or have <= 0.0:
        raise ValueError("heritage_dose_krad must be positive and finite")
    return have > needed or math.isclose(have, needed, rel_tol=DOSE_TOLERANCE, abs_tol=0.0)


def _validate_range(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError("%s must be a (low, high) pair" % label)
    low, high = value
    for part in (low, high):
        if not isinstance(part, (int, float)) or isinstance(part, bool):
            raise ValueError("%s bounds must be real numbers" % label)
        if not math.isfinite(float(part)):
            raise ValueError("%s bounds must be finite" % label)
    low = float(low)
    high = float(high)
    if low > high:
        raise ValueError("%s is inverted: %g above %g" % (label, low, high))
    return (low, high)


def temperature_envelope_covered(heritage_range, application_range, tolerance=0.0):
    """Return whether a heritage temperature envelope encloses the application one."""
    h_low, h_high = _validate_range(heritage_range, "heritage temperature range")
    a_low, a_high = _validate_range(application_range, "application temperature range")
    if not isinstance(tolerance, (int, float)) or isinstance(tolerance, bool):
        raise ValueError("tolerance must be a real number")
    slack = float(tolerance)
    if not math.isfinite(slack) or slack < 0.0:
        raise ValueError("tolerance must be finite and non-negative")
    low_ok = h_low < a_low + slack or math.isclose(
        h_low, a_low + slack, rel_tol=0.0, abs_tol=DOSE_TOLERANCE
    )
    high_ok = h_high > a_high - slack or math.isclose(
        h_high, a_high - slack, rel_tol=0.0, abs_tol=DOSE_TOLERANCE
    )
    return low_ok and high_ok


def validate_design_record(record, label):
    """Return a normalised heritage or application design record."""
    if not isinstance(record, dict):
        raise ValueError("%s must be a mapping" % label)
    normalised = {}
    for field in ("foundry", "package", "design_revision"):
        value = record.get(field)
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s needs a non-empty '%s'" % (label, field))
        normalised[field] = value.strip()
    node = record.get("process_node_nm")
    if not isinstance(node, (int, float)) or isinstance(node, bool):
        raise ValueError("%s needs a numeric 'process_node_nm'" % label)
    if not math.isfinite(float(node)) or float(node) <= 0.0:
        raise ValueError("%s process_node_nm must be positive and finite" % label)
    normalised["process_node_nm"] = float(node)
    normalised["temperature_range_c"] = _validate_range(
        record.get("temperature_range_c"), "%s temperature_range_c" % label
    )
    dose = record.get("total_dose_krad")
    if not isinstance(dose, (int, float)) or isinstance(dose, bool):
        raise ValueError("%s needs a numeric 'total_dose_krad'" % label)
    if not math.isfinite(float(dose)) or float(dose) <= 0.0:
        raise ValueError("%s total_dose_krad must be positive and finite" % label)
    normalised["total_dose_krad"] = float(dose)
    return normalised


def heritage_deltas(heritage, application, policy=None):
    """Return the ordered differences between a heritage record and the application."""
    settings = validate_reuse_policy(policy)
    left = validate_design_record(heritage, "heritage record")
    right = validate_design_record(application, "application record")
    deltas = []
    for attribute, activity in _ATTRIBUTE_ACTIVITY:
        before = left[attribute]
        after = right[attribute]
        if isinstance(before, float):
            same = math.isclose(before, after, rel_tol=DOSE_TOLERANCE, abs_tol=0.0)
        else:
            same = before == after
        if not same:
            deltas.append({
                "attribute": attribute,
                "heritage": before,
                "application": after,
                "activity": activity,
            })
    if not temperature_envelope_covered(
        left["temperature_range_c"],
        right["temperature_range_c"],
        settings["temperature_tolerance_c"],
    ):
        deltas.append({
            "attribute": "temperature_range_c",
            "heritage": left["temperature_range_c"],
            "application": right["temperature_range_c"],
            "activity": "electrical-characterization",
        })
    if not dose_adequate(
        left["total_dose_krad"],
        right["total_dose_krad"],
        settings["dose_margin_factor"],
    ):
        deltas.append({
            "attribute": "total_dose_krad",
            "heritage": left["total_dose_krad"],
            "application": right["total_dose_krad"],
            "activity": "radiation-verification",
        })
    return deltas


def reopened_activities(deltas):
    """Return the development activities the deltas re-open, in report order."""
    if not isinstance(deltas, (list, tuple)):
        raise ValueError("deltas must be a sequence")
    opened = set()
    for delta in deltas:
        if not isinstance(delta, dict) or "activity" not in delta:
            raise ValueError("each delta must be a mapping carrying 'activity'")
        opened.add(delta["activity"])
    return tuple(name for name in HERITAGE_ACTIVITIES if name in opened)


def reuse_credit(reopened_count, total=len(HERITAGE_ACTIVITIES)):
    """Return the share of heritage activities that carry over unchanged."""
    for label, value in (("reopened_count", reopened_count), ("total", total)):
        if not isinstance(value, int) or isinstance(value, bool):
            raise ValueError("%s must be an integer" % label)
    if total <= 0:
        raise ValueError("total must be positive")
    if reopened_count < 0 or reopened_count > total:
        raise ValueError("reopened_count must lie in 0..%d, got %d" % (total, reopened_count))
    return float(total - reopened_count) / float(total)


def assess_asic_route(case):
    """Run the clause 4.6.2 routing and reuse assessment.

    case keys: kind, optional heritage (design record), application (design
    record, required for an application-specific kind), optional policy.
    """
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping")
    if "kind" not in case:
        raise ValueError("case missing required key 'kind'")
    settings = validate_reuse_policy(case.get("policy"))
    route = route_for_kind(case["kind"])
    if route == GENERIC_COMPONENT_ROUTE:
        return {
            "route": route,
            "verdict": NOT_AN_ASIC,
            "deltas": [],
            "reopened_activities": (),
            "reuse_credit": 0.0,
            "findings": [
                "device kind %r is not application specific; clause 4.6.2 does not "
                "move it off the generic component route" % (case["kind"],)
            ],
        }

    if "application" not in case:
        raise ValueError("an application-specific device needs an 'application' record")
    application = validate_design_record(case["application"], "application record")

    heritage = case.get("heritage")
    if heritage is None:
        return {
            "route": route,
            "verdict": NEW_DEVELOPMENT_REQUIRED,
            "deltas": [],
            "reopened_activities": tuple(HERITAGE_ACTIVITIES),
            "reuse_credit": 0.0,
            "dose_margin_ratio": None,
            "findings": [
                "no heritage record was offered; every development activity of the "
                "microelectronics assurance route is open"
            ],
        }

    deltas = heritage_deltas(heritage, application, settings)
    opened = reopened_activities(deltas)
    credit = reuse_credit(len(opened))
    ratio = dose_margin_ratio(
        validate_design_record(heritage, "heritage record")["total_dose_krad"],
        application["total_dose_krad"],
    )

    findings = []
    for delta in deltas:
        findings.append(
            "%s differs from the heritage design and re-opens %s"
            % (delta["attribute"], delta["activity"])
        )
    if len(opened) == 0:
        verdict = REUSE_ACCEPTED
    elif len(opened) <= settings["max_reopened_activities_for_reuse"]:
        verdict = REUSE_WITH_REOPENED_ACTIVITIES
    else:
        verdict = NEW_DEVELOPMENT_REQUIRED
        findings.append(
            "%d activities re-open against a reuse allowance of %d; the claim is a "
            "new development" % (len(opened), settings["max_reopened_activities_for_reuse"])
        )

    return {
        "route": route,
        "verdict": verdict,
        "deltas": deltas,
        "reopened_activities": opened,
        "reuse_credit": credit,
        "dose_margin_ratio": ratio,
        "required_dose_krad": required_dose_krad(
            application["total_dose_krad"], settings["dose_margin_factor"]
        ),
        "findings": findings,
    }
