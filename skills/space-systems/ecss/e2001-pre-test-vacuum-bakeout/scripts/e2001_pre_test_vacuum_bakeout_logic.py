"""Pre-test vacuum bakeout of RF hardware ahead of multipactor testing.

Anchor: ECSS-E-ST-20-01C clause 6.2 (vacuum bakeout performed on
equipment or components before any multipactor test). Paraphrased into
an implementable procedure; no standard text is reproduced.

Stdlib only, offline, deterministic. The module sizes and grades a
bakeout: it checks the setpoint against the item's non-operating
temperature allowance, converts a dwell at that setpoint into an
equivalent dwell at the reference temperature the requirement is written
at, tracks the power-law decay of the outgassing rate, grades the
chamber pressure actually reached, and decides whether the hold between
bakeout completion and test start preserved or voided the bakeout.
"""

import math

ABSOLUTE_ZERO_C = -273.15

# Boltzmann constant in electronvolt per kelvin, for the desorption
# Arrhenius relation.
BOLTZMANN_EV_PER_K = 8.617333262e-5

# Desorption activation energy used when the programme does not state one.
DEFAULT_ACTIVATION_ENERGY_EV = 0.60

# Exponent of the power-law outgassing decay when none is stated.
DEFAULT_DECAY_EXPONENT = 1.0

# The decay relation is anchored one hour after pump-down starts.
DECAY_REFERENCE_HOURS = 1.0

# Boundary tolerance: a dwell or a pressure that lands exactly on its
# requirement is compliant, and a value assembled from several terms can
# sit a few units in the last place away from it. Absorb the
# representation error here rather than relaxing the requirement.
REL_TOL = 1e-9

_INERT_BACKFILL = {
    "dry-nitrogen": "inert",
    "gaseous-nitrogen": "inert",
    "dry-argon": "inert",
    "helium": "inert",
}

_AMBIENT_BACKFILL = {
    "ambient-air": "ambient",
    "room-air": "ambient",
    "unfiltered-air": "ambient",
    "cleanroom-air": "ambient",
}


def _real(value, label):
    try:
        number = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return number


def _positive(value, label):
    number = _real(value, label)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return number


