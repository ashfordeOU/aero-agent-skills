#!/usr/bin/env python3
"""Designing, choosing, buying and running a class 3 monolithic microwave part.

Anchor: ECSS-Q-ST-60C clause 6.6.5 (design, choice, purchase and use of
microwave monolithic integrated circuits in class 3 equipment). Paraphrased
into an implementable procedure; no standard text is reproduced.

The clause spans four phases and a part has to survive all four. A design with
no gain margin cannot be rescued by a good purchase; a well-chosen part with
no lot traceability is not a class 3 part; and a faultlessly procured device
run into a mismatched load is overstressed whatever its paperwork says. The
phases are graded in order, and the first one that stops the part is the
answer, because fixing a later phase while an earlier one is open changes
nothing.

Procedure implemented here
--------------------------
1. Design. Take the gain margin the stage leaves over what the function needs
   and test it against the floor.
2. Choice. Grade the screening pedigree against the weakest one class 3 admits
   and assemble the compensating evidence anything below the top rung obliges.
3. Purchase. Check the traceability record the lot arrived with is complete.
4. Use. Turn the load standing wave ratio into a reflection magnitude, take
   the voltage stress factor it puts on the output stage, feed the reflected
   power back into the dissipation, resolve the junction temperature across
   the die and interface path and take its margin against the class 3 limit.
5. Return the first phase that stops the part, or admissibility with the
   compensating evidence the choice obliged.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "PHASES",
    "MMIC_FUNCTIONS",
    "FUNCTION_GAIN_MARGIN_FLOOR_DB",
    "SCREENING_PEDIGREES",
    "PEDIGREE_RANK",
    "WEAKEST_CLASS_3_PEDIGREE",
    "UNKNOWN_PEDIGREE",
    "PEDIGREE_EVIDENCE",
    "DELIVERY_FORMS",
    "DELIVERY_FORM_EVIDENCE",
    "REQUIRED_TRACEABILITY_FIELDS",
    "DEFAULT_CLASS3_MMIC_POLICY",
    "TOLERANCE",
    "ADMISSIBLE_AT_CLASS_3",
    "DESIGN_GAIN_MARGIN_SHORT",
    "CHOICE_PEDIGREE_NOT_ADMISSIBLE",
    "PURCHASE_TRACEABILITY_INCOMPLETE",
    "USE_JUNCTION_TEMPERATURE_OVER_LIMIT",
    "USE_LOAD_MISMATCH_OVERSTRESS",
    "pedigree_rank",
    "meets_floor",
    "validate_class3_mmic_policy",
    "validate_class3_mmic_case",
    "gain_margin_db",
    "reflection_magnitude",
    "mismatch_stress_factor",
    "delivered_power_w",
    "dissipated_power_w",
    "junction_temperature_c",
    "junction_margin_c",
    "compensating_evidence",
    "design_findings",
    "choice_findings",
    "purchase_findings",
    "use_findings",
    "phase_findings",
    "first_blocking_phase",
    "assess_class3_mmic",
]

PHASES = ("design", "choice", "purchase", "use")

MMIC_FUNCTIONS = (
    "low-noise-amplifier",
    "power-amplifier",
    "frequency-converter",
    "switch-matrix",
)

# Gain margin in decibels the stage has to leave over what the chain asks for,
# by the job the part is doing. A power stage is held to more because its gain
# moves most with temperature and drive.
FUNCTION_GAIN_MARGIN_FLOOR_DB = {
    "low-noise-amplifier": 1.5,
    "power-amplifier": 3.0,
    "frequency-converter": 2.0,
    "switch-matrix": 1.0,
}

# Strongest first.
SCREENING_PEDIGREES = (
    "space-evaluated",
    "space-qualified-equivalent",
    "automotive-grade",
    "commercial-catalogue",
    "unknown-pedigree",
)

PEDIGREE_RANK = {name: index + 1 for index, name in enumerate(SCREENING_PEDIGREES)}

# Class 3 reaches down to a catalogue part. It does not reach a part whose
# screening history nobody can state, because there is nothing to compensate.
WEAKEST_CLASS_3_PEDIGREE = "commercial-catalogue"
UNKNOWN_PEDIGREE = "unknown-pedigree"

# What each pedigree obliges the project to produce for itself.
PEDIGREE_EVIDENCE = {
    "space-evaluated": (),
    "space-qualified-equivalent": ("equivalence-justification",),
    "automotive-grade": (
        "equivalence-justification",
        "radiation-evaluation",
        "lot-acceptance-testing",
    ),
    "commercial-catalogue": (
        "supplier-survey",
        "equivalence-justification",
        "radiation-evaluation",
        "lot-acceptance-testing",
        "upscreening-programme",
    ),
}

DELIVERY_FORMS = ("hermetic-package", "plastic-encapsulated", "bare-die")

DELIVERY_FORM_EVIDENCE = {
    "hermetic-package": (),
    "plastic-encapsulated": ("moisture-sensitivity-control",),
    "bare-die": ("die-attach-qualification", "assembly-hermeticity-control"),
}

REQUIRED_TRACEABILITY_FIELDS = (
    "lot_date_code",
    "lot_traceability_reference",
    "procurement_specification",
)

DEFAULT_CLASS3_MMIC_POLICY = {
    # Junction temperature a class 3 monolithic part is derated to.
    "junction_temperature_limit_c": 150.0,
    # Voltage stress factor the output stage may see from a mismatched load.
    "mismatch_stress_cap": 2.0,
}

# Every use-phase number here is computed, and a case sitting exactly on a
# limit is a real case, so the comparisons carry a tolerance rather than
# trusting the last place of a float on one platform.
TOLERANCE = 1e-9

ADMISSIBLE_AT_CLASS_3 = "mmic-admissible-at-class-3"
DESIGN_GAIN_MARGIN_SHORT = "design-gain-margin-short"
CHOICE_PEDIGREE_NOT_ADMISSIBLE = "choice-screening-pedigree-not-admissible"
PURCHASE_TRACEABILITY_INCOMPLETE = "purchase-lot-traceability-incomplete"
USE_JUNCTION_TEMPERATURE_OVER_LIMIT = "use-junction-temperature-over-limit"
USE_LOAD_MISMATCH_OVERSTRESS = "use-load-mismatch-overstress"


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _require_positive(label, value):
    if not _is_number(value) or value <= 0:
        raise ValueError("%s must be a positive number, got %r" % (label, value))
    return float(value)


def _require_non_negative(label, value):
    if not _is_number(value) or value < 0:
        raise ValueError("%s must be a non-negative number, got %r" % (label, value))
    return float(value)


def meets_floor(value, floor):
    """Whether a computed value reaches its floor, tolerant in the last place."""
    if not _is_number(value) or not _is_number(floor):
        raise ValueError("value and floor must be numbers, got %r and %r" % (value, floor))
    return value >= floor - TOLERANCE


def pedigree_rank(pedigree):
    """Position of a screening pedigree on the ladder; 1 is the strongest."""
    if pedigree not in PEDIGREE_RANK:
        raise ValueError(
            "unknown screening pedigree %r (known: %s)"
            % (pedigree, ", ".join(SCREENING_PEDIGREES))
        )
    return PEDIGREE_RANK[pedigree]


def validate_class3_mmic_policy(policy=None):
    """Validate the class 3 policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_CLASS3_MMIC_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_CLASS3_MMIC_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_CLASS3_MMIC_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    _require_positive("junction_temperature_limit_c", merged["junction_temperature_limit_c"])
    cap = merged["mismatch_stress_cap"]
    if not _is_number(cap) or cap < 1.0:
        raise ValueError(
            "mismatch_stress_cap must be at least 1.0, got %r" % (cap,)
        )
    return merged


