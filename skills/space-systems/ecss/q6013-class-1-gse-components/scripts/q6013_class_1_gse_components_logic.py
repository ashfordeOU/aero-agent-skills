"""Commercial components inside ground support equipment that touches flight hardware.

Anchor: ECSS-Q-ST-60-13C clause 4.1.5 (commercial components used in ground
support equipment connected to flight hardware). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate each ground support equipment part and the interface it sits behind.
2. Form the worst-case electrical energy the part can drive into the flight
   side from its own supply voltage and current limit -- the fault case, not
   the nominal operating point.
3. Credit a protection barrier only when the barrier is itself qualified; an
   undemonstrated barrier earns no attenuation at all.
4. Compare the attenuated injection with the susceptibility limit declared for
   the flight interface and form the interface margin.
5. Return the control category each part earns: ordinary ground support
   control when it cannot reach flight hardware, declared-with-protection when
   the margin holds, and flight-equivalent control when it does not.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "BARRIER_ATTENUATION",
    "CONTROL_CATEGORIES",
    "validate_identifier",
    "worst_case_injection_w",
    "credited_attenuation",
    "effective_injection_w",
    "interface_margin",
    "control_category",
    "evaluate_gse_part",
    "assess_gse_commercial_parts",
]

# A margin that is exactly met is met. Absorb the representation error of the
# division here instead of nudging the required margin.
MARGIN_TOLERANCE = 1e-9

# Protection barrier -> the power attenuation it is worth when it has been
# qualified. An unqualified barrier is credited nothing, whatever it is.
BARRIER_ATTENUATION = {
    "none": 1.0,
    "series-resistor": 20.0,
    "current-limited-supply": 50.0,
    "opto-isolator": 1000.0,
    "galvanic-transformer": 2000.0,
    "optical-fibre-link": 1.0e6,
}

CONTROL_CATEGORIES = (
    "gse-standard-control",
    "declared-with-protection",
    "flight-equivalent-control",
)

_CATEGORY_SEVERITY = {
    "flight-equivalent-control": 0,
    "declared-with-protection": 1,
    "gse-standard-control": 2,
}


def _require_positive(value, label):
    """Return a strictly positive finite float, or raise."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %g" % (label, number))
    return number


def _require_bool(value, label):
    """Return a genuine boolean, or raise."""
    if not isinstance(value, bool):
        raise ValueError("%s must be True or False, got %r" % (label, value))
    return value


def validate_identifier(value, label):
    """Return a non-blank stripped identifier, or raise."""
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (label, value))
    text = value.strip()
    if not text:
        raise ValueError("%s must not be blank" % label)
    return text


def worst_case_injection_w(supply_voltage_v, current_limit_a):
    """Return the worst-case power the part can drive into the flight side."""
    voltage = _require_positive(supply_voltage_v, "supply_voltage_v")
    current = _require_positive(current_limit_a, "current_limit_a")
    return voltage * current


def credited_attenuation(barrier_type, barrier_qualified):
    """Return the power attenuation credited to a protection barrier."""
    barrier = validate_identifier(barrier_type, "barrier_type").lower()
    if barrier not in BARRIER_ATTENUATION:
        raise ValueError(
            "unknown barrier_type %r; known: %s"
            % (barrier_type, ", ".join(sorted(BARRIER_ATTENUATION)))
        )
    qualified = _require_bool(barrier_qualified, "barrier_qualified")
    if barrier == "none":
        return 1.0
    if not qualified:
        return 1.0
    return BARRIER_ATTENUATION[barrier]


def effective_injection_w(worst_case_w, attenuation):
    """Return the injection that survives the credited barrier."""
    worst = _require_positive(worst_case_w, "worst_case_w")
    factor = _require_positive(attenuation, "attenuation")
    if factor < 1.0:
        raise ValueError("attenuation must be at least unity, got %g" % factor)
    return worst / factor


def interface_margin(susceptibility_limit_w, effective_w):
    """Return the ratio of what the flight interface tolerates to what arrives."""
    limit = _require_positive(susceptibility_limit_w, "susceptibility_limit_w")
    arriving = _require_positive(effective_w, "effective_w")
    return limit / arriving


def control_category(flight_connected, margin, required_margin):
    """Return the control category a ground support part earns."""
    connected = _require_bool(flight_connected, "flight_connected")
    if not connected:
        return "gse-standard-control"
    ratio = _require_positive(margin, "margin")
    required = _require_positive(required_margin, "required_margin")
    if ratio > required or math.isclose(ratio, required, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0):
        return "declared-with-protection"
    return "flight-equivalent-control"


