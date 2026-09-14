#!/usr/bin/env python3
"""Holding an external protection diode at temperature and asking whether it
came back out electrically unchanged.

Anchor: ECSS-E-ST-20-08C clause 9.6.13. The procedure below is a paraphrase
into implementable steps; no standard text is reproduced.

An annealing soak is not an environmental stress in the usual sense. Nothing
is cycled, nothing is vibrated: the devices are simply held hot, long enough
for whatever is mobile inside the junction and the contacts to move, and then
measured again. The question the clause asks is narrow and it is a stability
question -- did the parameters that were recorded before the soak still read
the same afterwards. Four things decide whether the answer means anything:

    the profile      a floor on the soak temperature and on its duration,
                     and a ceiling set by the package itself. A soak run
                     above the rating anneals the encapsulant as well as the
                     junction, and the drift that follows belongs to the
                     package, not to the diode
    the dose         temperature and time are one variable, not two. An
                     Arrhenius factor turns the soak into equivalent hours
                     at the reference temperature, so a short hot soak and a
                     long warm one can be compared at all
    the return       the post-soak reading has to be taken at the same
                     temperature as the pre-soak one. A device measured
                     while it is still warm reports its temperature
                     coefficient and calls it annealing drift
    the drift        forward voltage and blocking voltage move by a fraction
                     of themselves; reverse leakage moves by a ratio, since
                     it spans decades and a percentage of a nanoamp says
                     nothing

The acceleration factor is the one number that has to be computed rather than
read. It comes out of an exponential of a reciprocal temperature difference,
which lands a few units in the last place either side of a limit on different
hosts, so every comparison here absorbs that error while the limits themselves
are never relaxed.

The floors, ceilings and the subgroup label below are a declared policy, not
physical constants: a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANNEALING_SUBGROUP = "Q"

BOLTZMANN_EV_PER_K = 8.617333262e-5
ABSOLUTE_ZERO_C = -273.15

ANNEALING_SAMPLE_PLAN_DEFICIENT = "diode-annealing-sample-plan-deficient"
ANNEALING_PARAMETER_INSTABILITY = "diode-annealing-parameter-instability"
ANNEALING_SOAK_PROFILE_DEFICIENT = "diode-annealing-soak-profile-deficient"
ANNEALING_STABILITY_ACCEPTED = "diode-annealing-stability-accepted"

ANNEALING_VERDICTS = (
    ANNEALING_SAMPLE_PLAN_DEFICIENT,
    ANNEALING_PARAMETER_INSTABILITY,
    ANNEALING_SOAK_PROFILE_DEFICIENT,
    ANNEALING_STABILITY_ACCEPTED,
)

DEFAULT_DIODE_ANNEALING_POLICY = {
    "min_subgroup_diodes": 5,
    "min_soak_temperature_c": 125.0,
    "min_soak_duration_h": 168.0,
    "reference_temperature_c": 25.0,
    "activation_energy_ev": 0.7,
    "min_equivalent_reference_hours": 20000.0,
    "min_recovery_dwell_h": 2.0,
    "max_measurement_temperature_delta_k": 2.0,
    "max_forward_voltage_drift_fraction": 0.05,
    "max_reverse_leakage_growth_ratio": 10.0,
    "max_blocking_voltage_drift_fraction": 0.05,
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


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ValueError("%s must be a positive whole number, got %r" % (name, value))
    return value


def _require_temperature_c(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError("%s must be above absolute zero, got %r" % (name, value))
    return number


def _require_fraction(name, value):
    number = _require_number(name, value)
    if not 0.0 < number < 1.0:
        raise ValueError(
            "%s must be a fraction above zero and below one, got %r" % (name, value)
        )
    return number


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


def validate_annealing_policy(policy):
    """Check a protection diode annealing policy is self-consistent."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    _require_count("min_subgroup_diodes", policy.get("min_subgroup_diodes"))
    soak = _require_temperature_c(
        "min_soak_temperature_c", policy.get("min_soak_temperature_c")
    )
    reference = _require_temperature_c(
        "reference_temperature_c", policy.get("reference_temperature_c")
    )
    if not reference < soak:
        raise ValueError(
            "reference_temperature_c %g must sit below min_soak_temperature_c %g, "
            "or the soak accelerates nothing" % (reference, soak)
        )
    _require_positive("min_soak_duration_h", policy.get("min_soak_duration_h"))
    _require_positive("activation_energy_ev", policy.get("activation_energy_ev"))
    _require_positive(
        "min_equivalent_reference_hours",
        policy.get("min_equivalent_reference_hours"),
    )
    _require_positive("min_recovery_dwell_h", policy.get("min_recovery_dwell_h"))
    _require_positive(
        "max_measurement_temperature_delta_k",
        policy.get("max_measurement_temperature_delta_k"),
    )
    _require_fraction(
        "max_forward_voltage_drift_fraction",
        policy.get("max_forward_voltage_drift_fraction"),
    )
    growth = _require_number(
        "max_reverse_leakage_growth_ratio",
        policy.get("max_reverse_leakage_growth_ratio"),
    )
    if growth <= 1.0:
        raise ValueError(
            "max_reverse_leakage_growth_ratio must exceed one, got %r"
            % (policy.get("max_reverse_leakage_growth_ratio"),)
        )
    _require_fraction(
        "max_blocking_voltage_drift_fraction",
        policy.get("max_blocking_voltage_drift_fraction"),
    )
    return policy


