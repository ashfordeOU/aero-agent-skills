"""Manufacturing route and process control for threaded fasteners.

Anchor: ECSS-Q-ST-70-46, manufacturing clause (paraphrased into an
implementable procedure; no standard text is reproduced).

Procedure implemented here:

1. A fastener route is an ordered sequence, not a set of operations.
   Each admitted operation carries a position in the canonical order,
   and a declared route has to run non-decreasing through those
   positions, because the operations that damage each other when
   swapped are exactly the ones that look interchangeable on a
   traveller.
2. Some operations are mandatory and the trigger is the property
   class and the finish route rather than the shop's habit. A
   quenched and tempered class owes a heat treatment; a susceptible
   class that is electroplated owes the relief bake inside its window;
   every route owes a final inspection.
3. A process is controlled when its controlled characteristic sits
   inside its window with capability to spare. Capability is the
   distance from the process mean to the nearer window edge measured
   in three standard deviations, so a centred process with a wide
   spread and an off-centre process with a narrow one are separated
   rather than averaged.
4. Capability is graded in three bands, not two. Above the capable
   floor the process runs; between the marginal floor and the capable
   floor it runs under increased sampling; below the marginal floor
   the characteristic is not being held by the process at all and
   inspection is sorting, not controlling.
5. A qualified process is qualified at its parameters. A proposed
   change beyond the declared tolerance on any qualified parameter
   retires the qualification, and the route says so before the first
   part is run rather than after the lot is rejected.

Stdlib only, offline, deterministic.
"""

CONTROLLED = "controlled"
CONTROL_ACTION = "control-action-required"
NOT_CONTROLLED = "not-controlled"

_RANK = {CONTROLLED: 0, CONTROL_ACTION: 1, NOT_CONTROLLED: 2}

CAPABLE = "capable"
MARGINAL = "marginal"
NOT_CAPABLE = "not-capable"

# Canonical order of the admitted fastener manufacturing operations.
# A declared route must run non-decreasing through these positions.
OPERATION_ORDER = {
    "wire-drawing": 10,
    "cold-heading": 20,
    "hot-forging": 20,
    "rough-machining": 30,
    "heat-treatment": 40,
    "finish-machining": 50,
    "thread-forming": 60,
    "shot-peening": 70,
    "surface-treatment": 80,
    "embrittlement-relief-bake": 90,
    "lubricant-application": 100,
    "final-inspection": 110,
}

VALID_OPERATIONS = tuple(sorted(OPERATION_ORDER))

# Property classes that owe a quench and temper.
HEAT_TREATED_CLASSES = ("8.8", "9.8", "10.9", "12.9")

# Capability grading bands.
CAPABLE_FLOOR = 1.33
MARGINAL_FLOOR = 1.00

# The relief bake has to start inside this window after plating.
RELIEF_BAKE_WINDOW_HOURS = 4.0

# Capability indices and parameter ratios are quotients of measured
# floats, so a case exactly on a floor can land a few units in the last
# place under it. These absorb that without moving a floor.
INDEX_TOLERANCE = 1.0e-12
FRACTION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None):
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    value = float(value)
    if minimum is not None and value < minimum:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    return value


def operation_position(operation):
    """Position of one admitted operation in the canonical order."""
    if not isinstance(operation, str) or operation not in OPERATION_ORDER:
        raise ValueError(
            "unknown operation %r (expected one of %s)"
            % (operation, ", ".join(VALID_OPERATIONS))
        )
    return OPERATION_ORDER[operation]


def validate_route(operations):
    """Validate a declared route and return it normalized."""
    if not isinstance(operations, (list, tuple)) or not operations:
        raise ValueError("route must be a non-empty sequence of operations")
    positions = [operation_position(op) for op in operations]
    if len(set(operations)) != len(operations):
        raise ValueError("route repeats an operation")
    for earlier, later in zip(positions, positions[1:]):
        if later < earlier:
            raise ValueError(
                "route runs backwards through the canonical order at %r" % (later,)
            )
    return list(operations)


