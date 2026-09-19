#!/usr/bin/env python3
"""Common property assessment for explosive components.

Anchor: ECSS-E-ST-33-11C clauses 4.11.1 and 4.11.2, common property
table 4-3. The procedure below is a paraphrase into implementable
steps; no standard text is reproduced.

Table 4-3 is the part of the component clauses that does not care what
the device is. An initiator, a cartridge, a detonator and a packaged
charge are built differently and do different jobs, but every one of
them has to survive the same environment, hold the same seal, keep the
same insulation, last the same calendar and stay clear of its own
autoignition temperature. That common set is what this leaf grades,
and the per-kind tables are graded elsewhere.

The properties and the shape of each check:

operating / storage temperature range
    A containment question, not a comparison. The qualified range has
    to extend beyond the mission range by a declared margin at BOTH
    ends, and the two ends are reported separately because a
    qualification that is generous hot and tight cold is the common
    case.

seal leak rate
    An upper limit. Larger is worse.

insulation resistance
    A lower limit, and it is meaningless without the voltage the
    measurement was taken at, so both are required.

service life
    The declared life has to cover storage plus the mission, not the
    mission alone.

autoignition temperature
    A separation, not a limit: the autoignition temperature minus the
    maximum operating temperature has to leave the declared margin.

function time
    An upper limit, and it is the one property a packaged charge does
    not carry on its own -- it inherits the timing of whatever
    initiates it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

COMPONENT_KINDS = ("initiator", "cartridge", "detonator", "packaged-charge")

COMMON_PROPERTIES = (
    "operating-temperature-range",
    "storage-temperature-range",
    "seal-leak-rate",
    "insulation-resistance",
    "service-life",
    "autoignition-temperature",
    "function-time",
)

# A packaged charge has no firing circuit of its own, so function time
# belongs to the initiator that drives it rather than to the charge.
PROPERTY_APPLICABILITY = {
    "initiator": COMMON_PROPERTIES,
    "cartridge": COMMON_PROPERTIES,
    "detonator": COMMON_PROPERTIES,
    "packaged-charge": tuple(p for p in COMMON_PROPERTIES if p != "function-time"),
}

VERDICT_MET = "common-properties-met"
VERDICT_NOT_MET = "common-properties-not-met"

DEFAULT_COMMON_PROPERTY_POLICY = {
    "operating_temperature_margin_k": 10.0,
    "storage_temperature_margin_k": 5.0,
    "max_seal_leak_rate_scc_s": 1.0e-6,
    "min_insulation_resistance_ohm": 2.0e6,
    "min_insulation_test_voltage_v": 500.0,
    "autoignition_margin_k": 50.0,
    "max_function_time_ms": 10.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    value = _require_number(name, value)
    if value <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return value


def _require_non_negative(name, value):
    value = _require_number(name, value)
    if value < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_choice(name, value, allowed):
    if value not in allowed:
        raise ValueError(
            "%s must be one of %s, got %r" % (name, ", ".join(allowed), value)
        )
    return value


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_common_property_policy(policy):
    """Check a common-property policy carries a limit for every check."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_non_negative(
        "operating_temperature_margin_k", policy.get("operating_temperature_margin_k")
    )
    _require_non_negative(
        "storage_temperature_margin_k", policy.get("storage_temperature_margin_k")
    )
    _require_positive(
        "max_seal_leak_rate_scc_s", policy.get("max_seal_leak_rate_scc_s")
    )
    _require_positive(
        "min_insulation_resistance_ohm", policy.get("min_insulation_resistance_ohm")
    )
    _require_positive(
        "min_insulation_test_voltage_v", policy.get("min_insulation_test_voltage_v")
    )
    _require_non_negative("autoignition_margin_k", policy.get("autoignition_margin_k"))
    _require_positive("max_function_time_ms", policy.get("max_function_time_ms"))
    return policy


def applicable_properties(kind):
    """Common properties that apply to one component kind."""
    _require_choice("component kind", kind, COMPONENT_KINDS)
    return PROPERTY_APPLICABILITY[kind]