def validate_class3_mmic_case(case):
    """Validate one class 3 monolithic microwave case across all four phases."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (type(case).__name__,))
    _require_text("part_number", case.get("part_number"))
    function = case.get("function")
    if function not in FUNCTION_GAIN_MARGIN_FLOOR_DB:
        raise ValueError(
            "unknown function %r (known: %s)" % (function, ", ".join(MMIC_FUNCTIONS))
        )
    pedigree = case.get("screening_pedigree")
    pedigree_rank(pedigree)
    form = case.get("delivery_form")
    if form not in DELIVERY_FORM_EVIDENCE:
        raise ValueError(
            "unknown delivery form %r (known: %s)" % (form, ", ".join(DELIVERY_FORMS))
        )
    available = _require_non_negative("available_gain_db", case.get("available_gain_db"))
    required = _require_non_negative("required_gain_db", case.get("required_gain_db"))
    rated_output = _require_positive(
        "rated_output_power_w", case.get("rated_output_power_w")
    )
    nominal_output = _require_positive(
        "nominal_output_power_w", case.get("nominal_output_power_w")
    )
    if nominal_output > rated_output:
        raise ValueError(
            "nominal_output_power_w %r is above rated_output_power_w %r"
            % (nominal_output, rated_output)
        )
    dc_input = _require_positive("dc_input_power_w", case.get("dc_input_power_w"))
    if dc_input < nominal_output:
        raise ValueError(
            "dc_input_power_w %r is below nominal_output_power_w %r"
            % (dc_input, nominal_output)
        )
    vswr = case.get("load_vswr")
    if not _is_number(vswr) or vswr < 1.0:
        raise ValueError("load_vswr must be at least 1.0, got %r" % (vswr,))
    baseplate = case.get("baseplate_temperature_c")
    if not _is_number(baseplate):
        raise ValueError(
            "baseplate_temperature_c must be a number, got %r" % (baseplate,)
        )
    rth_jc = _require_positive(
        "thermal_resistance_junction_case_c_per_w",
        case.get("thermal_resistance_junction_case_c_per_w"),
    )
    rth_cb = _require_non_negative(
        "thermal_resistance_case_baseplate_c_per_w",
        case.get("thermal_resistance_case_baseplate_c_per_w"),
    )
    traceability = case.get("traceability", {})
    if not isinstance(traceability, dict):
        raise ValueError(
            "traceability must be a mapping, got %r" % (type(traceability).__name__,)
        )
    cleaned = {}
    for field in REQUIRED_TRACEABILITY_FIELDS:
        value = traceability.get(field)
        if value is not None and not isinstance(value, str):
            raise ValueError("%s must be a string or None, got %r" % (field, value))
        cleaned[field] = value.strip() or None if isinstance(value, str) else None
    return {
        "part_number": case["part_number"],
        "function": function,
        "screening_pedigree": pedigree,
        "delivery_form": form,
        "available_gain_db": available,
        "required_gain_db": required,
        "rated_output_power_w": rated_output,
        "nominal_output_power_w": nominal_output,
        "dc_input_power_w": dc_input,
        "load_vswr": float(vswr),
        "baseplate_temperature_c": float(baseplate),
        "thermal_resistance_junction_case_c_per_w": rth_jc,
        "thermal_resistance_case_baseplate_c_per_w": rth_cb,
        "traceability": cleaned,
    }


def gain_margin_db(case):
    """Decibels of gain the stage leaves over what the chain asked for."""
    validated = validate_class3_mmic_case(case)
    return validated["available_gain_db"] - validated["required_gain_db"]


def reflection_magnitude(vswr):
    """Magnitude of the reflection the load standing wave ratio implies."""
    if not _is_number(vswr) or vswr < 1.0:
        raise ValueError("load_vswr must be at least 1.0, got %r" % (vswr,))
    return (float(vswr) - 1.0) / (float(vswr) + 1.0)


def mismatch_stress_factor(vswr):
    """Voltage stress the reflected wave puts on the output stage, squared."""
    magnitude = reflection_magnitude(vswr)
    return (1.0 + magnitude) ** 2


def delivered_power_w(nominal_output_power_w, vswr):
    """Power that actually reaches the load once the reflection is taken off."""
    nominal = _require_positive("nominal_output_power_w", nominal_output_power_w)
    magnitude = reflection_magnitude(vswr)
    return nominal * (1.0 - magnitude * magnitude)


def dissipated_power_w(case):
    """Power the die has to get rid of, with the reflected power added back."""
    validated = validate_class3_mmic_case(case)
    delivered = delivered_power_w(
        validated["nominal_output_power_w"], validated["load_vswr"]
    )
    return validated["dc_input_power_w"] - delivered


def junction_temperature_c(case):
    """Junction temperature across the die and interface thermal path."""
    validated = validate_class3_mmic_case(case)
    path = (
        validated["thermal_resistance_junction_case_c_per_w"]
        + validated["thermal_resistance_case_baseplate_c_per_w"]
    )
    return validated["baseplate_temperature_c"] + dissipated_power_w(validated) * path


def junction_margin_c(case, policy=None):
    """Degrees left between the junction temperature and the class 3 limit."""
    merged = validate_class3_mmic_policy(policy)
    return merged["junction_temperature_limit_c"] - junction_temperature_c(case)


def compensating_evidence(case):
    """Evidence the chosen pedigree and delivery form oblige the project to make."""
    validated = validate_class3_mmic_case(case)
    pedigree = validated["screening_pedigree"]
    evidence = list(PEDIGREE_EVIDENCE.get(pedigree, ()))
    for item in DELIVERY_FORM_EVIDENCE[validated["delivery_form"]]:
        if item not in evidence:
            evidence.append(item)
    return tuple(evidence)


def design_findings(case, policy=None):
    """Phase one: does the stage leave the gain margin its function demands."""
    validated = validate_class3_mmic_case(case)
    floor = FUNCTION_GAIN_MARGIN_FLOOR_DB[validated["function"]]
    margin = gain_margin_db(validated)
    if not meets_floor(margin, floor):
        return (
            {
                "phase": "design",
                "finding": DESIGN_GAIN_MARGIN_SHORT,
                "required": floor,
                "measured": margin,
            },
        )
    return ()


def choice_findings(case, policy=None):
    """Phase two: is the screening pedigree one class 3 can actually admit."""
    validated = validate_class3_mmic_case(case)
    pedigree = validated["screening_pedigree"]
    if pedigree_rank(pedigree) > pedigree_rank(WEAKEST_CLASS_3_PEDIGREE):
        return (
            {
                "phase": "choice",
                "finding": CHOICE_PEDIGREE_NOT_ADMISSIBLE,
                "required": WEAKEST_CLASS_3_PEDIGREE,
                "measured": pedigree,
            },
        )
    return ()


def purchase_findings(case, policy=None):
    """Phase three: did the lot arrive with a traceability record."""
    validated = validate_class3_mmic_case(case)
    missing = [
        field
        for field in REQUIRED_TRACEABILITY_FIELDS
        if not validated["traceability"].get(field)
    ]
    if missing:
        return (
            {
                "phase": "purchase",
                "finding": PURCHASE_TRACEABILITY_INCOMPLETE,
                "required": ", ".join(REQUIRED_TRACEABILITY_FIELDS),
                "measured": ", ".join(missing),
            },
        )
    return ()


def use_findings(case, policy=None):
    """Phase four: does the application run the part inside its limits."""
    merged = validate_class3_mmic_policy(policy)
    validated = validate_class3_mmic_case(case)
    findings = []
    stress = mismatch_stress_factor(validated["load_vswr"])
    if stress > merged["mismatch_stress_cap"] + TOLERANCE:
        findings.append(
            {
                "phase": "use",
                "finding": USE_LOAD_MISMATCH_OVERSTRESS,
                "required": merged["mismatch_stress_cap"],
                "measured": stress,
            }
        )
    margin = junction_margin_c(validated, merged)
    if not meets_floor(margin, 0.0):
        findings.append(
            {
                "phase": "use",
                "finding": USE_JUNCTION_TEMPERATURE_OVER_LIMIT,
                "required": merged["junction_temperature_limit_c"],
                "measured": junction_temperature_c(validated),
            }
        )
    return tuple(findings)


def phase_findings(case, policy=None):
    """Every phase's findings, keyed by phase, in clause order."""
    validated = validate_class3_mmic_case(case)
    return {
        "design": design_findings(validated, policy),
        "choice": choice_findings(validated, policy),
        "purchase": purchase_findings(validated, policy),
        "use": use_findings(validated, policy),
    }