def missing_mandatory_operations(operations, property_class, electroplated=False):
    """Mandatory operations a route leaves out, given class and finish."""
    route = validate_route(operations)
    if not isinstance(property_class, str) or not property_class.strip():
        raise ValueError("property_class must be a non-empty string")
    missing = []
    if property_class in HEAT_TREATED_CLASSES and "heat-treatment" not in route:
        missing.append("heat-treatment")
    if electroplated:
        if "surface-treatment" not in route:
            missing.append("surface-treatment")
        if "embrittlement-relief-bake" not in route:
            missing.append("embrittlement-relief-bake")
    if "final-inspection" not in route:
        missing.append("final-inspection")
    return missing


def relief_bake_finding(delay_hours, window_hours=RELIEF_BAKE_WINDOW_HOURS):
    """Whether the relief bake started inside its window after plating."""
    delay = _numeric("delay_hours", delay_hours, 0.0)
    window = _numeric("window_hours", window_hours, 0.0)
    if window <= 0.0:
        raise ValueError("window_hours must be positive")
    return {
        "delay_hours": delay,
        "window_hours": window,
        "inside_window": delay <= window + FRACTION_TOLERANCE,
        "overrun_hours": max(0.0, delay - window),
    }


def capability_index(mean, sigma, lower, upper):
    """Distance from the mean to the nearer window edge, in three sigma."""
    mean = _numeric("mean", mean)
    sigma = _numeric("sigma", sigma, 0.0)
    lower = _numeric("lower", lower)
    upper = _numeric("upper", upper)
    if upper <= lower:
        raise ValueError("upper must sit above lower")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    return min(upper - mean, mean - lower) / (3.0 * sigma)


def capability_rating(index):
    """Grade a capability index into the three control bands."""
    index = _numeric("index", index)
    if index >= CAPABLE_FLOOR - INDEX_TOLERANCE:
        return CAPABLE
    if index >= MARGINAL_FLOOR - INDEX_TOLERANCE:
        return MARGINAL
    return NOT_CAPABLE


def validate_parameter(record):
    """Validate one controlled process parameter and normalize it."""
    if not isinstance(record, dict):
        raise ValueError("parameter must be a mapping")
    name = record.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("parameter needs a non-empty string name")
    operation = record.get("operation")
    operation_position(operation)
    lower = _numeric("%s lower" % name, record.get("lower"))
    upper = _numeric("%s upper" % name, record.get("upper"))
    if upper <= lower:
        raise ValueError("%s window must have upper above lower" % name)
    return {
        "name": name.strip(),
        "operation": operation,
        "lower": lower,
        "upper": upper,
        "mean": _numeric("%s mean" % name, record.get("mean")),
        "sigma": _numeric("%s sigma" % name, record.get("sigma"), 0.0),
        "qualified_value": record.get("qualified_value"),
        "proposed_value": record.get("proposed_value"),
        "requalification_tolerance_fraction": _numeric(
            "%s requalification_tolerance_fraction" % name,
            record.get("requalification_tolerance_fraction", 0.05),
            0.0,
        ),
    }


def requalification_required(qualified_value, proposed_value, tolerance_fraction):
    """Whether a parameter change retires the process qualification."""
    qualified = _numeric("qualified_value", qualified_value)
    proposed = _numeric("proposed_value", proposed_value)
    tolerance = _numeric("tolerance_fraction", tolerance_fraction, 0.0)
    if qualified == 0.0:
        raise ValueError("qualified_value must not be zero")
    drift = abs(proposed - qualified) / abs(qualified)
    return {
        "drift_fraction": drift,
        "tolerance_fraction": tolerance,
        "requalification_required": drift > tolerance + FRACTION_TOLERANCE,
    }


