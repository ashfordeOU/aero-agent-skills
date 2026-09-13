#!/usr/bin/env python3
"""Grounding/bonding provision verification by inspection plus continuity
measurement -- ECSS-E-ST-20-06C clause 6.8.1 (paraphrased procedure).

Offline, deterministic, stdlib only. The module implements the closure rule
of the clause: a bonding or grounding provision is only verified when the
inspection evidence is complete AND an electrical continuity measurement of
adequate quality lands inside the resistance bounds for that provision
category. Either half alone leaves the provision open.
"""

import math

# Representation tolerance. Bond-resistance budgets are sums/differences of
# small floats, so an exactly-compliant value can land a few ULPs over the
# bound. The tolerance absorbs the representation error only; the engineering
# bounds below are never widened.
REL_TOL = 1e-9
ABS_TOL = 1e-15

# Resistance bounds per provision category, in ohm: (lower, upper).
# Conductive bonds have no lower bound; a static-dissipative bleed path is
# bounded on both sides -- too low is a short, too high stops bleeding charge.
PROVISION_BOUNDS_OHM = {
    "structure-bond": (0.0, 2.5e-3),
    "equipment-chassis-bond": (0.0, 1.0e-2),
    "shield-termination": (0.0, 1.5e-2),
    "static-dissipative-bond": (1.0e4, 1.0e9),
}

# Spelling variants accepted from a verification dossier.
PROVISION_ALIASES = {
    "structure-bond": "structure-bond",
    "structural-bond": "structure-bond",
    "primary-structure-bond": "structure-bond",
    "equipment-chassis-bond": "equipment-chassis-bond",
    "chassis-bond": "equipment-chassis-bond",
    "unit-chassis-bond": "equipment-chassis-bond",
    "shield-termination": "shield-termination",
    "harness-shield-termination": "shield-termination",
    "backshell-termination": "shield-termination",
    "static-dissipative-bond": "static-dissipative-bond",
    "bleed-path-bond": "static-dissipative-bond",
}

# Inspection attributes the clause expects on record before a provision may
# close. conductor-routing only applies to a strap/pigtail provision.
INSPECTION_ATTRIBUTES = (
    "surface_preparation",
    "fastener_installation",
    "corrosion_protection",
    "conductor_routing",
)
ATTRIBUTE_STATES = ("verified", "not-verified", "not-applicable")

# conductor-routing may legitimately be not-applicable on a face-to-face bond.
ROUTING_OPTIONAL = ("structure-bond",)

MEASUREMENT_METHODS = ("four-wire-dc", "two-wire-dc")

# Below this bound a two-wire reading is dominated by lead resistance.
FOUR_WIRE_REQUIRED_ABOVE_OHM = 5.0e-2

# The instrument must resolve the bound to at least one part in ten.
RESOLUTION_FRACTION = 0.1


def _le(value, bound):
    """value <= bound, absorbing float representation error at the bound."""
    return value <= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _ge(value, bound):
    """value >= bound, absorbing float representation error at the bound."""
    return value >= bound or math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def categorize_provision(kind):
    """Map a dossier provision name onto one of the four bonding categories.

    Raises ValueError on a blank, non-string or unrecognized provision kind --
    an uncategorized provision must not silently inherit another category's
    resistance bound.
    """
    if not isinstance(kind, str):
        raise ValueError("provision kind must be a string, got %r" % (kind,))
    key = kind.strip().lower().replace("_", "-")
    if not key:
        raise ValueError("provision kind must not be blank")
    if key not in PROVISION_ALIASES:
        raise ValueError("unrecognized provision kind %r" % (kind,))
    return PROVISION_ALIASES[key]


def resistance_bounds(category):
    """Return (lower_ohm, upper_ohm) for an already-categorized provision."""
    if category not in PROVISION_BOUNDS_OHM:
        raise ValueError("unknown provision category %r" % (category,))
    return PROVISION_BOUNDS_OHM[category]


def evaluate_inspection_record(category, record):
    """Check the visual/dimensional inspection half of clause 6.8.1.

    Returns {"complete": bool, "findings": [str, ...]}. Raises ValueError when
    the record is structurally unusable (not a mapping, missing attribute,
    illegal attribute state, negative nonconformance count).
    """
    category = categorize_provision(category)
    if not isinstance(record, dict):
        raise ValueError("inspection record must be a mapping, got %r" % (type(record).__name__,))
    findings = []
    for attribute in INSPECTION_ATTRIBUTES:
        if attribute not in record:
            raise ValueError("inspection record missing attribute %r" % (attribute,))
        state = record[attribute]
        if state not in ATTRIBUTE_STATES:
            raise ValueError("attribute %r has illegal state %r" % (attribute, state))
        if state == "not-applicable":
            if attribute != "conductor_routing" or category not in ROUTING_OPTIONAL:
                findings.append("%s marked not-applicable but is required for %s" % (attribute, category))
        elif state == "not-verified":
            findings.append("%s not verified by inspection" % attribute)
    open_ncrs = record.get("open_nonconformances", 0)
    if not isinstance(open_ncrs, int) or isinstance(open_ncrs, bool):
        raise ValueError("open_nonconformances must be an int, got %r" % (open_ncrs,))
    if open_ncrs < 0:
        raise ValueError("open_nonconformances must not be negative")
    if open_ncrs > 0:
        findings.append("%d open nonconformance(s) against the provision" % open_ncrs)
    return {"complete": not findings, "findings": findings}