def arrhenius_acceleration_factor(
    soak_temperature_c, reference_temperature_c, activation_energy_ev
):
    """How much faster the soak ages the junction than the reference does."""
    soak_k = _require_temperature_c("soak_temperature_c", soak_temperature_c) - (
        ABSOLUTE_ZERO_C
    )
    reference_k = _require_temperature_c(
        "reference_temperature_c", reference_temperature_c
    ) - ABSOLUTE_ZERO_C
    energy = _require_positive("activation_energy_ev", activation_energy_ev)
    return math.exp(
        (energy / BOLTZMANN_EV_PER_K) * ((1.0 / reference_k) - (1.0 / soak_k))
    )


def equivalent_reference_hours(
    soak_duration_h,
    soak_temperature_c,
    reference_temperature_c,
    activation_energy_ev,
):
    """Hours at the reference temperature the soak is worth."""
    duration = _require_positive("soak_duration_h", soak_duration_h)
    return duration * arrhenius_acceleration_factor(
        soak_temperature_c, reference_temperature_c, activation_energy_ev
    )


def soak_within_package_rating(soak_temperature_c, max_rated_temperature_c):
    """True when the soak stays at or under what the package is rated for."""
    soak = _require_temperature_c("soak_temperature_c", soak_temperature_c)
    rating = _require_temperature_c(
        "max_rated_temperature_c", max_rated_temperature_c
    )
    return _at_most(soak, rating)


def subgroup_diode_count(sample_plan, subgroup=ANNEALING_SUBGROUP):
    """Devices the plan draws from the subgroup the annealing test is run on."""
    if not isinstance(sample_plan, dict):
        raise ValueError("sample_plan must be a mapping, got %r" % (sample_plan,))
    if not isinstance(subgroup, str) or not subgroup.strip():
        raise ValueError("subgroup must be a non-empty label, got %r" % (subgroup,))
    label = sample_plan.get("subgroup")
    if not isinstance(label, str) or not label.strip():
        raise ValueError("sample_plan is missing a subgroup label, got %r" % (label,))
    count = _require_count("sample_plan diode_count", sample_plan.get("diode_count"))
    if label.strip().upper() != subgroup.strip().upper():
        return 0
    return count


def relative_parameter_drift(before_value, after_value):
    """Size of the move across the soak, as a fraction of where it started."""
    before = _require_number("before_value", before_value)
    after = _require_number("after_value", after_value)
    if before == 0.0:
        raise ValueError("before_value must not be zero, got %r" % (before_value,))
    return abs(after - before) / abs(before)


def reverse_leakage_growth_ratio(before_value, after_value):
    """How many times its pre-soak value the reverse leakage came back at."""
    before = _require_positive("before_value", before_value)
    after = _require_positive("after_value", after_value)
    return after / before


def measurement_temperature_delta_k(before_temperature_c, after_temperature_c):
    """How far apart the two measurement temperatures sat."""
    before = _require_temperature_c("before_temperature_c", before_temperature_c)
    after = _require_temperature_c("after_temperature_c", after_temperature_c)
    return abs(after - before)