def evaluate_gse_part(part, interfaces, required_margin):
    """Return the control record of one ground support equipment part.

    part keys: part_id, flight_connected, and when connected supply_voltage_v,
    current_limit_a, interface_id, barrier_type, barrier_qualified.
    interfaces maps an interface identifier to its susceptibility limit in W.
    """
    if not isinstance(part, dict):
        raise ValueError("each part must be a mapping, got %r" % (type(part).__name__,))
    if not isinstance(interfaces, dict) or not interfaces:
        raise ValueError("interfaces must be a non-empty mapping of limits")
    required = _require_positive(required_margin, "required_margin")
    part_id = validate_identifier(part.get("part_id"), "part_id")
    connected = _require_bool(part.get("flight_connected"), "flight_connected")

    record = {
        "part_id": part_id,
        "flight_connected": connected,
        "interface_id": None,
        "worst_case_injection_w": None,
        "credited_attenuation": None,
        "effective_injection_w": None,
        "margin": None,
        "required_margin": required,
        "category": "gse-standard-control",
        "notes": [],
    }
    if not connected:
        return record

    interface_id = validate_identifier(part.get("interface_id"), "interface_id")
    if interface_id not in interfaces:
        raise ValueError(
            "interface %r has no declared susceptibility limit" % interface_id
        )
    limit = _require_positive(interfaces[interface_id], "susceptibility limit of %s" % interface_id)
    worst = worst_case_injection_w(part.get("supply_voltage_v"), part.get("current_limit_a"))
    barrier = validate_identifier(part.get("barrier_type", "none"), "barrier_type").lower()
    qualified = _require_bool(part.get("barrier_qualified", False), "barrier_qualified")
    attenuation = credited_attenuation(barrier, qualified)
    if barrier != "none" and not qualified:
        record["notes"].append(
            "barrier %s is not qualified; no attenuation credited" % barrier
        )
    if barrier == "none":
        record["notes"].append("part sits directly on the flight interface with no barrier")
    effective = effective_injection_w(worst, attenuation)
    margin = interface_margin(limit, effective)

    record.update(
        {
            "interface_id": interface_id,
            "worst_case_injection_w": worst,
            "credited_attenuation": attenuation,
            "effective_injection_w": effective,
            "margin": margin,
            "category": control_category(True, margin, required),
        }
    )
    return record


def assess_gse_commercial_parts(spec):
    """Run the full clause 4.1.5 ground support equipment assessment.

    spec keys: parts (sequence of part mappings), interfaces (identifier ->
    susceptibility limit in W), optional required_margin (default 2.0).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parts", "interfaces"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parts = spec["parts"]
    if not isinstance(parts, (list, tuple)) or not parts:
        raise ValueError("spec['parts'] must be a non-empty sequence")
    required = _require_positive(spec.get("required_margin", 2.0), "required_margin")
    interfaces = spec["interfaces"]

    records = [evaluate_gse_part(part, interfaces, required) for part in parts]
    counts = {category: 0 for category in CONTROL_CATEGORIES}
    for record in records:
        counts[record["category"]] += 1

    connected = [record for record in records if record["flight_connected"]]
    governing = None
    for record in connected:
        if governing is None or record["margin"] < governing["margin"]:
            governing = record
        elif math.isclose(record["margin"], governing["margin"], rel_tol=1e-12, abs_tol=0.0):
            if record["part_id"] < governing["part_id"]:
                governing = record

    findings = []
    for record in records:
        if record["category"] == "flight-equivalent-control":
            findings.append(
                {
                    "severity": 0,
                    "part_id": record["part_id"],
                    "detail": "margin %.3f on interface %s is below the required %.3f; "
                    "the part carries flight-equivalent control"
                    % (record["margin"], record["interface_id"], required),
                }
            )
        for note in record["notes"]:
            findings.append({"severity": 1, "part_id": record["part_id"], "detail": note})
    findings.sort(key=lambda item: (item["severity"], item["part_id"]))

    return {
        "records": records,
        "category_counts": counts,
        "governing_part": governing,
        "required_margin": required,
        "findings": findings,
        "compliant": counts["flight-equivalent-control"] == 0,
        "verdict": "accept" if counts["flight-equivalent-control"] == 0 else "escalate",
    }
