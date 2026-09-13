#!/usr/bin/env python3
"""Pre-measurement discharge control for dielectric yield coupons.

Anchor: ECSS-E-ST-20-01C clause 9.4.2.4 (multipaction design and test) --
a dielectric coupon is discharged before a secondary-emission-yield
measurement so that the surface potential is small in magnitude and
uniform across the measured area.

Paraphrased into an implementable procedure; no standard text is
reproduced. Stdlib only, offline, deterministic.

Units used throughout:
  surface potential     V       (volt)
  relative permittivity -       (dimensionless, >= 1)
  volume resistivity    ohm.m
  relaxation time       s
  dwell time            s
"""

import math

__all__ = [
    "VACUUM_PERMITTIVITY_F_PER_M",
    "DEFAULT_MAGNITUDE_LIMIT_V",
    "DEFAULT_SPREAD_LIMIT_V",
    "HARD_REJECT_SPREAD_MULTIPLE",
    "NEUTRALIZATION_TECHNIQUES",
    "SURFACE_ALTERING_TECHNIQUES",
    "REL_TOL",
    "validate_voltage_map",
    "surface_voltage_magnitude",
    "surface_voltage_spread",
    "is_within_limit",
    "categorize_precondition_state",
    "validate_neutralization_technique",
    "dielectric_relaxation_time",
    "residual_voltage_after",
    "required_neutralization_dwell",
    "verify_post_neutralization",
    "plan_discharge_sequence",
]

VACUUM_PERMITTIVITY_F_PER_M = 8.8541878128e-12

# Default pre-measurement acceptance limits on the coupon surface.
DEFAULT_MAGNITUDE_LIMIT_V = 5.0
DEFAULT_SPREAD_LIMIT_V = 2.0

# A spread this many times its limit indicates an embedded charge layer
# that no surface neutralization technique will clear.
HARD_REJECT_SPREAD_MULTIPLE = 10.0

# Admissible techniques and their effectiveness factor: the multiple by
# which the technique accelerates decay relative to bulk relaxation
# alone (1.0 = passive grounding, no acceleration).
NEUTRALIZATION_TECHNIQUES = {
    "electron-flood": 500.0,
    "ultraviolet-photoemission": 200.0,
    "low-energy-plasma": 1000.0,
    "grounded-mesh-contact": 50.0,
    "passive-grounding": 1.0,
}

# Techniques that do reduce potential but change the emitting surface,
# so they are never an admissible pre-measurement discharge step.
SURFACE_ALTERING_TECHNIQUES = {
    "solvent-wipe",
    "thermal-bake",
    "ion-beam-clean",
    "abrasive-polish",
}

# Representation tolerance for boundary comparisons. Magnitude and
# spread are differences of measured values, so an exactly-at-limit case
# can land a few ULPs high; this absorbs that, never the limit itself.
REL_TOL = 1e-9


def _finite_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return number


def _positive_number(value, name):
    number = _finite_number(value, name)
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def validate_voltage_map(readings):
    """Validate a surface-voltage map and return it as a list of floats.

    readings is a non-empty sequence of finite numeric surface
    potentials in volts, one per probed point. Raises ValueError on a
    non-sequence, an empty map, or a non-numeric or non-finite reading.
    """
    if isinstance(readings, (str, bytes)) or not isinstance(
        readings, (list, tuple)
    ):
        raise ValueError("voltage map must be a list or tuple, got %r" % (readings,))
    if len(readings) == 0:
        raise ValueError("voltage map is empty: no probed points on record")
    return [
        _finite_number(value, "voltage map reading %d" % index)
        for index, value in enumerate(readings)
    ]


def surface_voltage_magnitude(readings):
    """Largest absolute surface potential on the map, volts."""
    values = validate_voltage_map(readings)
    return max(abs(value) for value in values)


def surface_voltage_spread(readings):
    """Point-to-point spread of the map (highest minus lowest), volts."""
    values = validate_voltage_map(readings)
    return max(values) - min(values)


def is_within_limit(value, limit):
    """True when a non-negative figure is at or below its limit.

    A figure exactly at the limit is inside it; REL_TOL absorbs the few
    ULPs a measured difference can land above an exactly equal limit.
    The acceptance limit itself is never widened.
    """
    figure = _finite_number(value, "value")
    if figure < 0.0:
        raise ValueError("value must not be negative, got %r" % (value,))
    bound = _positive_number(limit, "limit")
    return figure <= bound or math.isclose(figure, bound, rel_tol=REL_TOL)


