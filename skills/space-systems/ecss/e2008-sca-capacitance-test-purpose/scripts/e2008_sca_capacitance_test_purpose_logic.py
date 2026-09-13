#!/usr/bin/env python3
"""Purpose of the capacitance test on a solar cell assembly.

Anchor: ECSS-E-ST-20-08C clause 6.4.3.16.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

Nobody wants the capacitance of one solar cell assembly for its own
sake. The number is wanted because the panel it will be built into
behaves like a capacitor at the moments that matter -- a regulator
switching, an electrostatic discharge striking the front surface, a
transient coupling into the harness -- and the panel is far too large
and far too late to measure. So the assembly is measured and the result
is extrapolated up.

That makes the purpose of the test an extrapolation question, not a
measurement question:

    specific capacitance   the assembly value divided by its active
                           area, the quantity that carries across
    representativeness     the measured specific value against the
                           declared reference for the cell technology,
                           because a sample that is not the flight build
                           extrapolates to a panel nobody is building
    precision              the relative standard error of the sample
                           mean, which is what the panel figure inherits
    panel value            assemblies in series divide, strings in
                           parallel multiply

and the panel quantities the extrapolation feeds: the charge held at the
bus working point, the energy an arc can draw from it, and the
displacement current a step in the working point pushes.

A panel value too small to move any of those does not earn the
campaign, whatever behaviours are declared against it.

The sample and band limits below are a declared policy, not a physical
constant: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Panel-level behaviour -> the quantity the extrapolated capacitance feeds.
PANEL_BEHAVIOURS = {
    "panel-electrostatic-discharge-energy": "panel-stored-energy-feeding-an-arc",
    "panel-regulator-switching-transient": "panel-displacement-current-at-switching",
    "panel-harness-transient-coupling": "panel-capacitive-coupling-path-impedance",
    "panel-plasma-current-collection": "panel-capacitive-coupling-to-the-plasma",
    "panel-bus-stability-margin": "panel-capacitance-bus-load-pole",
}

RECOGNISED_BEHAVIOURS = tuple(sorted(PANEL_BEHAVIOURS))

COMMON_OBJECTIVE = "sca-to-panel-capacitance-extrapolation"

PANEL_CHARACTERISATION_NOT_REQUIRED = "panel-characterisation-not-required"
ASSEMBLY_MEASUREMENT_NOT_PLANNED = "assembly-measurement-not-planned"
EXTRAPOLATION_INADEQUATE = "sca-to-panel-extrapolation-inadequate"
PANEL_BEHAVIOUR_CHARACTERISED = "panel-capacitance-characterised"

DEFAULT_EXTRAPOLATION_POLICY = {
    "min_sample_count": 3,
    "max_relative_standard_error": 0.05,
    "representativeness_band": 0.20,
    "significance_trigger_f": 1.0e-9,
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
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_non_negative(name, value):
    number = _require_number(name, value)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
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


def validate_extrapolation_policy(policy):
    """Check an assembly-to-panel extrapolation policy is complete and sane."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    count = policy.get("min_sample_count")
    if not isinstance(count, int) or isinstance(count, bool) or count < 2:
        raise ValueError(
            "min_sample_count must be a whole number of at least two; a single "
            "assembly has no scatter to extrapolate from, got %r" % (count,)
        )
    error = _require_positive(
        "max_relative_standard_error", policy.get("max_relative_standard_error")
    )
    if error >= 1.0:
        raise ValueError(
            "max_relative_standard_error %g must be below one" % error
        )
    band = _require_positive(
        "representativeness_band", policy.get("representativeness_band")
    )
    if band >= 1.0:
        raise ValueError("representativeness_band %g must be below one" % band)
    _require_positive("significance_trigger_f", policy.get("significance_trigger_f"))
    return policy


def sample_statistics(capacitances_f):
    """Mean, scatter and precision of a set of assembly capacitance readings."""
    if not isinstance(capacitances_f, (list, tuple)):
        raise ValueError("capacitances_f must be a sequence of readings")
    values = [
        _require_positive("capacitance reading", value) for value in capacitances_f
    ]
    count = len(values)
    if count < 2:
        raise ValueError(
            "at least two readings are needed; one assembly reports no scatter"
        )
    mean = math.fsum(values) / count
    variance = math.fsum((value - mean) ** 2 for value in values) / (count - 1)
    deviation = math.sqrt(variance)
    return {
        "count": count,
        "mean_f": mean,
        "sample_standard_deviation_f": deviation,
        "relative_standard_error": deviation / (mean * math.sqrt(count)),
    }


