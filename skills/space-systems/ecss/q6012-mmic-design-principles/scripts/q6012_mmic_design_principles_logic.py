"""Judging how a monolithic microwave circuit design is conceived and refined.

Anchor: ECSS-Q-ST-60-12C clause 7.1 (the guiding ideas a monolithic microwave
circuit design is shaped by). Paraphrased into an implementable procedure; no
standard text is reproduced.

Procedure implemented here
--------------------------
1. Turn each performance parameter into a parametric margin: how many standard
   deviations of process spread separate the nominal prediction from the
   specification limit, and what fraction of parts that leaves inside it.
2. Combine the per-parameter fractions into one predicted parametric yield,
   because a circuit is sold against every line of its specification at once.
3. Grade each device stress - channel temperature, metal current density, RF
   power density, gate voltage, dissipation - against its derated limit rather
   than its absolute one.
4. Weigh the proven library cells in the design against the novel structures,
   and require a test vehicle when the novel share is large.
5. Require design-rule cleanliness and on-wafer test provision before the
   design is taken to a mask set.
6. Return one verdict naming the most severe thing that stops the design, with
   the per-parameter and per-stress records behind it.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "LIMIT_SENSES",
    "DEFAULT_DERATING_FACTORS",
    "DEFAULT_DESIGN_POLICY",
    "STATUS_PRECEDENCE",
    "DESIGN_PRINCIPLES_SATISFIED",
    "PARAMETRIC_MARGIN_SHORTFALL",
    "PREDICTED_YIELD_SHORTFALL",
    "DERATING_LIMIT_EXCEEDED",
    "UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE",
    "DESIGN_RULE_VIOLATIONS_OPEN",
    "ON_WAFER_TEST_PROVISION_MISSING",
    "normal_cdf",
    "validate_design_policy",
    "validate_parameter",
    "parametric_margin_sigma",
    "parametric_yield",
    "assess_parameter",
    "combined_yield",
    "validate_stress",
    "derated_limit",
    "derating_ratio",
    "assess_stress",
    "proven_cell_fraction",
    "assess_design_principles",
]

# Margins and derating ratios are quotients of measured quantities; a case that
# sits physically exactly on its bound can land a few ULP either side. Absorb
# that here rather than by relaxing the engineering limit.
MARGIN_TOLERANCE = 1e-9

# Whether the specification limit is a floor the parameter must stay above or a
# ceiling it must stay below.
LIMIT_SENSES = ("lower", "upper")

# Fraction of the absolute device limit a design is allowed to use.
DEFAULT_DERATING_FACTORS = {
    "channel-temperature-c": 0.80,
    "metal-current-density-ma-per-um": 0.75,
    "rf-power-density-w-per-mm": 0.70,
    "gate-source-voltage-v": 0.80,
    "junction-power-dissipation-w": 0.75,
}

DESIGN_PRINCIPLES_SATISFIED = "design-principles-satisfied"
PARAMETRIC_MARGIN_SHORTFALL = "parametric-margin-shortfall"
PREDICTED_YIELD_SHORTFALL = "predicted-parametric-yield-shortfall"
DERATING_LIMIT_EXCEEDED = "device-derating-limit-exceeded"
UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE = "unproven-structure-without-test-vehicle"
DESIGN_RULE_VIOLATIONS_OPEN = "design-rule-violations-open"
ON_WAFER_TEST_PROVISION_MISSING = "on-wafer-test-provision-missing"

# Most severe first: a design with several defects reports the worst of them.
STATUS_PRECEDENCE = (
    DERATING_LIMIT_EXCEEDED,
    DESIGN_RULE_VIOLATIONS_OPEN,
    PARAMETRIC_MARGIN_SHORTFALL,
    PREDICTED_YIELD_SHORTFALL,
    UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE,
    ON_WAFER_TEST_PROVISION_MISSING,
)

DEFAULT_DESIGN_POLICY = {
    # Standard deviations of process spread required between the nominal
    # prediction and each specification limit.
    "required_margin_sigma": 3.0,
    # Predicted fraction of parts meeting every specification line at once.
    "min_predicted_yield": 0.95,
    # Fraction of the cells in the design that must come from proven library.
    "min_proven_cell_fraction": 0.70,
    # Whether on-wafer test structures must be provided on the mask set.
    "require_on_wafer_test_structures": True,
}


def _is_real(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def normal_cdf(z):
    """Return the standard normal cumulative probability at z."""
    if not _is_real(z):
        raise ValueError("z must be a real number")
    value = float(z)
    if not math.isfinite(value):
        raise ValueError("z must be finite")
    return 0.5 * (1.0 + math.erf(value / math.sqrt(2.0)))


def validate_design_policy(policy=None):
    """Return a complete design policy with the defaults filled in."""
    if policy is None:
        return dict(DEFAULT_DESIGN_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("design policy must be a mapping")
    merged = dict(DEFAULT_DESIGN_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_DESIGN_POLICY:
            raise ValueError("unknown design policy key %r" % (key,))
        default = DEFAULT_DESIGN_POLICY[key]
        if isinstance(default, bool):
            if not isinstance(value, bool):
                raise ValueError("%s must be a boolean" % key)
        else:
            if not _is_real(value):
                raise ValueError("%s must be a real number" % key)
            value = float(value)
            if not math.isfinite(value) or value < 0.0:
                raise ValueError("%s must be non-negative and finite" % key)
        merged[key] = value
    for key in ("min_predicted_yield", "min_proven_cell_fraction"):
        if merged[key] > 1.0:
            raise ValueError("%s cannot exceed 1.0" % key)
    return merged


def validate_parameter(parameter):
    """Return a validated performance-parameter record."""
    if not isinstance(parameter, dict):
        raise ValueError("parameter must be a mapping")
    for key in ("id", "nominal", "limit", "sense", "sigma"):
        if key not in parameter:
            raise ValueError("parameter missing required key '%s'" % key)
    identifier = parameter["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("parameter id must be a non-empty string")
    sense = parameter["sense"]
    if sense not in LIMIT_SENSES:
        raise ValueError("unknown limit sense %r" % (sense,))
    for key in ("nominal", "limit", "sigma"):
        if not _is_real(parameter[key]):
            raise ValueError("parameter %s must be a real number" % key)
        if not math.isfinite(float(parameter[key])):
            raise ValueError("parameter %s must be finite" % key)
    sigma = float(parameter["sigma"])
    if sigma <= 0.0:
        raise ValueError("parameter sigma must be positive, got %r" % (parameter["sigma"],))
    return {
        "id": identifier.strip(),
        "nominal": float(parameter["nominal"]),
        "limit": float(parameter["limit"]),
        "sense": sense,
        "sigma": sigma,
    }


def parametric_margin_sigma(parameter):
    """Return the margin between nominal and limit in standard deviations."""
    record = validate_parameter(parameter)
    if record["sense"] == "lower":
        gap = record["nominal"] - record["limit"]
    else:
        gap = record["limit"] - record["nominal"]
    return gap / record["sigma"]


def parametric_yield(margin_sigma):
    """Return the fraction of parts inside the limit for a margin in sigma."""
    return normal_cdf(margin_sigma)


def assess_parameter(parameter, policy=None):
    """Assess one performance parameter and return its record."""
    rules = validate_design_policy(policy)
    record = validate_parameter(parameter)
    margin = parametric_margin_sigma(record)
    fraction = parametric_yield(margin)
    statuses = []
    findings = []
    if margin < rules["required_margin_sigma"] - MARGIN_TOLERANCE:
        statuses.append(PARAMETRIC_MARGIN_SHORTFALL)
        findings.append(
            "parameter %s holds %.3f sigma of process spread against its limit, "
            "the design rule asks for %.3f"
            % (record["id"], margin, rules["required_margin_sigma"])
        )
    record = dict(record)
    record["margin_sigma"] = margin
    record["yield_fraction"] = fraction
    record["statuses"] = statuses
    record["findings"] = findings
    record["acceptable"] = not statuses
    return record


def combined_yield(records):
    """Return the predicted fraction of parts meeting every parameter at once."""
    if not isinstance(records, (list, tuple)) or not records:
        raise ValueError("records must be a non-empty sequence of parameter records")
    product = 1.0
    for record in records:
        if not isinstance(record, dict) or "yield_fraction" not in record:
            raise ValueError("each record must be a mapping carrying 'yield_fraction'")
        value = record["yield_fraction"]
        if not _is_real(value) or not 0.0 <= float(value) <= 1.0:
            raise ValueError("yield_fraction must lie between zero and one")
        product *= float(value)
    return product


def validate_stress(stress):
    """Return a validated device-stress record."""
    if not isinstance(stress, dict):
        raise ValueError("stress must be a mapping")
    for key in ("kind", "applied", "limit"):
        if key not in stress:
            raise ValueError("stress missing required key '%s'" % key)
    kind = stress["kind"]
    if kind not in DEFAULT_DERATING_FACTORS:
        raise ValueError("unknown device stress kind %r" % (kind,))
    for key in ("applied", "limit"):
        if not _is_real(stress[key]):
            raise ValueError("stress %s must be a real number" % key)
        if not math.isfinite(float(stress[key])):
            raise ValueError("stress %s must be finite" % key)
    applied = float(stress["applied"])
    limit = float(stress["limit"])
    if limit <= 0.0:
        raise ValueError("stress limit must be positive, got %r" % (stress["limit"],))
    if applied < 0.0:
        raise ValueError("applied stress must be non-negative, got %r" % (stress["applied"],))
    factor = stress.get("derating_factor", DEFAULT_DERATING_FACTORS[kind])
    if not _is_real(factor):
        raise ValueError("derating_factor must be a real number")
    factor = float(factor)
    if not math.isfinite(factor) or not 0.0 < factor <= 1.0:
        raise ValueError("derating_factor must lie above zero and at most one")
    return {"kind": kind, "applied": applied, "limit": limit, "derating_factor": factor}


def derated_limit(stress):
    """Return the fraction of the absolute limit the design may use."""
    record = validate_stress(stress)
    return record["limit"] * record["derating_factor"]


def derating_ratio(stress):
    """Return the applied stress as a fraction of its derated limit."""
    record = validate_stress(stress)
    return record["applied"] / (record["limit"] * record["derating_factor"])


def assess_stress(stress, policy=None):
    """Assess one device stress against its derated limit."""
    validate_design_policy(policy)
    record = validate_stress(stress)
    allowed = record["limit"] * record["derating_factor"]
    ratio = record["applied"] / allowed
    statuses = []
    findings = []
    scale = max(abs(record["applied"]), abs(allowed), 1.0)
    if record["applied"] > allowed + scale * MARGIN_TOLERANCE:
        statuses.append(DERATING_LIMIT_EXCEEDED)
        findings.append(
            "%s runs at %.4g against a derated limit of %.4g (%.0f%% of the absolute limit)"
            % (record["kind"], record["applied"], allowed, 100.0 * record["derating_factor"])
        )
    record = dict(record)
    record["derated_limit"] = allowed
    record["derating_ratio"] = ratio
    record["statuses"] = statuses
    record["findings"] = findings
    record["acceptable"] = not statuses
    return record


def proven_cell_fraction(proven, total):
    """Return the fraction of the cells in the design taken from proven library."""
    if not _is_int(proven) or not _is_int(total):
        raise ValueError("cell counts must be integers")
    if total <= 0:
        raise ValueError("total cell count must be positive, got %r" % (total,))
    if proven < 0:
        raise ValueError("proven cell count must be non-negative, got %r" % (proven,))
    if proven > total:
        raise ValueError("proven cells %d exceed the total %d" % (proven, total))
    return proven / float(total)


def _worst_status(statuses):
    for status in STATUS_PRECEDENCE:
        if status in statuses:
            return status
    return DESIGN_PRINCIPLES_SATISFIED


def assess_design_principles(spec):
    """Run the full clause 7.1 design-principle review.

    spec keys: parameters (non-empty), stresses (non-empty), cells
    ({proven, total}), drc_violations, on_wafer_test_structures, optional
    test_vehicle_planned and policy.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("parameters", "stresses", "cells", "drc_violations",
                "on_wafer_test_structures"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    parameters = spec["parameters"]
    stresses = spec["stresses"]
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("spec['parameters'] must be a non-empty sequence")
    if not isinstance(stresses, (list, tuple)) or not stresses:
        raise ValueError("spec['stresses'] must be a non-empty sequence")
    cells = spec["cells"]
    if not isinstance(cells, dict) or "proven" not in cells or "total" not in cells:
        raise ValueError("spec['cells'] must carry 'proven' and 'total' counts")
    violations = spec["drc_violations"]
    if not _is_int(violations) or violations < 0:
        raise ValueError("drc_violations must be a non-negative integer")
    provided = spec["on_wafer_test_structures"]
    if not isinstance(provided, bool):
        raise ValueError("on_wafer_test_structures must be a boolean")
    test_vehicle = spec.get("test_vehicle_planned", False)
    if not isinstance(test_vehicle, bool):
        raise ValueError("test_vehicle_planned must be a boolean")
    rules = validate_design_policy(spec.get("policy"))

    parameter_records = [assess_parameter(item, rules) for item in parameters]
    seen = set()
    for record in parameter_records:
        if record["id"] in seen:
            raise ValueError("duplicate parameter id %r" % (record["id"],))
        seen.add(record["id"])
    stress_records = [assess_stress(item, rules) for item in stresses]
    predicted = combined_yield(parameter_records)
    proven = proven_cell_fraction(cells["proven"], cells["total"])

    statuses = []
    findings = []
    for record in parameter_records + stress_records:
        statuses.extend(record["statuses"])
        findings.extend(record["findings"])
    if predicted < rules["min_predicted_yield"] - MARGIN_TOLERANCE:
        statuses.append(PREDICTED_YIELD_SHORTFALL)
        findings.append(
            "the specification lines together predict %.4f of parts inside every limit, "
            "below the %.4f the programme works to" % (predicted, rules["min_predicted_yield"])
        )
    if proven < rules["min_proven_cell_fraction"] - MARGIN_TOLERANCE and not test_vehicle:
        statuses.append(UNPROVEN_STRUCTURE_WITHOUT_TEST_VEHICLE)
        findings.append(
            "only %.2f of the cells come from proven library and no test vehicle is "
            "planned for the novel structures" % proven
        )
    if violations > 0:
        statuses.append(DESIGN_RULE_VIOLATIONS_OPEN)
        findings.append(
            "%d foundry design-rule violations are still open against the layout" % violations
        )
    if rules["require_on_wafer_test_structures"] and not provided:
        statuses.append(ON_WAFER_TEST_PROVISION_MISSING)
        findings.append(
            "the mask set carries no on-wafer test structures, so the process cannot be "
            "monitored on the delivered wafers"
        )
    verdict = _worst_status(statuses)
    return {
        "parameters": parameter_records,
        "stresses": stress_records,
        "predicted_yield": predicted,
        "worst_margin_sigma": min(record["margin_sigma"] for record in parameter_records),
        "proven_cell_fraction": proven,
        "verdict": verdict,
        "findings": findings,
        "satisfied": verdict == DESIGN_PRINCIPLES_SATISFIED,
    }
