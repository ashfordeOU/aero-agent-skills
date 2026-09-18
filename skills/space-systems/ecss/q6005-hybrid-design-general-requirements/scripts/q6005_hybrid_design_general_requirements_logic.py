"""General design requirements for a hybrid microcircuit before manufacture.

Anchor: ECSS-Q-ST-60-05 clause 7.1 (the overall expectations placed on the
design of a hybrid microcircuit before it enters manufacture). Paraphrased
into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the design-evidence record: the mandated pieces of design
   evidence are either present and current, or the design is not yet a
   release candidate.
2. Take every declared element's applied-to-rated stress ratio against the
   derating limit of its family, so a part sitting above its family limit is
   named rather than averaged away.
3. Build the junction temperature of the dissipating element from the base
   temperature and the stacked thermal resistances of die attach, substrate
   and package, and compare it with the maximum the design allows.
4. Grade each declared layout clearance (conductor spacing, wire-bond to
   adjacent feature, die-to-die) against its minimum.
5. Return one release-or-hold verdict with every shortfall named; a boundary
   equality is absorbed by a named tolerance, never by relaxing the limit.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "REQUIRED_DESIGN_EVIDENCE",
    "DEFAULT_DERATING_LIMITS",
    "validate_evidence_record",
    "missing_evidence",
    "derating_ratio",
    "derating_limit_for",
    "assess_element",
    "assess_elements",
    "junction_temperature_c",
    "thermal_margin_k",
    "clearance_margin_mm",
    "assess_clearances",
    "assess_hybrid_design",
]

# Ratios and margins are built from divisions and sums, so a case that is
# physically exactly at its limit can land a few ULP either side of it.
# Absorb the representation error here, never by widening the limit.
MARGIN_TOLERANCE = 1e-9

# The pieces of design evidence a hybrid design package carries before it is
# handed to manufacturing. Absence of any one of them is a hold, not a
# judgement call.
REQUIRED_DESIGN_EVIDENCE = (
    "design-rules",
    "parts-and-materials-list",
    "derating-analysis",
    "thermal-analysis",
    "layout-drawing",
    "worst-case-analysis",
    "testability-provisions",
)

# Applied-to-rated stress ceiling per element family.
DEFAULT_DERATING_LIMITS = {
    "resistor": 0.50,
    "capacitor": 0.60,
    "semiconductor-die": 0.70,
    "magnetic": 0.50,
    "interconnect": 0.80,
}


def _real(value, label, allow_zero=False, allow_negative=False):
    """Return value as a validated finite float."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if not allow_negative:
        if out < 0.0:
            raise ValueError("%s must not be negative, got %g" % (label, out))
        if out == 0.0 and not allow_zero:
            raise ValueError("%s must be strictly positive, got %g" % (label, out))
    return out


def _le(value, limit):
    """True when value is at or below limit, absorbing representation error."""
    return value <= limit or math.isclose(value, limit, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)


def validate_evidence_record(record):
    """Return the design-evidence record as a validated name -> bool mapping."""
    if not isinstance(record, dict):
        raise ValueError("evidence record must be a mapping of item -> bool")
    out = {}
    for key, value in record.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError("evidence item name must be a non-empty string, got %r" % (key,))
        name = key.strip().lower()
        if name not in REQUIRED_DESIGN_EVIDENCE:
            raise ValueError(
                "unknown evidence item '%s'; expected one of %s"
                % (name, ", ".join(REQUIRED_DESIGN_EVIDENCE))
            )
        if not isinstance(value, bool):
            raise ValueError("evidence item '%s' must be a boolean, got %r" % (name, value))
        if name in out:
            raise ValueError("evidence item '%s' declared twice" % name)
        out[name] = value
    return out


def missing_evidence(record):
    """Return the mandated evidence items that are absent or not yet complete."""
    validated = validate_evidence_record(record)
    return tuple(item for item in REQUIRED_DESIGN_EVIDENCE if not validated.get(item, False))


def derating_ratio(applied, rated):
    """Return the applied-to-rated stress ratio of one element."""
    a = _real(applied, "applied", allow_zero=True)
    r = _real(rated, "rated")
    return a / r


def derating_limit_for(family, limits=None):
    """Return the derating ceiling for an element family."""
    if not isinstance(family, str) or not family.strip():
        raise ValueError("family must be a non-empty string, got %r" % (family,))
    key = family.strip().lower()
    table = DEFAULT_DERATING_LIMITS if limits is None else limits
    if not isinstance(table, dict):
        raise ValueError("limits must be a mapping of family -> ceiling")
    if key not in table:
        raise ValueError("no derating limit declared for family '%s'" % key)
    return _real(table[key], "derating limit for '%s'" % key)


def assess_element(element, limits=None):
    """Return the derating record of one declared element."""
    if not isinstance(element, dict):
        raise ValueError("element must be a mapping")
    for key in ("reference", "family", "applied", "rated"):
        if key not in element:
            raise ValueError("element missing required key '%s'" % key)
    reference = element["reference"]
    if not isinstance(reference, str) or not reference.strip():
        raise ValueError("element reference must be a non-empty string")
    limit = derating_limit_for(element["family"], limits)
    ratio = derating_ratio(element["applied"], element["rated"])
    return {
        "reference": reference.strip(),
        "family": element["family"].strip().lower(),
        "ratio": ratio,
        "limit": limit,
        "compliant": _le(ratio, limit),
    }