def assess_diode_annealing(case, policy=DEFAULT_DIODE_ANNEALING_POLICY):
    """Full clause 9.6.13 judgement for one protection diode annealing soak."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_annealing_policy(policy)
    sample_plan = case.get("sample_plan")
    if sample_plan is None:
        raise ValueError("case is missing a sample_plan block")
    soak = case.get("soak")
    if not isinstance(soak, dict):
        raise ValueError("case is missing a soak block")
    before = case.get("before")
    after = case.get("after")
    if not isinstance(before, dict):
        raise ValueError("case is missing a before block")
    if not isinstance(after, dict):
        raise ValueError("case is missing an after block")

    planned = subgroup_diode_count(sample_plan)
    soak_temperature = _require_temperature_c(
        "soak soak_temperature_c", soak.get("soak_temperature_c")
    )
    soak_duration = _require_positive(
        "soak soak_duration_h", soak.get("soak_duration_h")
    )
    rating = _require_temperature_c(
        "soak max_rated_temperature_c", soak.get("max_rated_temperature_c")
    )
    recovery = _require_positive(
        "soak recovery_dwell_h", soak.get("recovery_dwell_h")
    )

    equivalent = equivalent_reference_hours(
        soak_duration,
        soak_temperature,
        float(policy["reference_temperature_c"]),
        float(policy["activation_energy_ev"]),
    )
    acceleration = arrhenius_acceleration_factor(
        soak_temperature,
        float(policy["reference_temperature_c"]),
        float(policy["activation_energy_ev"]),
    )
    temperature_delta = measurement_temperature_delta_k(
        before.get("measurement_temperature_c"),
        after.get("measurement_temperature_c"),
    )
    forward_drift = relative_parameter_drift(
        before.get("forward_voltage_v"), after.get("forward_voltage_v")
    )
    leakage_ratio = reverse_leakage_growth_ratio(
        before.get("reverse_leakage_a"), after.get("reverse_leakage_a")
    )
    blocking_drift = relative_parameter_drift(
        before.get("blocking_voltage_v"), after.get("blocking_voltage_v")
    )

    findings = []
    result = {
        "subgroup_diodes": planned,
        "acceleration_factor": acceleration,
        "equivalent_reference_hours": equivalent,
        "soak_within_rating": soak_within_package_rating(soak_temperature, rating),
        "measurement_temperature_delta_k": temperature_delta,
        "forward_voltage_drift_fraction": forward_drift,
        "reverse_leakage_growth_ratio": leakage_ratio,
        "blocking_voltage_drift_fraction": blocking_drift,
        "findings": findings,
    }

    sample_short = not _at_least(planned, float(policy["min_subgroup_diodes"]))
    if sample_short:
        findings.append(
            "the plan soaks %d subgroup %s diodes against the %d the policy asks for"
            % (planned, ANNEALING_SUBGROUP, int(policy["min_subgroup_diodes"]))
        )

    unstable = False
    if not _at_most(
        forward_drift, float(policy["max_forward_voltage_drift_fraction"])
    ):
        unstable = True
        findings.append(
            "the forward voltage moved %.5f of itself across the soak against the "
            "%.5f allowed, so the junction did not come back where it went in"
            % (forward_drift, float(policy["max_forward_voltage_drift_fraction"]))
        )
    if not _at_most(
        leakage_ratio, float(policy["max_reverse_leakage_growth_ratio"])
    ):
        unstable = True
        findings.append(
            "the reverse leakage came back %.4f times its pre-soak value against "
            "the %.4f allowed"
            % (leakage_ratio, float(policy["max_reverse_leakage_growth_ratio"]))
        )
    if not _at_most(
        blocking_drift, float(policy["max_blocking_voltage_drift_fraction"])
    ):
        unstable = True
        findings.append(
            "the blocking voltage moved %.5f of itself against the %.5f allowed"
            % (blocking_drift, float(policy["max_blocking_voltage_drift_fraction"]))
        )

    if not result["soak_within_rating"]:
        findings.append(
            "the soak ran at %.2f C against a %.2f C package rating, so the "
            "encapsulant was annealed alongside the junction"
            % (soak_temperature, rating)
        )
    if not _at_least(soak_temperature, float(policy["min_soak_temperature_c"])):
        findings.append(
            "the soak ran at %.2f C against the %.2f C floor"
            % (soak_temperature, float(policy["min_soak_temperature_c"]))
        )
    if not _at_least(soak_duration, float(policy["min_soak_duration_h"])):
        findings.append(
            "the soak ran %.2f h against the %.2f h floor"
            % (soak_duration, float(policy["min_soak_duration_h"]))
        )
    if not _at_least(
        equivalent, float(policy["min_equivalent_reference_hours"])
    ):
        findings.append(
            "the soak is worth %.1f h at %.2f C against the %.1f h the policy "
            "asks the annealing to reach"
            % (
                equivalent,
                float(policy["reference_temperature_c"]),
                float(policy["min_equivalent_reference_hours"]),
            )
        )
    if not _at_least(recovery, float(policy["min_recovery_dwell_h"])):
        findings.append(
            "the devices recovered %.2f h before the post-soak reading against "
            "the %.2f h required" % (recovery, float(policy["min_recovery_dwell_h"]))
        )
    reading_mismatch = not _at_most(
        temperature_delta, float(policy["max_measurement_temperature_delta_k"])
    )
    if reading_mismatch:
        findings.append(
            "the two readings sat %.3f K apart against the %.3f K allowed, so the "
            "difference between them is a temperature coefficient"
            % (
                temperature_delta,
                float(policy["max_measurement_temperature_delta_k"]),
            )
        )

    if reading_mismatch:
        # A drift taken between two different temperatures is a temperature
        # coefficient wearing the annealing result's name, so the mismatch
        # outranks the drift it would otherwise be reported as.
        result["verdict"] = ANNEALING_SOAK_PROFILE_DEFICIENT
    elif unstable:
        result["verdict"] = ANNEALING_PARAMETER_INSTABILITY
    elif sample_short:
        result["verdict"] = ANNEALING_SAMPLE_PLAN_DEFICIENT
    elif findings:
        result["verdict"] = ANNEALING_SOAK_PROFILE_DEFICIENT
    else:
        result["verdict"] = ANNEALING_STABILITY_ACCEPTED
    return result