def first_blocking_phase(case, policy=None):
    """The earliest phase that stops the part, or None when all four are clear."""
    by_phase = phase_findings(case, policy)
    for phase in PHASES:
        if by_phase[phase]:
            return phase
    return None


def assess_class3_mmic(case, policy=None):
    """Grade a class 3 monolithic microwave part across all four phases."""
    merged = validate_class3_mmic_policy(policy)
    validated = validate_class3_mmic_case(case)
    by_phase = phase_findings(validated, merged)
    findings = []
    for phase in PHASES:
        findings.extend(by_phase[phase])
    blocking = first_blocking_phase(validated, merged)
    verdict = ADMISSIBLE_AT_CLASS_3 if blocking is None else by_phase[blocking][0]["finding"]
    return {
        "verdict": verdict,
        "part_number": validated["part_number"],
        "function": validated["function"],
        "blocking_phase": blocking,
        "gain_margin_db": gain_margin_db(validated),
        "gain_margin_floor_db": FUNCTION_GAIN_MARGIN_FLOOR_DB[validated["function"]],
        "reflection_magnitude": reflection_magnitude(validated["load_vswr"]),
        "mismatch_stress_factor": mismatch_stress_factor(validated["load_vswr"]),
        "delivered_power_w": delivered_power_w(
            validated["nominal_output_power_w"], validated["load_vswr"]
        ),
        "dissipated_power_w": dissipated_power_w(validated),
        "junction_temperature_c": junction_temperature_c(validated),
        "junction_margin_c": junction_margin_c(validated, merged),
        "compensating_evidence": compensating_evidence(validated),
        "phase_findings": by_phase,
        "findings": findings,
        "admissible": verdict == ADMISSIBLE_AT_CLASS_3,
    }