def assess_elements(elements, limits=None):
    """Return the derating records of every declared element."""
    if not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence of element mappings")
    if not elements:
        raise ValueError("at least one element must be declared for a derating screen")
    records = []
    seen = set()
    for element in elements:
        record = assess_element(element, limits)
        if record["reference"] in seen:
            raise ValueError("element reference '%s' declared twice" % record["reference"])
        seen.add(record["reference"])
        records.append(record)
    return records


def junction_temperature_c(base_temperature_c, dissipation_w, thermal_resistances_k_per_w):
    """Return the junction temperature from the stacked thermal resistances."""
    base = _real(base_temperature_c, "base_temperature_c", allow_zero=True, allow_negative=True)
    power = _real(dissipation_w, "dissipation_w", allow_zero=True)
    if not isinstance(thermal_resistances_k_per_w, (list, tuple)) or not thermal_resistances_k_per_w:
        raise ValueError("thermal_resistances_k_per_w must be a non-empty sequence")
    total = 0.0
    for i, item in enumerate(thermal_resistances_k_per_w):
        total += _real(item, "thermal_resistances_k_per_w[%d]" % i, allow_zero=True)
    return base + power * total


def thermal_margin_k(junction_temperature, max_junction_temperature_c):
    """Return how far the junction sits below its allowed maximum, in kelvin."""
    tj = _real(junction_temperature, "junction_temperature", allow_zero=True, allow_negative=True)
    tmax = _real(
        max_junction_temperature_c, "max_junction_temperature_c", allow_zero=True, allow_negative=True
    )
    return tmax - tj


def clearance_margin_mm(declared_mm, minimum_mm):
    """Return how far a declared layout clearance exceeds its minimum."""
    declared = _real(declared_mm, "declared_mm", allow_zero=True)
    minimum = _real(minimum_mm, "minimum_mm", allow_zero=True)
    return declared - minimum


def assess_clearances(declared, minima):
    """Return one record per layout clearance the design rules call out."""
    if not isinstance(declared, dict) or not isinstance(minima, dict):
        raise ValueError("clearances and their minima must both be mappings")
    if not minima:
        raise ValueError("at least one clearance minimum must be declared")
    records = []
    for name in sorted(minima):
        if name not in declared:
            raise ValueError("layout clearance '%s' has a minimum but no declared value" % name)
        margin = clearance_margin_mm(declared[name], minima[name])
        records.append(
            {
                "name": name,
                "declared_mm": float(declared[name]),
                "minimum_mm": float(minima[name]),
                "margin_mm": margin,
                "compliant": _le(0.0, margin),
            }
        )
    for name in declared:
        if name not in minima:
            raise ValueError("layout clearance '%s' has no declared minimum to grade it" % name)
    return records


def assess_hybrid_design(spec):
    """Run the full clause 7.1 pre-manufacture design assessment.

    spec keys: evidence, elements, base_temperature_c, dissipation_w,
    thermal_resistances_k_per_w, max_junction_temperature_c, clearances_mm,
    clearance_minima_mm, optional derating_limits.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "evidence",
        "elements",
        "base_temperature_c",
        "dissipation_w",
        "thermal_resistances_k_per_w",
        "max_junction_temperature_c",
        "clearances_mm",
        "clearance_minima_mm",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    gaps = missing_evidence(spec["evidence"])
    elements = assess_elements(spec["elements"], spec.get("derating_limits"))
    tj = junction_temperature_c(
        spec["base_temperature_c"],
        spec["dissipation_w"],
        spec["thermal_resistances_k_per_w"],
    )
    margin_k = thermal_margin_k(tj, spec["max_junction_temperature_c"])
    clearances = assess_clearances(spec["clearances_mm"], spec["clearance_minima_mm"])

    over_derated = [r["reference"] for r in elements if not r["compliant"]]
    tight_clearances = [r["name"] for r in clearances if not r["compliant"]]
    thermal_ok = _le(0.0, margin_k)

    findings = []
    if gaps:
        findings.append("design evidence incomplete: %s" % ", ".join(gaps))
    if over_derated:
        findings.append("elements above their derating limit: %s" % ", ".join(over_derated))
    if not thermal_ok:
        findings.append(
            "junction temperature %.3f C exceeds the allowed maximum by %.3f K"
            % (tj, -margin_k)
        )
    if tight_clearances:
        findings.append("layout clearances below minimum: %s" % ", ".join(tight_clearances))

    return {
        "evidence_gaps": gaps,
        "element_records": elements,
        "over_derated": tuple(over_derated),
        "junction_temperature_c": tj,
        "thermal_margin_k": margin_k,
        "thermal_compliant": thermal_ok,
        "clearance_records": clearances,
        "tight_clearances": tuple(tight_clearances),
        "findings": findings,
        "releasable": not findings,
    }