def evaluate_continuity_measurement(category, measured_ohm, resolution_ohm, method):
    """Check the electrical half: method, instrument resolution, and bounds.

    Returns a mapping with the compliance verdict and the findings that block
    it. Raises ValueError on a non-numeric, non-finite or negative reading, a
    non-positive resolution, or an unknown measurement method.
    """
    category = categorize_provision(category)
    lower, upper = resistance_bounds(category)
    for label, value in (("measured_ohm", measured_ohm), ("resolution_ohm", resolution_ohm)):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise ValueError("%s must be numeric, got %r" % (label, value))
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    measured_ohm = float(measured_ohm)
    resolution_ohm = float(resolution_ohm)
    if measured_ohm < 0.0:
        raise ValueError("measured_ohm must not be negative")
    if resolution_ohm <= 0.0:
        raise ValueError("resolution_ohm must be positive")
    if method not in MEASUREMENT_METHODS:
        raise ValueError("unknown measurement method %r" % (method,))
    findings = []
    if upper <= FOUR_WIRE_REQUIRED_ABOVE_OHM and method != "four-wire-dc":
        findings.append("method %s cannot resolve a %.4g ohm bound; four-wire-dc required" % (method, upper))
    if not _le(resolution_ohm, upper * RESOLUTION_FRACTION):
        findings.append("instrument resolution %.4g ohm coarser than one tenth of the %.4g ohm bound" % (resolution_ohm, upper))
    within = _le(measured_ohm, upper) and _ge(measured_ohm, lower)
    if not within:
        findings.append("measured %.6g ohm outside the %.4g..%.4g ohm bounds for %s" % (measured_ohm, lower, upper, category))
    return {
        "category": category,
        "measured_ohm": measured_ohm,
        "lower_ohm": lower,
        "upper_ohm": upper,
        "within_bounds": within,
        "compliant": not findings,
        "findings": findings,
    }


def bond_resistance_margin(category, measured_ohm):
    """Fractional margin to the upper bound: (upper - measured) / upper.

    Negative when the reading exceeds the bound. Raises ValueError through
    categorize_provision on an unknown category.
    """
    _, upper = resistance_bounds(categorize_provision(category))
    if isinstance(measured_ohm, bool) or not isinstance(measured_ohm, (int, float)):
        raise ValueError("measured_ohm must be numeric, got %r" % (measured_ohm,))
    if not math.isfinite(float(measured_ohm)):
        raise ValueError("measured_ohm must be finite")
    if float(measured_ohm) < 0.0:
        raise ValueError("measured_ohm must not be negative")
    return (upper - float(measured_ohm)) / upper


def verify_provision(provision):
    """Close one provision against both halves of clause 6.8.1.

    provision keys: id, kind, inspection (mapping), measurement (mapping with
    measured_ohm, resolution_ohm, method).
    """
    if not isinstance(provision, dict):
        raise ValueError("provision must be a mapping, got %r" % (type(provision).__name__,))
    ident = provision.get("id")
    if not isinstance(ident, str) or not ident.strip():
        raise ValueError("provision needs a non-blank string id")
    category = categorize_provision(provision.get("kind"))
    inspection = evaluate_inspection_record(category, provision.get("inspection"))
    measurement_in = provision.get("measurement")
    if not isinstance(measurement_in, dict):
        raise ValueError("provision %s has no measurement mapping" % ident)
    for key in ("measured_ohm", "resolution_ohm", "method"):
        if key not in measurement_in:
            raise ValueError("measurement for %s missing %r" % (ident, key))
    measurement = evaluate_continuity_measurement(
        category,
        measurement_in["measured_ohm"],
        measurement_in["resolution_ohm"],
        measurement_in["method"],
    )
    findings = ["inspection: " + f for f in inspection["findings"]]
    findings += ["continuity: " + f for f in measurement["findings"]]
    return {
        "id": ident,
        "category": category,
        "inspection_complete": inspection["complete"],
        "continuity_compliant": measurement["compliant"],
        "margin": bond_resistance_margin(category, measurement["measured_ohm"]),
        "status": "verified" if not findings else "open",
        "findings": findings,
    }


def verify_grounding_network(provisions):
    """Roll the per-provision verdicts into a network-level closure statement.

    A network with no structure-bond reference point is reported as open even
    when every individual provision passes -- the reference is what the other
    bonds are measured against.
    """
    if not isinstance(provisions, (list, tuple)) or not provisions:
        raise ValueError("provisions must be a non-empty list")
    results = [verify_provision(p) for p in provisions]
    seen = set()
    for result in results:
        seen.add(result["category"])
    open_ids = [r["id"] for r in results if r["status"] == "open"]
    network_findings = []
    if "structure-bond" not in seen:
        network_findings.append("no structure-bond reference point in the network")
    duplicate_ids = len(results) - len({r["id"] for r in results})
    if duplicate_ids:
        network_findings.append("%d duplicate provision id(s) in the dossier" % duplicate_ids)
    return {
        "provisions": results,
        "verified_count": sum(1 for r in results if r["status"] == "verified"),
        "open_ids": open_ids,
        "categories_present": sorted(seen),
        "network_findings": network_findings,
        "closed": not open_ids and not network_findings,
    }
