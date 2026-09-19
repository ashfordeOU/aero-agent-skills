#!/usr/bin/env python3
"""Planetary-protection interface of a sterilization-compatibility test.

Anchor: ECSS-Q-ST-70-53C, the interface clauses that tie a compatibility test
to the microbial-reduction standards ECSS-Q-ST-70-56C (dry heat) and
ECSS-Q-ST-70-57C (vapour-phase). The procedure below is a paraphrase into
implementable steps; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the process kind and its decimal-reduction-time parameters.
2. Correct the reference decimal-reduction time to the condition actually
   run: the z-value relation for dry heat, the concentration-coefficient
   relation for a vapour-phase process.
3. Divide the accumulated exposure by the corrected decimal-reduction time to
   obtain the log reduction achieved.
4. Scale the initial spore count by ten to the minus that reduction and
   compare the surviving count with its allocation.
5. Derive the exposure a declared target reduction would need, and the
   shortfall against the exposure actually planned.
6. Compare every required process parameter with the compatibility-qualified
   envelope; a parameter over its ceiling, or absent from the envelope, is
   outside it.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "ALLOCATION_TOLERANCE",
    "DRY_HEAT",
    "VAPOUR_PHASE",
    "PROCESSES",
    "validate_process",
    "dry_heat_d_value",
    "vapour_phase_d_value",
    "effective_d_value",
    "log_reduction",
    "surviving_bioburden",
    "required_exposure_minutes",
    "envelope_findings",
    "assess_planetary_protection_interface",
]

# The allocation comparison is a comparison of counts produced by a power of
# ten: an exact equality can land a few ULPs on the wrong side. Absorb the
# representation error here instead of relaxing the allocation.
ALLOCATION_TOLERANCE = 1e-9

DRY_HEAT = "dry-heat"
VAPOUR_PHASE = "vapour-phase"
PROCESSES = (DRY_HEAT, VAPOUR_PHASE)


def _positive(value, label):
    """Return value as a positive finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, out))
    return out