def _non_negative(value, label):
    number = _real(value, label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def celsius_to_kelvin(temperature_c):
    """Absolute temperature, rejecting anything at or below absolute zero."""
    value = _real(temperature_c, "temperature_c")
    kelvin = value - ABSOLUTE_ZERO_C
    if kelvin <= 0.0:
        raise ValueError(
            "temperature_c must lie above absolute zero (%g C), got %r"
            % (ABSOLUTE_ZERO_C, temperature_c)
        )
    return kelvin


def evaluate_bakeout_setpoint(
    setpoint_c, max_allowable_c, thermal_margin_k, minimum_effective_c
):
    """Check a bakeout setpoint against its upper and lower bounds.

    The setpoint has to sit at or below the item's non-operating
    allowance reduced by the thermal margin, and at or above the
    temperature below which desorption is too slow to be worth running.
    """
    setpoint = _real(setpoint_c, "setpoint_c")
    ceiling_raw = _real(max_allowable_c, "max_allowable_c")
    margin = _non_negative(thermal_margin_k, "thermal_margin_k")
    floor_value = _real(minimum_effective_c, "minimum_effective_c")
    celsius_to_kelvin(setpoint)
    ceiling = ceiling_raw - margin
    if ceiling < floor_value:
        raise ValueError(
            "no usable bakeout window: allowance %g C minus margin %g K is below "
            "the minimum effective temperature %g C" % (ceiling_raw, margin, floor_value)
        )
    at_ceiling = math.isclose(setpoint, ceiling, rel_tol=REL_TOL, abs_tol=1e-12)
    at_floor = math.isclose(setpoint, floor_value, rel_tol=REL_TOL, abs_tol=1e-12)
    over = setpoint > ceiling and not at_ceiling
    under = setpoint < floor_value and not at_floor
    return {
        "setpoint_c": setpoint,
        "derated_ceiling_c": ceiling,
        "minimum_effective_c": floor_value,
        "exceeds_allowance": over,
        "below_effective_floor": under,
        "headroom_k": ceiling - setpoint,
        "acceptable": not over and not under,
    }


def thermal_acceleration_factor(
    bakeout_c, reference_c, activation_energy_ev=DEFAULT_ACTIVATION_ENERGY_EV
):
    """How much faster desorption runs at the bakeout temperature.

    Arrhenius ratio between the bakeout and the reference temperature the
    requirement is written at.
    """
    energy = _positive(activation_energy_ev, "activation_energy_ev")
    t_bake = celsius_to_kelvin(bakeout_c)
    t_ref = celsius_to_kelvin(reference_c)
    exponent = (energy / BOLTZMANN_EV_PER_K) * ((1.0 / t_ref) - (1.0 / t_bake))
    return math.exp(exponent)


def equivalent_reference_hours(
    bakeout_c, reference_c, bakeout_hours,
    activation_energy_ev=DEFAULT_ACTIVATION_ENERGY_EV,
):
    """Dwell at the bakeout setpoint expressed at the reference temperature."""
    hours = _non_negative(bakeout_hours, "bakeout_hours")
    return hours * thermal_acceleration_factor(bakeout_c, reference_c, activation_energy_ev)


def evaluate_bakeout_dwell(
    bakeout_c, reference_c, bakeout_hours, required_reference_hours,
    activation_energy_ev=DEFAULT_ACTIVATION_ENERGY_EV,
):
    """Grade a dwell against the required equivalent dwell."""
    required = _positive(required_reference_hours, "required_reference_hours")
    achieved = equivalent_reference_hours(
        bakeout_c, reference_c, bakeout_hours, activation_energy_ev
    )
    at_requirement = math.isclose(achieved, required, rel_tol=REL_TOL, abs_tol=0.0)
    return {
        "achieved_reference_hours": achieved,
        "required_reference_hours": required,
        "at_requirement": at_requirement,
        "coverage": achieved / required,
        "sufficient": achieved > required or at_requirement,
    }


def outgassing_rate(
    initial_rate, elapsed_hours, decay_exponent=DEFAULT_DECAY_EXPONENT,
    reference_hours=DECAY_REFERENCE_HOURS,
):
    """Outgassing rate after a dwell, following the power-law decay.

    Before the decay anchor the rate is held at its initial value; after
    it the rate falls as elapsed time to the power of the decay exponent.
    """
    q_zero = _positive(initial_rate, "initial_rate")
    elapsed = _non_negative(elapsed_hours, "elapsed_hours")
    alpha = _positive(decay_exponent, "decay_exponent")
    anchor = _positive(reference_hours, "reference_hours")
    if elapsed <= anchor:
        return q_zero
    return q_zero * ((elapsed / anchor) ** (-alpha))


def hours_to_reach_outgassing_target(
    initial_rate, target_rate, decay_exponent=DEFAULT_DECAY_EXPONENT,
    reference_hours=DECAY_REFERENCE_HOURS,
):
    """Dwell needed for the outgassing rate to fall to a target."""
    q_zero = _positive(initial_rate, "initial_rate")
    target = _positive(target_rate, "target_rate")
    alpha = _positive(decay_exponent, "decay_exponent")
    anchor = _positive(reference_hours, "reference_hours")
    if target >= q_zero:
        return anchor
    return anchor * ((q_zero / target) ** (1.0 / alpha))


def evaluate_chamber_pressure(measured_mbar, required_mbar):
    """Grade the pressure the chamber actually reached during bakeout."""
    measured = _positive(measured_mbar, "measured_mbar")
    required = _positive(required_mbar, "required_mbar")
    at_limit = math.isclose(measured, required, rel_tol=REL_TOL, abs_tol=0.0)
    return {
        "measured_mbar": measured,
        "required_mbar": required,
        "at_limit": at_limit,
        "decades_of_margin": math.log10(required / measured),
        "compliant": measured < required or at_limit,
    }


def categorize_backfill_gas(gas):
    """Return 'inert' or 'ambient' for a repressurisation medium."""
    if not isinstance(gas, str):
        raise ValueError("gas must be a string, got %r" % (gas,))
    key = gas.strip().lower().replace(" ", "-").replace("_", "-")
    if not key:
        raise ValueError("gas must not be empty")
    if key in _INERT_BACKFILL:
        return _INERT_BACKFILL[key]
    if key in _AMBIENT_BACKFILL:
        return _AMBIENT_BACKFILL[key]
    raise ValueError("uncategorized repressurisation medium %r" % (gas,))


def evaluate_post_bakeout_hold(hold_hours, allowed_hold_hours, backfill_gas):
    """Decide whether the wait between bakeout and test voided the bakeout.

    A break back to ambient air re-adsorbs a monolayer and voids the
    bakeout outright. A dry inert backfill preserves it for a bounded
    hold only.
    """
    hold = _non_negative(hold_hours, "hold_hours")
    allowed = _positive(allowed_hold_hours, "allowed_hold_hours")
    category = categorize_backfill_gas(backfill_gas)
    if category == "ambient":
        return {
            "gas_category": category,
            "hold_hours": hold,
            "allowed_hold_hours": allowed,
            "at_limit": False,
            "bakeout_still_valid": False,
            "reason": "exposure to ambient air voids the bakeout",
        }
    at_limit = math.isclose(hold, allowed, rel_tol=REL_TOL, abs_tol=0.0)
    valid = hold < allowed or at_limit
    return {
        "gas_category": category,
        "hold_hours": hold,
        "allowed_hold_hours": allowed,
        "at_limit": at_limit,
        "bakeout_still_valid": valid,
        "reason": "" if valid else "inert hold exceeded its allowance",
    }


def assess_bakeout_readiness(record):
    """Aggregate the clause 6.2 checks into a findings list."""
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping")
    required_keys = (
        "setpoint_c",
        "max_allowable_c",
        "thermal_margin_k",
        "minimum_effective_c",
        "reference_c",
        "bakeout_hours",
        "required_reference_hours",
        "chamber_pressure_mbar",
        "required_pressure_mbar",
        "hold_hours",
        "allowed_hold_hours",
        "backfill_gas",
    )
    for key in required_keys:
        if key not in record:
            raise ValueError("record missing required key %r" % (key,))
    findings = []
    energy = record.get("activation_energy_ev", DEFAULT_ACTIVATION_ENERGY_EV)

    setpoint = evaluate_bakeout_setpoint(
        record["setpoint_c"],
        record["max_allowable_c"],
        record["thermal_margin_k"],
        record["minimum_effective_c"],
    )
    if setpoint["exceeds_allowance"]:
        findings.append("bakeout setpoint exceeds the derated non-operating allowance")
    if setpoint["below_effective_floor"]:
        findings.append("bakeout setpoint sits below the effective desorption floor")

    dwell = evaluate_bakeout_dwell(
        record["setpoint_c"],
        record["reference_c"],
        record["bakeout_hours"],
        record["required_reference_hours"],
        energy,
    )
    if not dwell["sufficient"]:
        findings.append("equivalent bakeout dwell falls short of the requirement")

    pressure = evaluate_chamber_pressure(
        record["chamber_pressure_mbar"], record["required_pressure_mbar"]
    )
    if not pressure["compliant"]:
        findings.append("chamber pressure during bakeout stayed above the requirement")

    hold = evaluate_post_bakeout_hold(
        record["hold_hours"], record["allowed_hold_hours"], record["backfill_gas"]
    )
    if not hold["bakeout_still_valid"]:
        findings.append("post-bakeout hold voided the bakeout: %s" % hold["reason"])

    outgassing = None
    if "initial_outgassing_rate" in record and "target_outgassing_rate" in record:
        alpha = record.get("decay_exponent", DEFAULT_DECAY_EXPONENT)
        needed = hours_to_reach_outgassing_target(
            record["initial_outgassing_rate"], record["target_outgassing_rate"], alpha
        )
        reached = outgassing_rate(
            record["initial_outgassing_rate"], record["bakeout_hours"], alpha
        )
        target = _positive(record["target_outgassing_rate"], "target_outgassing_rate")
        met = reached < target or math.isclose(reached, target, rel_tol=REL_TOL, abs_tol=0.0)
        outgassing = {
            "hours_needed": needed,
            "rate_at_end_of_dwell": reached,
            "target_rate": target,
            "target_met": met,
        }
        if not met:
            findings.append("outgassing rate at end of dwell is above the target")
    else:
        findings.append("no outgassing-rate target on record for the bakeout")

    return {
        "setpoint": setpoint,
        "dwell": dwell,
        "pressure": pressure,
        "hold": hold,
        "outgassing": outgassing,
        "findings": sorted(findings),
        "ready_for_test": not findings,
    }
