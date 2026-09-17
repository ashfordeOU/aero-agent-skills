#!/usr/bin/env python3
"""Developing, reusing and maintaining a programmable logic device at class 3.

Anchor: ECSS-Q-ST-60C clause 6.6.4 (development, reuse and maintenance rules
for programmable logic devices used in class 3 equipment). Paraphrased into an
implementable procedure; no standard text is reproduced.

A programmable logic device is bought as a component and flown as a design.
Class 3 allows the verification set behind that design to be reduced, but not
uniformly: the reduction is read off the function the logic performs and the
technology that holds the configuration, and what remains has floors that a
measured coverage number either reaches or does not. Maintenance is the third
term — the design data has to outlive the equipment, and a device that can be
reprogrammed in the field has to say who may do it.

Procedure implemented here
--------------------------
1. Assemble the verification objectives this design owes: the class 3 base
   set, what the function criticality adds, and what the configuration
   technology adds on top of both.
2. Compare the objectives actually performed against that set.
3. Read the coverage floors the criticality sets and measure functional and
   statement coverage against them.
4. Compute the timing margin from the required and achieved clock periods and
   test it against its floor.
5. Test the single event mitigation declaration where the criticality and the
   technology demand one.
6. Check the design data retention covers the mission plus the margin the
   policy keeps after it, and that a reprogrammable device names its
   reprogramming control.
7. Route the design and return one verdict naming the first thing that stops
   the programme.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

__all__ = [
    "FUNCTION_CRITICALITIES",
    "CONFIGURATION_TECHNOLOGIES",
    "REPROGRAMMABLE_TECHNOLOGIES",
    "VERIFICATION_OBJECTIVES",
    "BASE_OBJECTIVES",
    "CRITICALITY_EXTRA_OBJECTIVES",
    "TECHNOLOGY_EXTRA_OBJECTIVES",
    "COVERAGE_FLOORS",
    "TIMING_MARGIN_FLOOR",
    "MITIGATION_REQUIRED_CRITICALITIES",
    "DEFAULT_VERIFICATION_POLICY",
    "TOLERANCE",
    "FULL_DEVELOPMENT",
    "DELTA_VERIFICATION",
    "REVIEWED_REUSE",
    "PROGRAMME_ACCEPTED",
    "OBJECTIVE_NOT_PERFORMED",
    "COVERAGE_BELOW_FLOOR",
    "TIMING_MARGIN_BELOW_FLOOR",
    "MITIGATION_NOT_DECLARED",
    "DESIGN_DATA_RETENTION_SHORT",
    "REPROGRAMMING_CONTROL_MISSING",
    "validate_verification_policy",
    "validate_design_record",
    "meets_floor",
    "required_objectives",
    "coverage_floors",
    "missing_objectives",
    "coverage_margins",
    "coverage_findings",
    "timing_margin",
    "mitigation_is_required",
    "required_retention_months",
    "retention_findings",
    "route_design",
    "verification_completeness",
    "assess_pld_programme",
]

FUNCTION_CRITICALITIES = (
    "mission-critical",
    "mission-important",
    "non-critical",
)

CONFIGURATION_TECHNOLOGIES = (
    "antifuse-one-time",
    "flash-reprogrammable",
    "volatile-sram-configured",
)

REPROGRAMMABLE_TECHNOLOGIES = (
    "flash-reprogrammable",
    "volatile-sram-configured",
)

VERIFICATION_OBJECTIVES = (
    "requirements-traceability",
    "functional-simulation",
    "statement-coverage-measurement",
    "toggle-coverage-measurement",
    "static-timing-analysis",
    "back-annotated-simulation",
    "independent-design-review",
    "single-event-mitigation-analysis",
    "power-on-configuration-check",
    "configuration-scrubbing-design",
    "reprogramming-control-procedure",
    "programming-yield-record",
)

# What every class 3 programmable logic design owes whatever it does.
BASE_OBJECTIVES = (
    "requirements-traceability",
    "functional-simulation",
    "statement-coverage-measurement",
    "static-timing-analysis",
)

# What the function the logic performs adds on top of the base set.
CRITICALITY_EXTRA_OBJECTIVES = {
    "mission-critical": (
        "toggle-coverage-measurement",
        "back-annotated-simulation",
        "independent-design-review",
        "single-event-mitigation-analysis",
    ),
    "mission-important": (
        "back-annotated-simulation",
        "single-event-mitigation-analysis",
    ),
    "non-critical": (),
}

# What the technology holding the configuration adds, whatever the function is.
TECHNOLOGY_EXTRA_OBJECTIVES = {
    "antifuse-one-time": ("programming-yield-record",),
    "flash-reprogrammable": ("reprogramming-control-procedure",),
    "volatile-sram-configured": (
        "power-on-configuration-check",
        "configuration-scrubbing-design",
        "reprogramming-control-procedure",
    ),
}

# Coverage the class 3 verification has to reach, by function criticality.
COVERAGE_FLOORS = {
    "mission-critical": {"functional": 0.95, "statement": 0.90},
    "mission-important": {"functional": 0.85, "statement": 0.80},
    "non-critical": {"functional": 0.70, "statement": 0.60},
}

# Share of the required clock period that has to be left standing.
TIMING_MARGIN_FLOOR = {
    "mission-critical": 0.20,
    "mission-important": 0.12,
    "non-critical": 0.05,
}

MITIGATION_REQUIRED_CRITICALITIES = ("mission-critical", "mission-important")

DEFAULT_VERIFICATION_POLICY = {
    # Months the design data is kept after the mission ends.
    "post_mission_retention_months": 24,
}

# Coverage and margin values arrive as measurements and are compared with
# floors of the same magnitude. A value sitting on its floor must read as
# meeting it on every platform, so the comparison carries a tolerance rather
# than trusting the last place of a float.
TOLERANCE = 1e-9

FULL_DEVELOPMENT = "full-development-flow"
DELTA_VERIFICATION = "delta-verification-flow"
REVIEWED_REUSE = "reviewed-reuse-flow"

PROGRAMME_ACCEPTED = "class-3-pld-programme-accepted"
OBJECTIVE_NOT_PERFORMED = "verification-objective-not-performed"
COVERAGE_BELOW_FLOOR = "measured-coverage-below-floor"
TIMING_MARGIN_BELOW_FLOOR = "timing-margin-below-floor"
MITIGATION_NOT_DECLARED = "single-event-mitigation-not-declared"
DESIGN_DATA_RETENTION_SHORT = "design-data-retention-short"
REPROGRAMMING_CONTROL_MISSING = "field-reprogramming-control-missing"


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool)


def _is_number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _require_text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (label, value))
    return value


def _require_fraction(label, value):
    if not _is_number(value) or value < 0.0 or value > 1.0:
        raise ValueError("%s must be a fraction between 0 and 1, got %r" % (label, value))
    return float(value)


def meets_floor(value, floor):
    """Whether a measured value reaches its floor, tolerant in the last place."""
    if not _is_number(value) or not _is_number(floor):
        raise ValueError("value and floor must be numbers, got %r and %r" % (value, floor))
    return value >= floor - TOLERANCE


def validate_verification_policy(policy=None):
    """Validate the verification policy, returning the default when omitted."""
    if policy is None:
        return dict(DEFAULT_VERIFICATION_POLICY)
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (type(policy).__name__,))
    merged = dict(DEFAULT_VERIFICATION_POLICY)
    for key, value in policy.items():
        if key not in DEFAULT_VERIFICATION_POLICY:
            raise ValueError("unknown policy key %r" % (key,))
        merged[key] = value
    months = merged["post_mission_retention_months"]
    if not _is_int(months) or months < 0:
        raise ValueError(
            "post_mission_retention_months must be a non-negative integer, got %r"
            % (months,)
        )
    return merged


def validate_design_record(record):
    """Validate one class 3 programmable logic design record."""
    if not isinstance(record, dict):
        raise ValueError("design record must be a mapping, got %r" % (type(record).__name__,))
    _require_text("design_id", record.get("design_id"))
    criticality = record.get("function_criticality")
    if criticality not in COVERAGE_FLOORS:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    technology = record.get("configuration_technology")
    if technology not in TECHNOLOGY_EXTRA_OBJECTIVES:
        raise ValueError(
            "unknown configuration technology %r (known: %s)"
            % (technology, ", ".join(CONFIGURATION_TECHNOLOGIES))
        )
    origin = record.get("design_origin")
    if origin not in ("new-design", "modified-reuse", "unchanged-reuse"):
        raise ValueError(
            "design_origin must be new-design, modified-reuse or unchanged-reuse, got %r"
            % (origin,)
        )
    performed = record.get("objectives_performed")
    if not isinstance(performed, (list, tuple)):
        raise ValueError(
            "objectives_performed must be a list or tuple, got %r"
            % (type(performed).__name__,)
        )
    for name in performed:
        if name not in VERIFICATION_OBJECTIVES:
            raise ValueError(
                "unknown verification objective %r (known: %s)"
                % (name, ", ".join(VERIFICATION_OBJECTIVES))
            )
    functional = _require_fraction(
        "functional_coverage", record.get("functional_coverage")
    )
    statement = _require_fraction(
        "statement_coverage", record.get("statement_coverage")
    )
    for key in ("required_clock_period_ns", "achieved_clock_period_ns"):
        value = record.get(key)
        if not _is_number(value) or value <= 0:
            raise ValueError("%s must be a positive number, got %r" % (key, value))
    mitigation = record.get("mitigation_declared")
    if not isinstance(mitigation, bool):
        raise ValueError("mitigation_declared must be a boolean, got %r" % (mitigation,))
    for key in ("mission_duration_months", "design_data_retention_months"):
        value = record.get(key)
        if not _is_int(value) or value < 0:
            raise ValueError("%s must be a non-negative integer, got %r" % (key, value))
    control = record.get("reprogramming_control_reference")
    if control is not None and not isinstance(control, str):
        raise ValueError(
            "reprogramming_control_reference must be a string or None, got %r" % (control,)
        )
    return {
        "design_id": record["design_id"],
        "function_criticality": criticality,
        "configuration_technology": technology,
        "design_origin": origin,
        "objectives_performed": tuple(performed),
        "functional_coverage": functional,
        "statement_coverage": statement,
        "required_clock_period_ns": float(record["required_clock_period_ns"]),
        "achieved_clock_period_ns": float(record["achieved_clock_period_ns"]),
        "mitigation_declared": mitigation,
        "mission_duration_months": record["mission_duration_months"],
        "design_data_retention_months": record["design_data_retention_months"],
        "reprogramming_control_reference": (
            control.strip() or None if isinstance(control, str) else None
        ),
    }


def required_objectives(criticality, technology):
    """The verification set this design owes, in table order."""
    if criticality not in CRITICALITY_EXTRA_OBJECTIVES:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    if technology not in TECHNOLOGY_EXTRA_OBJECTIVES:
        raise ValueError(
            "unknown configuration technology %r (known: %s)"
            % (technology, ", ".join(CONFIGURATION_TECHNOLOGIES))
        )
    needed = set(BASE_OBJECTIVES)
    needed.update(CRITICALITY_EXTRA_OBJECTIVES[criticality])
    needed.update(TECHNOLOGY_EXTRA_OBJECTIVES[technology])
    return tuple(name for name in VERIFICATION_OBJECTIVES if name in needed)


def coverage_floors(criticality):
    """Functional and statement coverage floors for a function criticality."""
    if criticality not in COVERAGE_FLOORS:
        raise ValueError(
            "unknown function criticality %r (known: %s)"
            % (criticality, ", ".join(FUNCTION_CRITICALITIES))
        )
    return dict(COVERAGE_FLOORS[criticality])


def missing_objectives(record):
    """Required objectives the design record does not claim to have performed."""
    validated = validate_design_record(record)
    performed = set(validated["objectives_performed"])
    return tuple(
        name
        for name in required_objectives(
            validated["function_criticality"], validated["configuration_technology"]
        )
        if name not in performed
    )


def coverage_margins(record):
    """How far the measured coverages sit above or below their floors."""
    validated = validate_design_record(record)
    floors = coverage_floors(validated["function_criticality"])
    return {
        "functional": validated["functional_coverage"] - floors["functional"],
        "statement": validated["statement_coverage"] - floors["statement"],
    }


def coverage_findings(record):
    """Findings raised by a coverage measurement short of its floor."""
    validated = validate_design_record(record)
    floors = coverage_floors(validated["function_criticality"])
    findings = []
    for name, measured in (
        ("functional", validated["functional_coverage"]),
        ("statement", validated["statement_coverage"]),
    ):
        if not meets_floor(measured, floors[name]):
            findings.append(
                {
                    "subject": name,
                    "finding": COVERAGE_BELOW_FLOOR,
                    "required": floors[name],
                    "measured": measured,
                }
            )
    return tuple(findings)


def timing_margin(record):
    """Share of the required clock period left standing after timing closure."""
    validated = validate_design_record(record)
    required = validated["required_clock_period_ns"]
    achieved = validated["achieved_clock_period_ns"]
    return (required - achieved) / required


def mitigation_is_required(criticality, technology):
    """Whether a single event mitigation declaration is owed at all."""
    if criticality not in CRITICALITY_EXTRA_OBJECTIVES:
        raise ValueError("unknown function criticality %r" % (criticality,))
    if technology not in TECHNOLOGY_EXTRA_OBJECTIVES:
        raise ValueError("unknown configuration technology %r" % (technology,))
    if criticality in MITIGATION_REQUIRED_CRITICALITIES:
        return True
    # A volatile part holds its logic in cells that an upset can rewrite, so
    # the question follows the technology even on a non-critical function.
    return technology == "volatile-sram-configured"


def required_retention_months(mission_months, policy=None):
    """Months the design data has to survive: the mission plus the margin."""
    merged = validate_verification_policy(policy)
    if not _is_int(mission_months) or mission_months < 0:
        raise ValueError(
            "mission_months must be a non-negative integer, got %r" % (mission_months,)
        )
    return mission_months + merged["post_mission_retention_months"]


def retention_findings(record, policy=None):
    """Findings on design data retention and field reprogramming control."""
    validated = validate_design_record(record)
    findings = []
    needed = required_retention_months(validated["mission_duration_months"], policy)
    if validated["design_data_retention_months"] < needed:
        findings.append(
            {
                "subject": "design-data-retention",
                "finding": DESIGN_DATA_RETENTION_SHORT,
                "required": needed,
                "measured": validated["design_data_retention_months"],
            }
        )
    if (
        validated["configuration_technology"] in REPROGRAMMABLE_TECHNOLOGIES
        and not validated["reprogramming_control_reference"]
    ):
        findings.append(
            {
                "subject": "reprogramming-control",
                "finding": REPROGRAMMING_CONTROL_MISSING,
                "required": "a named reprogramming control procedure",
                "measured": None,
            }
        )
    return tuple(findings)


def route_design(record):
    """Pick the flow this design enters from its origin and its archive."""
    validated = validate_design_record(record)
    origin = validated["design_origin"]
    if origin == "new-design":
        return {"flow": FULL_DEVELOPMENT, "reason": "design-authored-for-this-build"}
    if origin == "modified-reuse":
        return {"flow": DELTA_VERIFICATION, "reason": "design-changed-since-reference"}
    if missing_objectives(validated):
        return {"flow": DELTA_VERIFICATION, "reason": "verification-set-incomplete"}
    return {"flow": REVIEWED_REUSE, "reason": "verification-set-complete-and-unchanged"}


def verification_completeness(record):
    """Share of the required objectives the design claims to have performed."""
    validated = validate_design_record(record)
    needed = required_objectives(
        validated["function_criticality"], validated["configuration_technology"]
    )
    if not needed:
        return 1.0
    done = len(needed) - len(missing_objectives(validated))
    return done / len(needed)


def assess_pld_programme(case, policy=None):
    """Grade a whole class 3 programmable logic development or reuse case."""
    validated = validate_design_record(case)
    criticality = validated["function_criticality"]
    technology = validated["configuration_technology"]
    findings = []
    for name in missing_objectives(validated):
        findings.append(
            {
                "subject": name,
                "finding": OBJECTIVE_NOT_PERFORMED,
                "required": "performed and recorded",
                "measured": None,
            }
        )
    findings.extend(coverage_findings(validated))
    margin = timing_margin(validated)
    floor = TIMING_MARGIN_FLOOR[criticality]
    if not meets_floor(margin, floor):
        findings.append(
            {
                "subject": "timing-margin",
                "finding": TIMING_MARGIN_BELOW_FLOOR,
                "required": floor,
                "measured": margin,
            }
        )
    if mitigation_is_required(criticality, technology) and not validated[
        "mitigation_declared"
    ]:
        findings.append(
            {
                "subject": "single-event-mitigation",
                "finding": MITIGATION_NOT_DECLARED,
                "required": "a declared mitigation approach",
                "measured": False,
            }
        )
    findings.extend(retention_findings(validated, policy))
    order = (
        OBJECTIVE_NOT_PERFORMED,
        COVERAGE_BELOW_FLOOR,
        TIMING_MARGIN_BELOW_FLOOR,
        MITIGATION_NOT_DECLARED,
        REPROGRAMMING_CONTROL_MISSING,
        DESIGN_DATA_RETENTION_SHORT,
    )
    verdict = PROGRAMME_ACCEPTED
    for name in order:
        if any(item["finding"] == name for item in findings):
            verdict = name
            break
    routing = route_design(validated)
    return {
        "verdict": verdict,
        "design_id": validated["design_id"],
        "flow": routing["flow"],
        "routing_reason": routing["reason"],
        "required_objectives": required_objectives(criticality, technology),
        "missing_objectives": missing_objectives(validated),
        "verification_completeness": verification_completeness(validated),
        "coverage_floors": coverage_floors(criticality),
        "coverage_margins": coverage_margins(validated),
        "timing_margin": margin,
        "timing_margin_floor": floor,
        "mitigation_required": mitigation_is_required(criticality, technology),
        "required_retention_months": required_retention_months(
            validated["mission_duration_months"], policy
        ),
        "findings": findings,
        "acceptable": verdict == PROGRAMME_ACCEPTED,
    }
