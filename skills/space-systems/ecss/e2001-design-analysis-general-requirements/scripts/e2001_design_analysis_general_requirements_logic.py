"""General applicability of multipaction design analysis to equipment types.

Anchor: ECSS-E-ST-20-01C clause 5.3.2.1 (design analysis -- general
requirements: which equipment types the analysis applies to, and how the
single-carrier and multicarrier cases are each covered). Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Categorize each item of equipment by type and decide whether it carries RF
   power through a region that can reach vacuum during operation.
2. Decide the operating environment route: a vacuum-exposed region belongs to
   the multipaction route; a sealed pressurised region belongs to the gas
   discharge route and must say so explicitly.
3. Determine the carrier case from the declared carrier set: one carrier is
   the single-carrier case, several carriers the multicarrier case with a
   coherent peak-envelope amplitude sum.
4. Screen the item: if the peak gap voltage cannot reach the lowest tabulated
   breakdown-voltage threshold, design analysis is not demanded, but the
   screening result is recorded as evidence.
5. Derive the required analysis coverage and compare it with what the design
   file declares; every gap is a finding.
"""

import math

__all__ = [
    "VOLTAGE_TOLERANCE_REL",
    "EQUIPMENT_TYPES",
    "ENVIRONMENTS",
    "ANALYSIS_ITEMS",
    "normalize_equipment_type",
    "normalize_environment",
    "environment_route",
    "carrier_case",
    "peak_envelope_power_w",
    "average_carrier_power_w",
    "gap_voltage_v",
    "screen_equipment",
    "required_analysis_items",
    "assess_equipment_item",
    "assess_design_analysis_coverage",
]

# The screening comparison is a square root of a product against a tabulated
# value: an exactly-at-the-threshold item can land a few ULPs on either side.
# Absorb the representation error; never move the engineering threshold.
VOLTAGE_TOLERANCE_REL = 1e-12

# Equipment families seen in a transmit chain. rf_power_carrying decides
# whether the item can develop a gap voltage at all.
EQUIPMENT_TYPES = {
    "waveguide-filter": {"rf_power_carrying": True},
    "output-multiplexer": {"rf_power_carrying": True},
    "diplexer": {"rf_power_carrying": True},
    "coaxial-switch": {"rf_power_carrying": True},
    "waveguide-switch": {"rf_power_carrying": True},
    "rotary-joint": {"rf_power_carrying": True},
    "antenna-feed-chain": {"rf_power_carrying": True},
    "radiating-element": {"rf_power_carrying": True},
    "amplifier-output-section": {"rf_power_carrying": True},
    "waveguide-transition": {"rf_power_carrying": True},
    "directional-coupler": {"rf_power_carrying": True},
    "isolator-circulator": {"rf_power_carrying": True},
    "dc-power-harness": {"rf_power_carrying": False},
    "digital-processing-unit": {"rf_power_carrying": False},
    "telemetry-sensor-harness": {"rf_power_carrying": False},
}

# Operating environment of the region carrying the RF field.
ENVIRONMENTS = {
    "vented-to-vacuum": "multipaction-route",
    "open-to-vacuum": "multipaction-route",
    "hermetically-sealed-pressurised": "gas-discharge-route",
    "gas-filled-waveguide": "gas-discharge-route",
}

ANALYSIS_ITEMS = (
    "single-carrier-design-analysis",
    "multicarrier-design-analysis",
)


def normalize_equipment_type(name):
    """Return the canonical equipment-type key."""
    if not isinstance(name, str):
        raise ValueError("equipment type must be a string, got %r" % (name,))
    key = name.strip().lower()
    if not key:
        raise ValueError("equipment type must not be empty")
    if key not in EQUIPMENT_TYPES:
        raise ValueError("uncategorized equipment type '%s'" % name)
    return key


def normalize_environment(name):
    """Return the canonical operating-environment key."""
    if not isinstance(name, str):
        raise ValueError("environment must be a string, got %r" % (name,))
    key = name.strip().lower()
    if not key:
        raise ValueError("environment must not be empty")
    if key not in ENVIRONMENTS:
        raise ValueError("uncategorized operating environment '%s'" % name)
    return key


def environment_route(name):
    """Return the breakdown route implied by the operating environment."""
    return ENVIRONMENTS[normalize_environment(name)]


def _validate_power(value, label):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite" % label)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, v))
    return v


def _validate_carriers(carrier_powers_w):
    if not isinstance(carrier_powers_w, (list, tuple)) or not carrier_powers_w:
        raise ValueError("carrier_powers_w must be a non-empty sequence of carrier powers")
    return [_validate_power(p, "carrier power") for p in carrier_powers_w]


def carrier_case(carrier_powers_w):
    """Return 'single-carrier' or 'multicarrier' for the declared carrier set."""
    powers = _validate_carriers(carrier_powers_w)
    return "single-carrier" if len(powers) == 1 else "multicarrier"


def peak_envelope_power_w(carrier_powers_w):
    """Return the worst-case coherent peak-envelope power of the carrier set."""
    powers = _validate_carriers(carrier_powers_w)
    amplitude_sum = math.fsum(math.sqrt(p) for p in powers)
    return amplitude_sum * amplitude_sum


def average_carrier_power_w(carrier_powers_w):
    """Return the summed average power of the carrier set."""
    return math.fsum(_validate_carriers(carrier_powers_w))


