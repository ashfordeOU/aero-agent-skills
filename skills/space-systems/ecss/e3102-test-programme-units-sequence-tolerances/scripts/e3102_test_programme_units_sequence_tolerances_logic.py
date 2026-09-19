"""Test-programme definition for two-phase heat transport equipment.

Anchor: ECSS-E-ST-31-02C clauses 5.6.1 to 5.6.4 (test programme: number of
units, test sequence for a heat pipe versus a capillary driven loop, allowable
tolerances on applied test parameters and required measurement accuracy).
Paraphrased into an implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Unit count: the declared number of test articles is graded against the
   minimum the programme owes for that equipment type and model philosophy.
2. Sequence: each equipment type has its own ordered flow. The declared
   sequence is checked for missing steps, steps that do not belong to the
   flow, repeated steps, and ordering pairs that the flow fixes -- proof
   pressure before anything is performance tested, a leak test after every
   pressure application, and the destructive burst last.
3. Tolerances: the tolerance a facility applies to a set parameter is graded
   against the allowable band for that quantity, absolute or relative
   depending on the quantity.
4. Measurement accuracy: the instrumentation accuracy declared for a quantity
   is graded against the required accuracy, and separately against the
   applied tolerance band -- an instrument no finer than the band it is
   policing cannot show the parameter stayed inside it.
"""

import math

__all__ = [
    "TOLERANCE_EPSILON",
    "EQUIPMENT_TYPES",
    "MODEL_PHILOSOPHIES",
    "MINIMUM_UNITS",
    "REQUIRED_STEPS",
    "SEQUENCE_PRECEDENCE",
    "ALLOWABLE_TOLERANCE",
    "REQUIRED_ACCURACY",
    "ACCURACY_TO_TOLERANCE_RATIO",
    "validate_equipment_type",
    "validate_model_philosophy",
    "minimum_unit_count",
    "assess_unit_count",
    "assess_sequence",
    "tolerance_band",
    "resolve_limit",
    "assess_applied_tolerance",
    "assess_measurement_accuracy",
    "assess_test_programme",
]

# Tolerance and accuracy grades are float comparisons a correct programme can
# land exactly on. Absorb the representation error, never the requirement.
TOLERANCE_EPSILON = 1e-12

EQUIPMENT_TYPES = ("heat-pipe", "capillary-driven-loop")

MODEL_PHILOSOPHIES = ("qualification-model", "protoflight-model")

# Minimum number of test articles the programme owes. A dedicated
# qualification model is tested to destruction, so more units are needed than
# under a protoflight approach where the flight article carries the campaign.
MINIMUM_UNITS = {
    ("heat-pipe", "qualification-model"): 3,
    ("heat-pipe", "protoflight-model"): 2,
    ("capillary-driven-loop", "qualification-model"): 2,
    ("capillary-driven-loop", "protoflight-model"): 1,
}

# The ordered flow per equipment type. A capillary driven loop adds the
# start-up and set-point regulation steps a fixed-conductance heat pipe has
# no equivalent of.
REQUIRED_STEPS = {
    "heat-pipe": (
        "proof-pressure",
        "leak",
        "thermal-performance",
        "thermal-cycling",
        "vibration",
        "pressure-cycle",
        "burst",
    ),
    "capillary-driven-loop": (
        "proof-pressure",
        "leak",
        "start-up",
        "thermal-performance",
        "regulation",
        "thermal-cycling",
        "vibration",
        "pressure-cycle",
        "burst",
    ),
}

# Ordering pairs the flow fixes: (earlier, later).
SEQUENCE_PRECEDENCE = {
    "heat-pipe": (
        ("proof-pressure", "leak"),
        ("leak", "thermal-performance"),
        ("thermal-performance", "thermal-cycling"),
        ("thermal-cycling", "vibration"),
        ("vibration", "pressure-cycle"),
        ("pressure-cycle", "burst"),
    ),
    "capillary-driven-loop": (
        ("proof-pressure", "leak"),
        ("leak", "start-up"),
        ("start-up", "thermal-performance"),
        ("thermal-performance", "regulation"),
        ("regulation", "thermal-cycling"),
        ("thermal-cycling", "vibration"),
        ("vibration", "pressure-cycle"),
        ("pressure-cycle", "burst"),
    ),
}