def specific_capacitance_f_per_m2(capacitance_f, active_area_m2):
    """Assembly capacitance per unit active area -- what carries to the panel."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    area = _require_positive("active_area_m2", active_area_m2)
    return capacitance / area


def representativeness_ratio(measured_specific, reference_specific):
    """Measured specific capacitance against the cell technology reference."""
    measured = _require_positive("measured_specific", measured_specific)
    reference = _require_positive("reference_specific", reference_specific)
    return measured / reference


def sample_is_representative(ratio, policy=DEFAULT_EXTRAPOLATION_POLICY):
    """True when the sample sits inside the declared representativeness band."""
    validate_extrapolation_policy(policy)
    value = _require_positive("ratio", ratio)
    return _at_most(abs(value - 1.0), float(policy["representativeness_band"]))


def sample_count_adequate(count, policy=DEFAULT_EXTRAPOLATION_POLICY):
    """True when enough assemblies were measured to extrapolate from."""
    validate_extrapolation_policy(policy)
    number = _require_count("count", count)
    return number >= int(policy["min_sample_count"])


def precision_adequate(relative_standard_error, policy=DEFAULT_EXTRAPOLATION_POLICY):
    """True when the sample mean is precise enough for the panel to inherit."""
    validate_extrapolation_policy(policy)
    error = _require_non_negative(
        "relative_standard_error", relative_standard_error
    )
    return _at_most(error, float(policy["max_relative_standard_error"]))


def panel_capacitance_f(
    assembly_capacitance_f, assemblies_in_series, strings_in_parallel
):
    """Panel capacitance: series assemblies divide, parallel strings multiply."""
    capacitance = _require_positive(
        "assembly_capacitance_f", assembly_capacitance_f
    )
    series = _require_count("assemblies_in_series", assemblies_in_series)
    parallel = _require_count("strings_in_parallel", strings_in_parallel)
    return capacitance * parallel / series


def panel_stored_charge_c(capacitance_f, working_point_v):
    """Charge the panel holds at the bus working point."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_number("working_point_v", working_point_v)
    return capacitance * voltage