def categorize_precondition_state(
    readings,
    magnitude_limit_v=DEFAULT_MAGNITUDE_LIMIT_V,
    spread_limit_v=DEFAULT_SPREAD_LIMIT_V,
):
    """Categorize the as-received charge state of a dielectric coupon.

    Returns a dict with magnitude, spread, the two pass flags, a state
    of "ready", "needs-neutralization" or "reject-coupon", and the
    findings behind that state.
    """
    values = validate_voltage_map(readings)
    magnitude_bound = _positive_number(magnitude_limit_v, "magnitude_limit_v")
    spread_bound = _positive_number(spread_limit_v, "spread_limit_v")

    magnitude = max(abs(value) for value in values)
    spread = max(values) - min(values)
    magnitude_ok = is_within_limit(magnitude, magnitude_bound)
    spread_ok = is_within_limit(spread, spread_bound)

    findings = []
    if not magnitude_ok:
        findings.append(
            "surface potential magnitude %.4f V exceeds limit %.4f V"
            % (magnitude, magnitude_bound)
        )
    if not spread_ok:
        findings.append(
            "surface potential spread %.4f V exceeds limit %.4f V"
            % (spread, spread_bound)
        )

    if spread > spread_bound * HARD_REJECT_SPREAD_MULTIPLE:
        state = "reject-coupon"
        findings.append(
            "spread %.4f V is more than %.0fx its limit: embedded charge layer "
            "or conduction defect, surface neutralization will not clear it"
            % (spread, HARD_REJECT_SPREAD_MULTIPLE)
        )
    elif magnitude_ok and spread_ok:
        state = "ready"
    else:
        state = "needs-neutralization"

    return {
        "magnitude_v": magnitude,
        "spread_v": spread,
        "magnitude_within_limit": magnitude_ok,
        "spread_within_limit": spread_ok,
        "state": state,
        "findings": findings,
        "point_count": len(values),
    }


def validate_neutralization_technique(technique):
    """Return the effectiveness factor of an admissible technique.

    Raises ValueError on an unrecognized technique, and separately on a
    technique that alters the emitting surface (which reduces potential
    but destroys the surface treatment under measurement).
    """
    if not isinstance(technique, str) or not technique.strip():
        raise ValueError("technique must be a non-empty string")
    key = technique.strip().lower()
    if key in SURFACE_ALTERING_TECHNIQUES:
        raise ValueError(
            "technique %r alters the emitting surface and is not an admissible "
            "pre-measurement discharge step" % technique
        )
    if key not in NEUTRALIZATION_TECHNIQUES:
        raise ValueError(
            "unknown technique %r; admissible: %s"
            % (technique, ", ".join(sorted(NEUTRALIZATION_TECHNIQUES)))
        )
    return NEUTRALIZATION_TECHNIQUES[key]


def dielectric_relaxation_time(relative_permittivity, volume_resistivity_ohm_m):
    """Bulk charge relaxation time of the coupon stack, seconds."""
    permittivity = _positive_number(relative_permittivity, "relative_permittivity")
    if permittivity < 1.0:
        raise ValueError(
            "relative_permittivity must be >= 1.0, got %r" % (relative_permittivity,)
        )
    resistivity = _positive_number(
        volume_resistivity_ohm_m, "volume_resistivity_ohm_m"
    )
    return VACUUM_PERMITTIVITY_F_PER_M * permittivity * resistivity


def residual_voltage_after(initial_voltage_v, relaxation_time_s, elapsed_s):
    """Surface potential left after an exponential decay, volts."""
    initial = _finite_number(initial_voltage_v, "initial_voltage_v")
    tau = _positive_number(relaxation_time_s, "relaxation_time_s")
    elapsed = _finite_number(elapsed_s, "elapsed_s")
    if elapsed < 0.0:
        raise ValueError("elapsed_s must not be negative, got %r" % (elapsed_s,))
    return initial * math.exp(-elapsed / tau)


def required_neutralization_dwell(
    initial_magnitude_v, target_magnitude_v, relaxation_time_s, effectiveness=1.0
):
    """Dwell time needed to decay the magnitude to the target, seconds.

    An initial magnitude already at or below the target needs no dwell
    and returns 0.0. effectiveness is the technique factor: it divides
    the effective time constant.
    """
    initial = _finite_number(initial_magnitude_v, "initial_magnitude_v")
    if initial < 0.0:
        raise ValueError("initial_magnitude_v must not be negative")
    target = _positive_number(target_magnitude_v, "target_magnitude_v")
    tau = _positive_number(relaxation_time_s, "relaxation_time_s")
    factor = _positive_number(effectiveness, "effectiveness")
    if is_within_limit(initial, target):
        return 0.0
    return (tau / factor) * math.log(initial / target)