def gap_voltage_v(power_w, impedance_ohm, magnification=1.0):
    """Return the peak gap voltage produced by a power level."""
    p = _validate_power(power_w, "power_w")
    z = _validate_power(impedance_ohm, "impedance_ohm")
    m = _validate_power(magnification, "magnification")
    return m * math.sqrt(2.0 * z * p)


def screen_equipment(peak_voltage_v, lowest_threshold_v):
    """Return True when the item is screened out (cannot reach the threshold)."""
    v = _validate_power(peak_voltage_v, "peak_voltage_v")
    limit = _validate_power(lowest_threshold_v, "lowest_threshold_v")
    if v < limit:
        return True
    return math.isclose(v, limit, rel_tol=VOLTAGE_TOLERANCE_REL, abs_tol=0.0)


def required_analysis_items(case, in_scope, screened_out):
    """Return the analysis coverage demanded for an item."""
    if case not in ("single-carrier", "multicarrier"):
        raise ValueError("uncategorized carrier case '%s'" % (case,))
    if not isinstance(in_scope, bool) or not isinstance(screened_out, bool):
        raise ValueError("in_scope and screened_out must be booleans")
    if not in_scope or screened_out:
        return []
    if case == "single-carrier":
        return ["single-carrier-design-analysis"]
    return ["single-carrier-design-analysis", "multicarrier-design-analysis"]


def _validate_declared(declared):
    if declared is None:
        return []
    if not isinstance(declared, (list, tuple)):
        raise ValueError("declared_analyses must be a sequence")
    out = []
    for item in declared:
        if not isinstance(item, str):
            raise ValueError("declared analysis entry must be a string, got %r" % (item,))
        key = item.strip().lower()
        if key not in ANALYSIS_ITEMS:
            raise ValueError("uncategorized declared analysis item '%s'" % item)
        out.append(key)
    return out


def assess_equipment_item(item):
    """Assess one equipment item against clause 5.3.2.1.

    item keys: id, equipment_type, environment, carrier_powers_w,
    impedance_ohm, lowest_threshold_v, optional magnification and
    declared_analyses.
    """
    if not isinstance(item, dict):
        raise ValueError("equipment item must be a mapping")
    for key in ("id", "equipment_type", "environment", "carrier_powers_w",
                "impedance_ohm", "lowest_threshold_v"):
        if key not in item:
            raise ValueError("equipment item missing required key '%s'" % key)
    if not isinstance(item["id"], str) or not item["id"].strip():
        raise ValueError("equipment item id must be a non-empty string")
    eq_type = normalize_equipment_type(item["equipment_type"])
    env = normalize_environment(item["environment"])
    route = ENVIRONMENTS[env]
    case = carrier_case(item["carrier_powers_w"])
    peak_power = peak_envelope_power_w(item["carrier_powers_w"])
    average_power = average_carrier_power_w(item["carrier_powers_w"])
    magnification = item.get("magnification", 1.0)
    peak_voltage = gap_voltage_v(peak_power, item["impedance_ohm"], magnification)
    rf_carrying = EQUIPMENT_TYPES[eq_type]["rf_power_carrying"]
    in_scope = bool(rf_carrying and route == "multipaction-route")
    screened_out = screen_equipment(peak_voltage, item["lowest_threshold_v"]) if in_scope else False
    required = required_analysis_items(case, in_scope, screened_out)
    declared = _validate_declared(item.get("declared_analyses"))
    missing = [name for name in required if name not in declared]
    findings = []
    for name in missing:
        findings.append("%s: %s required for the %s case but not declared"
                        % (item["id"], name, case))
    if rf_carrying and route == "gas-discharge-route":
        findings.append(
            "%s: RF region is %s, so the gas discharge route applies and has to be "
            "declared instead of the multipaction route" % (item["id"], env)
        )
    extraneous = [name for name in declared if name not in required]
    for name in extraneous:
        findings.append("%s: %s declared although the item does not demand it"
                        % (item["id"], name))
    return {
        "id": item["id"],
        "equipment_type": eq_type,
        "environment": env,
        "route": route,
        "carrier_case": case,
        "carrier_count": len(item["carrier_powers_w"]),
        "peak_envelope_power_w": peak_power,
        "average_power_w": average_power,
        "peak_gap_voltage_v": peak_voltage,
        "in_scope": in_scope,
        "screened_out": screened_out,
        "required_analyses": required,
        "declared_analyses": declared,
        "missing_analyses": missing,
        "findings": findings,
        "compliant": not findings,
    }


def assess_design_analysis_coverage(items):
    """Assess a set of equipment items and aggregate the coverage findings."""
    if not isinstance(items, (list, tuple)) or not items:
        raise ValueError("items must be a non-empty sequence of equipment items")
    seen = set()
    records = []
    for item in items:
        record = assess_equipment_item(item)
        if record["id"] in seen:
            raise ValueError("duplicate equipment item id '%s'" % record["id"])
        seen.add(record["id"])
        records.append(record)
    findings = []
    for record in records:
        findings.extend(record["findings"])
    return {
        "records": records,
        "in_scope_count": sum(1 for r in records if r["in_scope"]),
        "screened_out_count": sum(1 for r in records if r["screened_out"]),
        "multicarrier_count": sum(1 for r in records if r["carrier_case"] == "multicarrier"),
        "findings": findings,
        "compliant": not findings,
    }