def assess_temperature_envelope(block, margin_k, label):
    """Grade a qualified temperature range against a required range."""
    if not isinstance(block, dict):
        raise ValueError("%s block must be a mapping, got %r" % (label, block))
    margin = _require_non_negative("%s margin" % label, margin_k)
    qual_low = _require_number("%s qualified_low_c" % label, block.get("qualified_low_c"))
    qual_high = _require_number(
        "%s qualified_high_c" % label, block.get("qualified_high_c")
    )
    req_low = _require_number("%s required_low_c" % label, block.get("required_low_c"))
    req_high = _require_number(
        "%s required_high_c" % label, block.get("required_high_c")
    )
    if qual_high <= qual_low:
        raise ValueError("%s qualified range is inverted or empty" % label)
    if req_high <= req_low:
        raise ValueError("%s required range is inverted or empty" % label)
    low_margin = req_low - qual_low
    high_margin = qual_high - req_high
    findings = []
    if not _at_least(low_margin, margin):
        findings.append(
            "%s cold end: qualification reaches %.4g C against a required "
            "%.4g C, leaving %.4g K of the %.4g K margin"
            % (label, qual_low, req_low, low_margin, margin)
        )
    if not _at_least(high_margin, margin):
        findings.append(
            "%s hot end: qualification reaches %.4g C against a required "
            "%.4g C, leaving %.4g K of the %.4g K margin"
            % (label, qual_high, req_high, high_margin, margin)
        )
    return {
        "property": label,
        "low_margin_k": low_margin,
        "high_margin_k": high_margin,
        "required_margin_k": margin,
        "compliant": not findings,
        "findings": findings,
    }