def _non_negative(value, label):
    """Return value as a non-negative finite float, or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out < 0.0:
        raise ValueError("%s must be non-negative, got %g" % (label, out))
    return out


def validate_process(process):
    """Return the validated microbial-reduction process kind."""
    if process not in PROCESSES:
        raise ValueError(
            "process must be one of %s, got %r" % (", ".join(PROCESSES), process)
        )
    return process


def dry_heat_d_value(reference_d_minutes, reference_temperature_c,
                     temperature_c, z_value_c):
    """Return the decimal-reduction time corrected to a dry-heat temperature."""
    d_ref = _positive(reference_d_minutes, "reference_d_minutes")
    z_value = _positive(z_value_c, "z_value_c")
    if not isinstance(reference_temperature_c, (int, float)) or isinstance(
        reference_temperature_c, bool
    ):
        raise ValueError("reference_temperature_c must be a real number")
    if not isinstance(temperature_c, (int, float)) or isinstance(temperature_c, bool):
        raise ValueError("temperature_c must be a real number")
    t_ref = float(reference_temperature_c)
    temperature = float(temperature_c)
    if not math.isfinite(t_ref) or not math.isfinite(temperature):
        raise ValueError("temperatures must be finite")
    if temperature <= -273.15 or t_ref <= -273.15:
        raise ValueError("temperatures must lie above absolute zero")
    return d_ref * 10.0 ** ((t_ref - temperature) / z_value)


def vapour_phase_d_value(reference_d_minutes, reference_concentration_mg_l,
                         concentration_mg_l, concentration_exponent):
    """Return the decimal-reduction time corrected to a sterilant concentration."""
    d_ref = _positive(reference_d_minutes, "reference_d_minutes")
    c_ref = _positive(reference_concentration_mg_l, "reference_concentration_mg_l")
    concentration = _positive(concentration_mg_l, "concentration_mg_l")
    exponent = _positive(concentration_exponent, "concentration_exponent")
    return d_ref * (c_ref / concentration) ** exponent


def effective_d_value(process, parameters):
    """Dispatch the decimal-reduction-time correction for a process kind."""
    kind = validate_process(process)
    if not isinstance(parameters, dict):
        raise ValueError("parameters must be a mapping")
    if kind == DRY_HEAT:
        for key in ("reference_d_minutes", "reference_temperature_c",
                    "temperature_c", "z_value_c"):
            if key not in parameters:
                raise ValueError("dry-heat parameters missing '%s'" % key)
        return dry_heat_d_value(
            parameters["reference_d_minutes"],
            parameters["reference_temperature_c"],
            parameters["temperature_c"],
            parameters["z_value_c"],
        )
    for key in ("reference_d_minutes", "reference_concentration_mg_l",
                "concentration_mg_l", "concentration_exponent"):
        if key not in parameters:
            raise ValueError("vapour-phase parameters missing '%s'" % key)
    return vapour_phase_d_value(
        parameters["reference_d_minutes"],
        parameters["reference_concentration_mg_l"],
        parameters["concentration_mg_l"],
        parameters["concentration_exponent"],
    )


def log_reduction(exposure_minutes, d_minutes):
    """Return the number of decimal reductions an exposure achieves."""
    exposure = _non_negative(exposure_minutes, "exposure_minutes")
    d_value = _positive(d_minutes, "d_minutes")
    return exposure / d_value


def surviving_bioburden(initial_spores, reduction):
    """Return the spore count surviving a given number of decimal reductions."""
    initial = _non_negative(initial_spores, "initial_spores")
    decades = _non_negative(reduction, "reduction")
    return initial * 10.0 ** (-decades)


def required_exposure_minutes(d_minutes, target_reduction):
    """Return the exposure a target number of decimal reductions needs."""
    d_value = _positive(d_minutes, "d_minutes")
    target = _non_negative(target_reduction, "target_reduction")
    return d_value * target


def envelope_findings(required, qualified):
    """Return findings where a required parameter leaves the qualified envelope."""
    if not isinstance(required, dict) or not required:
        raise ValueError("required envelope must be a non-empty mapping")
    if not isinstance(qualified, dict) or not qualified:
        raise ValueError("qualified envelope must be a non-empty mapping")
    findings = []
    for name in sorted(required):
        need = _non_negative(required[name], "required %r" % name)
        if name not in qualified:
            findings.append(
                "process parameter '%s' is not covered by the compatibility-qualified "
                "envelope" % name
            )
            continue
        ceiling = _non_negative(qualified[name], "qualified %r" % name)
        if need > ceiling and not math.isclose(
            need, ceiling, rel_tol=ALLOCATION_TOLERANCE, abs_tol=0.0
        ):
            findings.append(
                "process parameter '%s' needs %.6g against a qualified ceiling of %.6g"
                % (name, need, ceiling)
            )
    return findings


def assess_planetary_protection_interface(spec):
    """Run the full ECSS-Q-ST-70-53C planetary-protection interface assessment.

    spec keys: process, process_parameters, exposure_minutes,
    initial_bioburden_spores, allocated_bioburden_spores, required_envelope,
    qualified_envelope. Optional: item_id, target_log_reduction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("process", "process_parameters", "exposure_minutes",
                "initial_bioburden_spores", "allocated_bioburden_spores",
                "required_envelope", "qualified_envelope"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    process = validate_process(spec["process"])
    d_value = effective_d_value(process, spec["process_parameters"])
    exposure = _non_negative(spec["exposure_minutes"], "exposure_minutes")
    achieved = log_reduction(exposure, d_value)
    initial = _non_negative(spec["initial_bioburden_spores"], "initial_bioburden_spores")
    allocation = _non_negative(
        spec["allocated_bioburden_spores"], "allocated_bioburden_spores"
    )
    surviving = surviving_bioburden(initial, achieved)
    allocation_met = surviving < allocation or math.isclose(
        surviving, allocation, rel_tol=ALLOCATION_TOLERANCE, abs_tol=0.0
    )

    findings = []
    if not allocation_met:
        findings.append(
            "surviving bioburden %.6g spores exceeds the allocation of %.6g spores"
            % (surviving, allocation)
        )

    target = spec.get("target_log_reduction")
    needed_exposure = None
    exposure_shortfall = 0.0
    target_met = True
    if target is not None:
        target_value = _non_negative(target, "target_log_reduction")
        needed_exposure = required_exposure_minutes(d_value, target_value)
        target_met = achieved > target_value or math.isclose(
            achieved, target_value, rel_tol=ALLOCATION_TOLERANCE, abs_tol=0.0
        )
        exposure_shortfall = max(0.0, needed_exposure - exposure)
        if not target_met:
            findings.append(
                "achieved %.4f decimal reductions against a target of %.4f; "
                "another %.4f minutes of exposure is needed"
                % (achieved, target_value, exposure_shortfall)
            )

    envelope = envelope_findings(spec["required_envelope"], spec["qualified_envelope"])
    findings.extend(envelope)
    return {
        "item_id": spec.get("item_id"),
        "process": process,
        "effective_d_minutes": d_value,
        "exposure_minutes": exposure,
        "achieved_log_reduction": achieved,
        "surviving_bioburden_spores": surviving,
        "allocated_bioburden_spores": allocation,
        "allocation_met": allocation_met,
        "target_log_reduction": None if target is None else float(target),
        "required_exposure_minutes": needed_exposure,
        "exposure_shortfall_minutes": exposure_shortfall,
        "target_met": target_met,
        "envelope_findings": envelope,
        "within_qualified_envelope": not envelope,
        "acceptable": allocation_met and target_met and not envelope,
        "findings": findings,
    }