# Allowable tolerance on an applied (set) test parameter, as
# (kind, value) with kind in {"absolute", "relative"}.
ALLOWABLE_TOLERANCE = {
    "temperature_k": ("absolute", 2.0),
    "heat_load_w": ("relative", 0.02),
    "pressure_pa": ("relative", 0.02),
    "elevation_m": ("absolute", 0.001),
    "duration_s": ("relative", 0.05),
    "mass_flow_kg_per_s": ("relative", 0.03),
}

# Required instrumentation accuracy per measured quantity, same encoding.
REQUIRED_ACCURACY = {
    "temperature_k": ("absolute", 0.5),
    "heat_load_w": ("relative", 0.01),
    "pressure_pa": ("relative", 0.01),
    "elevation_m": ("absolute", 0.0005),
    "duration_s": ("relative", 0.01),
    "mass_flow_kg_per_s": ("relative", 0.02),
}

# An instrument has to be this much finer than the tolerance band it polices
# before a reading inside the band is evidence rather than noise.
ACCURACY_TO_TOLERANCE_RATIO = 3.0


def _require_real(label, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _require_positive(label, value):
    out = _require_real(label, value)
    if out <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return out


def _require_non_negative(label, value):
    out = _require_real(label, value)
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %r" % (label, value))
    return out


def _within(value, limit):
    """True when value <= limit, absorbing float representation error."""
    return value < limit or math.isclose(value, limit, rel_tol=1e-12,
                                         abs_tol=TOLERANCE_EPSILON)


def validate_equipment_type(equipment_type):
    """Return the normalised equipment type or raise ValueError."""
    if not isinstance(equipment_type, str) or not equipment_type.strip():
        raise ValueError("equipment_type must be a non-empty string")
    name = equipment_type.strip().lower()
    if name not in EQUIPMENT_TYPES:
        raise ValueError("unknown equipment_type %r; expected one of %s"
                         % (equipment_type, ", ".join(EQUIPMENT_TYPES)))
    return name


def validate_model_philosophy(model_philosophy):
    """Return the normalised model philosophy or raise ValueError."""
    if not isinstance(model_philosophy, str) or not model_philosophy.strip():
        raise ValueError("model_philosophy must be a non-empty string")
    name = model_philosophy.strip().lower()
    if name not in MODEL_PHILOSOPHIES:
        raise ValueError("unknown model_philosophy %r; expected one of %s"
                         % (model_philosophy, ", ".join(MODEL_PHILOSOPHIES)))
    return name


def minimum_unit_count(equipment_type, model_philosophy, overrides=None):
    """Return the minimum number of test articles the programme owes."""
    equipment = validate_equipment_type(equipment_type)
    philosophy = validate_model_philosophy(model_philosophy)
    key = (equipment, philosophy)
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise ValueError("overrides must be a mapping of (type, philosophy) to a count")
        if key in overrides:
            value = overrides[key]
            if isinstance(value, bool) or not isinstance(value, int):
                raise ValueError("override unit count must be an integer, got %r" % (value,))
            if value < 1:
                raise ValueError("override unit count must be at least 1, got %d" % value)
            return value
    return MINIMUM_UNITS[key]


def assess_unit_count(declared_units, equipment_type, model_philosophy, overrides=None):
    """Grade the declared number of test articles against the minimum."""
    if isinstance(declared_units, bool) or not isinstance(declared_units, int):
        raise ValueError("declared_units must be an integer, got %r" % (declared_units,))
    if declared_units < 0:
        raise ValueError("declared_units must be non-negative, got %d" % declared_units)
    required = minimum_unit_count(equipment_type, model_philosophy, overrides)
    compliant = declared_units >= required
    findings = []
    if not compliant:
        findings.append("test programme declares %d unit(s); %d required for a %s %s"
                        % (declared_units, required,
                           validate_model_philosophy(model_philosophy),
                           validate_equipment_type(equipment_type)))
    return {
        "declared_units": declared_units,
        "required_units": required,
        "shortfall": max(0, required - declared_units),
        "compliant": compliant,
        "findings": findings,
    }


def assess_sequence(equipment_type, declared_sequence):
    """Grade a declared test sequence against the flow for the equipment type."""
    equipment = validate_equipment_type(equipment_type)
    if not isinstance(declared_sequence, (list, tuple)) or not declared_sequence:
        raise ValueError("declared_sequence must be a non-empty sequence of step names")
    steps = []
    for index, item in enumerate(declared_sequence):
        if not isinstance(item, str) or not item.strip():
            raise ValueError("declared_sequence[%d] must be a non-empty string" % index)
        steps.append(item.strip().lower())
    required = REQUIRED_STEPS[equipment]
    position = {}
    repeated = []
    for index, step in enumerate(steps):
        if step in position:
            if step not in repeated:
                repeated.append(step)
        else:
            position[step] = index
    missing = [step for step in required if step not in position]
    unknown = [step for step in steps if step not in required]
    seen_unknown = []
    for step in unknown:
        if step not in seen_unknown:
            seen_unknown.append(step)
    violations = []
    for earlier, later in SEQUENCE_PRECEDENCE[equipment]:
        if earlier in position and later in position:
            if position[earlier] > position[later]:
                violations.append((earlier, later))
    findings = []
    if missing:
        findings.append("sequence omits required step(s): %s" % ", ".join(missing))
    if seen_unknown:
        findings.append("sequence contains step(s) outside the %s flow: %s"
                        % (equipment, ", ".join(seen_unknown)))
    if repeated:
        findings.append("sequence repeats step(s): %s" % ", ".join(repeated))
    for earlier, later in violations:
        findings.append("'%s' must precede '%s'" % (earlier, later))
    return {
        "equipment_type": equipment,
        "steps": steps,
        "missing_steps": missing,
        "unknown_steps": seen_unknown,
        "repeated_steps": repeated,
        "precedence_violations": violations,
        "compliant": not findings,
        "findings": findings,
    }


def resolve_limit(quantity, table, label):
    """Return the (kind, value) limit pair for a quantity from a table."""
    if not isinstance(quantity, str) or not quantity.strip():
        raise ValueError("quantity must be a non-empty string")
    name = quantity.strip().lower()
    if name not in table:
        raise ValueError("no %s limit tabulated for quantity %r" % (label, quantity))
    return name, table[name]


def tolerance_band(nominal, kind, value):
    """Return the (low, high) band a set parameter is allowed to sit in."""
    if kind not in ("absolute", "relative"):
        raise ValueError("tolerance kind must be 'absolute' or 'relative', got %r" % (kind,))
    target = _require_real("nominal", nominal)
    width = _require_non_negative("tolerance value", value)
    if kind == "relative":
        half = abs(target) * width
    else:
        half = width
    return (target - half, target + half)


def _as_absolute(kind, value, nominal):
    """Convert a (kind, value) limit into an absolute half-width."""
    if kind not in ("absolute", "relative"):
        raise ValueError("limit kind must be 'absolute' or 'relative', got %r" % (kind,))
    width = _require_non_negative("limit value", value)
    if kind == "relative":
        return abs(_require_real("nominal", nominal)) * width
    return width


def assess_applied_tolerance(quantity, nominal, applied_kind, applied_value,
                             allowable=None):
    """Grade the tolerance a facility applies to a set parameter."""
    table = ALLOWABLE_TOLERANCE if allowable is None else allowable
    name, (limit_kind, limit_value) = resolve_limit(quantity, table, "tolerance")
    target = _require_real("nominal", nominal)
    applied_abs = _as_absolute(applied_kind, applied_value, target)
    allowed_abs = _as_absolute(limit_kind, limit_value, target)
    compliant = _within(applied_abs, allowed_abs)
    findings = []
    if not compliant:
        findings.append("applied tolerance on %s is +/-%g, wider than the allowable +/-%g"
                        % (name, applied_abs, allowed_abs))
    low, high = tolerance_band(target, applied_kind, applied_value)
    return {
        "quantity": name,
        "nominal": target,
        "applied_half_width": applied_abs,
        "allowable_half_width": allowed_abs,
        "band": (low, high),
        "compliant": compliant,
        "findings": findings,
    }


def assess_measurement_accuracy(quantity, nominal, declared_kind, declared_value,
                                applied_half_width=None, required=None):
    """Grade instrumentation accuracy against the requirement and the band."""
    table = REQUIRED_ACCURACY if required is None else required
    name, (limit_kind, limit_value) = resolve_limit(quantity, table, "accuracy")
    target = _require_real("nominal", nominal)
    declared_abs = _as_absolute(declared_kind, declared_value, target)
    required_abs = _as_absolute(limit_kind, limit_value, target)
    meets_requirement = _within(declared_abs, required_abs)
    findings = []
    if not meets_requirement:
        findings.append("declared accuracy on %s is +/-%g, coarser than the required +/-%g"
                        % (name, declared_abs, required_abs))
    resolves_band = True
    if applied_half_width is not None:
        band_half = _require_positive("applied_half_width", applied_half_width)
        resolves_band = _within(declared_abs * ACCURACY_TO_TOLERANCE_RATIO, band_half)
        if not resolves_band:
            findings.append(
                "accuracy +/-%g on %s cannot police a +/-%g band at the %gx resolution rule"
                % (declared_abs, name, band_half, ACCURACY_TO_TOLERANCE_RATIO)
            )
    return {
        "quantity": name,
        "declared_half_width": declared_abs,
        "required_half_width": required_abs,
        "meets_requirement": meets_requirement,
        "resolves_band": resolves_band,
        "compliant": meets_requirement and resolves_band,
        "findings": findings,
    }


def assess_test_programme(spec):
    """Run the whole clause 5.6.1 to 5.6.4 test-programme assessment.

    spec keys: equipment_type, model_philosophy, declared_units, sequence,
    parameters (a list of mappings with quantity, nominal, tolerance_kind,
    tolerance_value, accuracy_kind, accuracy_value), optional unit_overrides.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("equipment_type", "model_philosophy", "declared_units",
                "sequence", "parameters"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    units = assess_unit_count(
        spec["declared_units"], spec["equipment_type"], spec["model_philosophy"],
        spec.get("unit_overrides"),
    )
    sequence = assess_sequence(spec["equipment_type"], spec["sequence"])
    parameters = spec["parameters"]
    if not isinstance(parameters, (list, tuple)) or not parameters:
        raise ValueError("spec['parameters'] must be a non-empty sequence of mappings")
    tolerance_results = []
    accuracy_results = []
    seen = []
    for index, item in enumerate(parameters):
        if not isinstance(item, dict):
            raise ValueError("parameters[%d] must be a mapping" % index)
        for key in ("quantity", "nominal", "tolerance_kind", "tolerance_value",
                    "accuracy_kind", "accuracy_value"):
            if key not in item:
                raise ValueError("parameters[%d] missing key '%s'" % (index, key))
        tol = assess_applied_tolerance(
            item["quantity"], item["nominal"],
            item["tolerance_kind"], item["tolerance_value"],
            spec.get("allowable_tolerance"),
        )
        if tol["quantity"] in seen:
            raise ValueError("parameters repeat the quantity %r" % tol["quantity"])
        seen.append(tol["quantity"])
        acc = assess_measurement_accuracy(
            item["quantity"], item["nominal"],
            item["accuracy_kind"], item["accuracy_value"],
            tol["applied_half_width"] if tol["applied_half_width"] > 0.0 else None,
            spec.get("required_accuracy"),
        )
        tolerance_results.append(tol)
        accuracy_results.append(acc)
    findings = []
    for item in units["findings"]:
        findings.append("units: %s" % item)
    for item in sequence["findings"]:
        findings.append("sequence: %s" % item)
    for result in tolerance_results:
        for item in result["findings"]:
            findings.append("tolerance: %s" % item)
    for result in accuracy_results:
        for item in result["findings"]:
            findings.append("accuracy: %s" % item)
    compliant = (
        units["compliant"]
        and sequence["compliant"]
        and all(r["compliant"] for r in tolerance_results)
        and all(r["compliant"] for r in accuracy_results)
    )
    return {
        "units": units,
        "sequence": sequence,
        "tolerances": tolerance_results,
        "accuracies": accuracy_results,
        "findings": findings,
        "compliant": compliant,
    }