def assess_parameter(record):
    """Assess one controlled parameter: capability and qualification."""
    norm = validate_parameter(record)
    index = capability_index(
        norm["mean"], norm["sigma"], norm["lower"], norm["upper"]
    )
    rating = capability_rating(index)
    inside_window = (
        norm["lower"] - FRACTION_TOLERANCE
        <= norm["mean"]
        <= norm["upper"] + FRACTION_TOLERANCE
    )
    change = None
    if norm["qualified_value"] is not None and norm["proposed_value"] is not None:
        change = requalification_required(
            norm["qualified_value"],
            norm["proposed_value"],
            norm["requalification_tolerance_fraction"],
        )
    findings = []
    disposition = CONTROLLED
    if not inside_window:
        findings.append("%s-mean-outside-its-window" % norm["name"])
        disposition = NOT_CONTROLLED
    elif rating == NOT_CAPABLE:
        findings.append("%s-not-capable" % norm["name"])
        disposition = NOT_CONTROLLED
    elif rating == MARGINAL:
        findings.append("%s-marginally-capable" % norm["name"])
        disposition = CONTROL_ACTION
    if change is not None and change["requalification_required"]:
        findings.append("%s-change-retires-the-qualification" % norm["name"])
        if _RANK[CONTROL_ACTION] > _RANK[disposition]:
            disposition = CONTROL_ACTION
    return {
        "name": norm["name"],
        "operation": norm["operation"],
        "capability_index": index,
        "capability_rating": rating,
        "mean_inside_window": inside_window,
        "change": change,
        "findings": findings,
        "disposition": disposition,
    }


def validate_route_record(record):
    """Validate one route record and return a normalized copy."""
    if not isinstance(record, dict):
        raise ValueError("route record must be a mapping")
    part = record.get("part_number")
    if not isinstance(part, str) or not part.strip():
        raise ValueError("route record needs a non-empty part_number")
    property_class = record.get("property_class")
    if not isinstance(property_class, str) or not property_class.strip():
        raise ValueError("route record needs a property_class")
    parameters = record.get("parameters", [])
    if not isinstance(parameters, (list, tuple)):
        raise ValueError("parameters must be a sequence")
    return {
        "part_number": part.strip(),
        "property_class": property_class.strip(),
        "operations": validate_route(record.get("operations")),
        "electroplated": bool(record.get("electroplated", False)),
        "relief_bake_delay_hours": _numeric(
            "relief_bake_delay_hours", record.get("relief_bake_delay_hours", 0.0), 0.0
        ),
        "parameters": [validate_parameter(p) for p in parameters],
    }


def assess_route(record):
    """Assess one manufacturing route end to end."""
    norm = validate_route_record(record)
    findings = []
    disposition = CONTROLLED

    def escalate(level):
        if _RANK[level] > _RANK[disposition]:
            return level
        return disposition

    missing = missing_mandatory_operations(
        norm["operations"], norm["property_class"], norm["electroplated"]
    )
    for operation in missing:
        findings.append("route-missing-%s" % operation)
        disposition = escalate(NOT_CONTROLLED)

    bake = None
    if norm["electroplated"] and "embrittlement-relief-bake" in norm["operations"]:
        bake = relief_bake_finding(norm["relief_bake_delay_hours"])
        if not bake["inside_window"]:
            findings.append("relief-bake-started-outside-its-window")
            disposition = escalate(NOT_CONTROLLED)

    parameter_results = []
    for parameter in norm["parameters"]:
        result = assess_parameter(parameter)
        parameter_results.append(result)
        findings.extend(result["findings"])
        disposition = escalate(result["disposition"])

    unqualified = [
        p["operation"]
        for p in parameter_results
        if p["change"] is not None and p["change"]["requalification_required"]
    ]
    return {
        "part_number": norm["part_number"],
        "property_class": norm["property_class"],
        "operations": norm["operations"],
        "missing_operations": missing,
        "relief_bake": bake,
        "parameters": parameter_results,
        "operations_needing_requalification": sorted(set(unqualified)),
        "findings": findings,
        "disposition": disposition,
    }


def assess_shop_routes(records):
    """Assess every route on a shop order and roll them up."""
    if not isinstance(records, list) or not records:
        raise ValueError("records must be a non-empty list")
    results = []
    seen = set()
    for record in records:
        result = assess_route(record)
        if result["part_number"] in seen:
            raise ValueError("duplicate part %r" % (result["part_number"],))
        seen.add(result["part_number"])
        results.append(result)
    order = CONTROLLED
    for result in results:
        if _RANK[result["disposition"]] > _RANK[order]:
            order = result["disposition"]
    return {
        "routes": results,
        "order_disposition": order,
        "uncontrolled_parts": [
            r["part_number"] for r in results if r["disposition"] == NOT_CONTROLLED
        ],
        "parts_needing_requalification": [
            r["part_number"]
            for r in results
            if r["operations_needing_requalification"]
        ],
    }