def assess_seal_leak_rate(leak_rate_scc_s, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Grade a measured seal leak rate against its upper limit."""
    validate_common_property_policy(policy)
    rate = _require_non_negative("leak_rate_scc_s", leak_rate_scc_s)
    limit = policy["max_seal_leak_rate_scc_s"]
    findings = []
    if not _at_most(rate, limit):
        findings.append(
            "seal leak rate %.4g scc/s exceeds the allowed %.4g scc/s"
            % (rate, limit)
        )
    return {
        "property": "seal-leak-rate",
        "leak_rate_scc_s": rate,
        "limit_scc_s": limit,
        "compliant": not findings,
        "findings": findings,
    }


def assess_insulation_resistance(block, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Grade insulation resistance and the voltage it was measured at."""
    validate_common_property_policy(policy)
    if not isinstance(block, dict):
        raise ValueError("insulation block must be a mapping, got %r" % (block,))
    resistance = _require_positive("resistance_ohm", block.get("resistance_ohm"))
    voltage = _require_positive("test_voltage_v", block.get("test_voltage_v"))
    findings = []
    if not _at_least(resistance, policy["min_insulation_resistance_ohm"]):
        findings.append(
            "insulation resistance %.4g ohm is below the required %.4g ohm"
            % (resistance, policy["min_insulation_resistance_ohm"])
        )
    if not _at_least(voltage, policy["min_insulation_test_voltage_v"]):
        findings.append(
            "insulation resistance was measured at %.4g V, below the required "
            "%.4g V, so the figure does not demonstrate the requirement"
            % (voltage, policy["min_insulation_test_voltage_v"])
        )
    return {
        "property": "insulation-resistance",
        "resistance_ohm": resistance,
        "test_voltage_v": voltage,
        "compliant": not findings,
        "findings": findings,
    }


def assess_service_life(block):
    """Check the declared life covers storage plus the mission."""
    if not isinstance(block, dict):
        raise ValueError("service life block must be a mapping, got %r" % (block,))
    declared = _require_positive("declared_life_years", block.get("declared_life_years"))
    storage = _require_non_negative("storage_years", block.get("storage_years"))
    mission = _require_positive("mission_years", block.get("mission_years"))
    needed = storage + mission
    findings = []
    if not _at_least(declared, needed):
        findings.append(
            "declared service life %.4g years does not cover %.4g years of "
            "storage plus %.4g years of mission" % (declared, storage, mission)
        )
    return {
        "property": "service-life",
        "declared_life_years": declared,
        "required_life_years": needed,
        "compliant": not findings,
        "findings": findings,
    }


def assess_autoignition(block, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Check the autoignition temperature stands clear of operation."""
    validate_common_property_policy(policy)
    if not isinstance(block, dict):
        raise ValueError("autoignition block must be a mapping, got %r" % (block,))
    autoignition = _require_number(
        "autoignition_temperature_c", block.get("autoignition_temperature_c")
    )
    max_operating = _require_number(
        "max_operating_temperature_c", block.get("max_operating_temperature_c")
    )
    separation = autoignition - max_operating
    required = policy["autoignition_margin_k"]
    findings = []
    if not _at_least(separation, required):
        findings.append(
            "autoignition at %.4g C stands only %.4g K above the %.4g C "
            "maximum operating temperature, against a required %.4g K"
            % (autoignition, separation, max_operating, required)
        )
    return {
        "property": "autoignition-temperature",
        "separation_k": separation,
        "required_margin_k": required,
        "compliant": not findings,
        "findings": findings,
    }


def assess_function_time(function_time_ms, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Grade the declared function time against its upper limit."""
    validate_common_property_policy(policy)
    value = _require_positive("function_time_ms", function_time_ms)
    limit = policy["max_function_time_ms"]
    findings = []
    if not _at_most(value, limit):
        findings.append(
            "function time %.4g ms exceeds the allowed %.4g ms" % (value, limit)
        )
    return {
        "property": "function-time",
        "function_time_ms": value,
        "limit_ms": limit,
        "compliant": not findings,
        "findings": findings,
    }


def assess_common_properties(component, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Grade one explosive component against every property that applies."""
    validate_common_property_policy(policy)
    if not isinstance(component, dict):
        raise ValueError("component must be a mapping, got %r" % (component,))
    kind = _require_choice("component kind", component.get("kind"), COMPONENT_KINDS)
    properties = component.get("properties")
    if not isinstance(properties, dict):
        raise ValueError("component properties must be a mapping, got %r" % (properties,))
    applicable = applicable_properties(kind)
    for key in properties:
        _require_choice("declared property", key, COMMON_PROPERTIES)
        if key not in applicable:
            raise ValueError(
                "property %s does not apply to a %s and must not be declared "
                "against it" % (key, kind)
            )
    for name in applicable:
        if name not in properties:
            raise ValueError("%s does not declare %s" % (kind, name))
    results = {}
    if "operating-temperature-range" in applicable:
        results["operating-temperature-range"] = assess_temperature_envelope(
            properties["operating-temperature-range"],
            policy["operating_temperature_margin_k"],
            "operating-temperature-range",
        )
    if "storage-temperature-range" in applicable:
        results["storage-temperature-range"] = assess_temperature_envelope(
            properties["storage-temperature-range"],
            policy["storage_temperature_margin_k"],
            "storage-temperature-range",
        )
    results["seal-leak-rate"] = assess_seal_leak_rate(
        properties["seal-leak-rate"], policy
    )
    results["insulation-resistance"] = assess_insulation_resistance(
        properties["insulation-resistance"], policy
    )
    results["service-life"] = assess_service_life(properties["service-life"])
    results["autoignition-temperature"] = assess_autoignition(
        properties["autoignition-temperature"], policy
    )
    if "function-time" in applicable:
        results["function-time"] = assess_function_time(
            properties["function-time"], policy
        )
    findings = []
    failed = []
    for name in applicable:
        result = results[name]
        findings.extend(result["findings"])
        if not result["compliant"]:
            failed.append(name)
    return {
        "kind": kind,
        "applicable_properties": list(applicable),
        "properties": results,
        "failed_properties": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }


def assess_component_set(components, policy=DEFAULT_COMMON_PROPERTY_POLICY):
    """Grade a set of explosive components and roll the verdicts up."""
    validate_common_property_policy(policy)
    if not isinstance(components, dict) or not components:
        raise ValueError("components must be a non-empty mapping keyed by part name")
    reports = {}
    failed = []
    findings = []
    for name in sorted(components):
        if not isinstance(name, str) or not name.strip():
            raise ValueError("component key must be a non-empty string, got %r" % (name,))
        report = assess_common_properties(components[name], policy)
        reports[name] = report
        if not report["compliant"]:
            failed.append(name)
        findings.extend("%s: %s" % (name, f) for f in report["findings"])
    return {
        "components": reports,
        "failed_components": failed,
        "compliant": not failed,
        "verdict": VERDICT_NOT_MET if failed else VERDICT_MET,
        "findings": findings,
    }