def verify_post_neutralization(
    before_readings,
    after_readings,
    magnitude_limit_v=DEFAULT_MAGNITUDE_LIMIT_V,
    spread_limit_v=DEFAULT_SPREAD_LIMIT_V,
):
    """Confirm a neutralization step actually worked.

    Raises ValueError when the two maps do not cover the same points.
    Returns a report with both states, the magnitude change, and the
    release decision.
    """
    before = validate_voltage_map(before_readings)
    after = validate_voltage_map(after_readings)
    if len(before) != len(after):
        raise ValueError(
            "post-neutralization map has %d points but the pre map has %d: the "
            "two maps must cover the same probed points" % (len(after), len(before))
        )
    before_state = categorize_precondition_state(
        before, magnitude_limit_v, spread_limit_v
    )
    after_state = categorize_precondition_state(
        after, magnitude_limit_v, spread_limit_v
    )

    findings = list(after_state["findings"])
    magnitude_drop = before_state["magnitude_v"] - after_state["magnitude_v"]
    if magnitude_drop <= 0.0 and not math.isclose(
        before_state["magnitude_v"], after_state["magnitude_v"], rel_tol=REL_TOL
    ):
        findings.append(
            "magnitude rose from %.4f V to %.4f V: the step charged the coupon "
            "instead of discharging it" % (
                before_state["magnitude_v"], after_state["magnitude_v"]
            )
        )
    released = (
        after_state["magnitude_within_limit"]
        and after_state["spread_within_limit"]
        and not findings
    )
    return {
        "before": before_state,
        "after": after_state,
        "magnitude_drop_v": magnitude_drop,
        "findings": findings,
        "released_for_measurement": released,
    }


def plan_discharge_sequence(plan):
    """Plan the pre-measurement discharge of one dielectric coupon.

    plan keys: readings, relative_permittivity, volume_resistivity_ohm_m,
    technique, available_slot_s; optional magnitude_limit_v,
    spread_limit_v, target_magnitude_v.
    Returns a report dict; raises ValueError on any invalid input.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    required = (
        "readings",
        "relative_permittivity",
        "volume_resistivity_ohm_m",
        "technique",
        "available_slot_s",
    )
    missing = [key for key in required if key not in plan]
    if missing:
        raise ValueError("plan missing key(s): %s" % ", ".join(sorted(missing)))

    magnitude_limit = _positive_number(
        plan.get("magnitude_limit_v", DEFAULT_MAGNITUDE_LIMIT_V), "magnitude_limit_v"
    )
    spread_limit = _positive_number(
        plan.get("spread_limit_v", DEFAULT_SPREAD_LIMIT_V), "spread_limit_v"
    )
    target = _positive_number(
        plan.get("target_magnitude_v", magnitude_limit), "target_magnitude_v"
    )
    slot = _positive_number(plan["available_slot_s"], "available_slot_s")

    state = categorize_precondition_state(
        plan["readings"], magnitude_limit, spread_limit
    )
    findings = list(state["findings"])

    if state["state"] == "reject-coupon":
        return {
            "state": state,
            "technique": None,
            "relaxation_time_s": None,
            "required_dwell_s": None,
            "fits_available_slot": False,
            "findings": findings,
            "proceed_to_measurement": False,
        }

    tau = dielectric_relaxation_time(
        plan["relative_permittivity"], plan["volume_resistivity_ohm_m"]
    )

    if state["state"] == "ready":
        return {
            "state": state,
            "technique": None,
            "relaxation_time_s": tau,
            "required_dwell_s": 0.0,
            "fits_available_slot": True,
            "findings": findings,
            "proceed_to_measurement": True,
        }

    factor = validate_neutralization_technique(plan["technique"])
    dwell = required_neutralization_dwell(
        state["magnitude_v"], target, tau, factor
    )
    fits = dwell <= slot or math.isclose(dwell, slot, rel_tol=REL_TOL)
    if not fits:
        findings.append(
            "required dwell %.1f s does not fit the available slot %.1f s; use a "
            "more effective technique or extend the slot" % (dwell, slot)
        )
    return {
        "state": state,
        "technique": plan["technique"].strip().lower(),
        "technique_effectiveness": factor,
        "relaxation_time_s": tau,
        "required_dwell_s": dwell,
        "fits_available_slot": fits,
        "findings": findings,
        "proceed_to_measurement": False,
    }