def panel_discharge_energy_j(capacitance_f, working_point_v):
    """Energy an arc on the panel front surface can draw from that charge."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    voltage = _require_number("working_point_v", working_point_v)
    return 0.5 * capacitance * voltage * voltage


def panel_displacement_current_a(capacitance_f, step_rate_v_per_s):
    """Current the panel capacitance pushes when the working point is stepped."""
    capacitance = _require_positive("capacitance_f", capacitance_f)
    rate = _require_number("step_rate_v_per_s", step_rate_v_per_s)
    return capacitance * rate


def behaviour_inventory(behaviours):
    """Group the declared panel behaviours, rejecting an unrecognised one."""
    if not isinstance(behaviours, (list, tuple, set, frozenset)):
        raise ValueError("behaviours must be a collection of behaviour names")
    grouped = []
    for behaviour in behaviours:
        if behaviour not in PANEL_BEHAVIOURS:
            raise ValueError(
                "unknown panel behaviour %r; recognised behaviours are %s"
                % (behaviour, ", ".join(RECOGNISED_BEHAVIOURS))
            )
        if behaviour not in grouped:
            grouped.append(behaviour)
    return tuple(sorted(grouped))


def extrapolation_objectives(behaviours):
    """What the extrapolated panel capacitance feeds, given the behaviours."""
    grouped = behaviour_inventory(behaviours)
    if not grouped:
        return ()
    objectives = [PANEL_BEHAVIOURS[behaviour] for behaviour in grouped]
    objectives.append(COMMON_OBJECTIVE)
    return tuple(objectives)


def assess_sca_capacitance_purpose(case, policy=DEFAULT_EXTRAPOLATION_POLICY):
    """Full clause 6.4.3.16.1 judgement for one assembly capacitance campaign."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_extrapolation_policy(policy)
    if "panel_behaviours" not in case:
        raise ValueError(
            "case is missing panel_behaviours; an absent inventory is not an "
            "empty one"
        )
    behaviours = behaviour_inventory(case["panel_behaviours"])
    objectives = extrapolation_objectives(case["panel_behaviours"])

    panel = case.get("panel")
    if not isinstance(panel, dict):
        raise ValueError("case is missing a panel block")
    series = _require_count(
        "panel assemblies_in_series", panel.get("assemblies_in_series")
    )
    parallel = _require_count(
        "panel strings_in_parallel", panel.get("strings_in_parallel")
    )
    working_point = _require_number(
        "panel working_point_v", panel.get("working_point_v")
    )
    step_rate = _require_number(
        "panel step_rate_v_per_s", panel.get("step_rate_v_per_s")
    )

    findings = []
    result = {
        "panel_behaviours": behaviours,
        "objectives": objectives,
        "sample": None,
        "assembly_specific_f_per_m2": None,
        "representativeness_ratio": None,
        "panel_capacitance_f": None,
        "panel_stored_charge_c": None,
        "panel_discharge_energy_j": None,
        "panel_displacement_current_a": None,
        "sample_count_adequate": None,
        "precision_adequate": None,
        "sample_representative": None,
        "findings": findings,
    }

    if not behaviours:
        findings.append(
            "no panel-level behaviour is declared, so no panel figure is being "
            "extrapolated toward"
        )
        result["required"] = False
        result["verdict"] = PANEL_CHARACTERISATION_NOT_REQUIRED
        return result

    measurement = case.get("assembly_measurement")
    if measurement is None:
        findings.append(
            "panel behaviours are declared but no assembly capacitance "
            "measurement is planned; there is nothing to extrapolate from"
        )
        result["required"] = True
        result["verdict"] = ASSEMBLY_MEASUREMENT_NOT_PLANNED
        return result
    if not isinstance(measurement, dict):
        raise ValueError(
            "assembly_measurement must be a mapping, got %r" % (measurement,)
        )

    sample = sample_statistics(measurement.get("capacitances_f"))
    active_area = _require_positive(
        "assembly active_area_m2", measurement.get("active_area_m2")
    )
    reference_specific = _require_positive(
        "assembly reference_specific_f_per_m2",
        measurement.get("reference_specific_f_per_m2"),
    )
    specific = specific_capacitance_f_per_m2(sample["mean_f"], active_area)
    ratio = representativeness_ratio(specific, reference_specific)
    panel_value = panel_capacitance_f(sample["mean_f"], series, parallel)

    result["sample"] = sample
    result["assembly_specific_f_per_m2"] = specific
    result["representativeness_ratio"] = ratio
    result["panel_capacitance_f"] = panel_value
    result["panel_stored_charge_c"] = panel_stored_charge_c(
        panel_value, working_point
    )
    result["panel_discharge_energy_j"] = panel_discharge_energy_j(
        panel_value, working_point
    )
    result["panel_displacement_current_a"] = panel_displacement_current_a(
        panel_value, step_rate
    )

    trigger = float(policy["significance_trigger_f"])
    if not _at_least(panel_value, trigger):
        findings.append(
            "the panel extrapolates to %.4g F, below the %.4g F significance "
            "trigger, so no declared behaviour can respond to it"
            % (panel_value, trigger)
        )
        result["required"] = False
        result["verdict"] = PANEL_CHARACTERISATION_NOT_REQUIRED
        return result

    result["required"] = True
    counted = sample_count_adequate(sample["count"], policy)
    precise = precision_adequate(sample["relative_standard_error"], policy)
    representative = sample_is_representative(ratio, policy)

    result["sample_count_adequate"] = counted
    result["precision_adequate"] = precise
    result["sample_representative"] = representative

    if not counted:
        findings.append(
            "%d assemblies were measured against the %d the extrapolation "
            "basis asks for" % (sample["count"], int(policy["min_sample_count"]))
        )
    if not precise:
        findings.append(
            "the sample mean carries a %.4g relative standard error, above the "
            "%.4g the panel figure may inherit"
            % (
                sample["relative_standard_error"],
                float(policy["max_relative_standard_error"]),
            )
        )
    if not representative:
        findings.append(
            "the measured specific capacitance is %.3f times the reference for "
            "the cell technology, outside the %.3f band, so the sample is not "
            "the build the panel extrapolates to"
            % (ratio, float(policy["representativeness_band"]))
        )

    result["verdict"] = (
        PANEL_BEHAVIOUR_CHARACTERISED
        if counted and precise and representative
        else EXTRAPOLATION_INADEQUATE
    )
    return result
