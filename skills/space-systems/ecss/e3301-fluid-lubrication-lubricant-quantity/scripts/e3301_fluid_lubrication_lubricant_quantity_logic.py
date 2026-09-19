"""Fluid lubrication: suitability and the quantity of lubricant to be provided.

Anchor: ECSS-E-ST-33-01C clauses 4.7.3.3.1 (fluid lubrication, general -- fluid
lubricants are the choice for high-speed, high-cycle duties) and 4.7.3.3.2 (the
quantity of lubricant provided covers the operating film plus the losses over
the life: evaporation in vacuum, creep along surfaces, absorption into porous
retainers and consumption through the duty). Vacuum mass-loss figures come from
the outgassing screening standard ECSS-Q-ST-70-02. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Say whether the duty is in the fluid-lubrication domain: high sliding speed
   or a high cycle count, and a temperature range a fluid survives.
2. Scale the reference vacuum mass-loss rate to the operating temperature with
   an Arrhenius factor, because the reference figure is measured at a screening
   temperature and evaporation is exponential in temperature.
3. Accumulate the four loss terms over the life: evaporation from the exposed
   free surface, creep along the wetted perimeter reduced by the barrier
   effectiveness, absorption into the retainer, and consumption through the
   actuation count.
4. Add the operating film requirement, apply the quantity design factor, and
   report the charge the mechanism has to be filled with.
5. Compare the charge with the reservoir capacity and with the maximum fill
   fraction of the free volume, because over-filling raises drag and throws
   lubricant out, and is a defect in the same way under-filling is.
"""

import math

__all__ = [
    "MARGIN_TOLERANCE",
    "GAS_CONSTANT_J_PER_MOL_K",
    "KELVIN_OFFSET",
    "FLUID_SPEED_FLOOR_M_S",
    "FLUID_CYCLE_FLOOR",
    "DEFAULT_QUANTITY_FACTOR",
    "DEFAULT_MAX_FILL_FRACTION",
    "validate_positive",
    "validate_non_negative",
    "validate_fraction",
    "arrhenius_factor",
    "evaporation_loss_g",
    "creep_loss_g",
    "absorption_loss_g",
    "consumption_loss_g",
    "loss_budget",
    "required_charge_g",
    "fill_fraction",
    "duty_indication",
    "assess_lubricant_quantity",
]

# Quantity comparisons are sums of products; absorb representation error only.
MARGIN_TOLERANCE = 1e-9

GAS_CONSTANT_J_PER_MOL_K = 8.314462618
KELVIN_OFFSET = 273.15

# Below these a solid film is usually the better answer; at or above them the
# duty is in the fluid domain.
FLUID_SPEED_FLOOR_M_S = 0.15
FLUID_CYCLE_FLOOR = 1.0e5

# The charge carries a design factor over the computed need.
DEFAULT_QUANTITY_FACTOR = 2.0

# Filling more than this fraction of the free volume churns rather than
# lubricates.
DEFAULT_MAX_FILL_FRACTION = 0.30


def validate_positive(label, value):
    """Return value as a strictly positive finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_non_negative(label, value):
    """Return value as a non-negative finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    if number < 0.0:
        raise ValueError("%s must not be negative, got %r" % (label, value))
    return number


def validate_fraction(label, value):
    """Return value as a float in the closed interval zero to one."""
    number = validate_non_negative(label, value)
    if number > 1.0:
        raise ValueError("%s must not exceed 1.0, got %r" % (label, value))
    return number


def arrhenius_factor(temperature_c, reference_temperature_c, activation_energy_kj_per_mol):
    """Return the factor scaling a reference loss rate to an operating temperature."""
    for label, value in (
        ("temperature_c", temperature_c),
        ("reference_temperature_c", reference_temperature_c),
    ):
        if not isinstance(value, (int, float)) or isinstance(value, bool):
            raise ValueError("%s must be a real number" % label)
        if not math.isfinite(float(value)):
            raise ValueError("%s must be finite" % label)
    energy = validate_positive(
        "activation_energy_kj_per_mol", activation_energy_kj_per_mol
    )
    kelvin = float(temperature_c) + KELVIN_OFFSET
    reference_kelvin = float(reference_temperature_c) + KELVIN_OFFSET
    if kelvin <= 0.0 or reference_kelvin <= 0.0:
        raise ValueError("temperatures must be above absolute zero")
    exponent = (
        energy
        * 1000.0
        / GAS_CONSTANT_J_PER_MOL_K
        * (1.0 / reference_kelvin - 1.0 / kelvin)
    )
    return math.exp(exponent)


def evaporation_loss_g(exposed_area_cm2, life_years, reference_rate_g_per_cm2_year,
                       temperature_c, reference_temperature_c,
                       activation_energy_kj_per_mol):
    """Return the mass lost to vacuum evaporation over the life, in g."""
    area = validate_non_negative("exposed_area_cm2", exposed_area_cm2)
    years = validate_non_negative("life_years", life_years)
    rate = validate_non_negative(
        "reference_rate_g_per_cm2_year", reference_rate_g_per_cm2_year
    )
    factor = arrhenius_factor(
        temperature_c, reference_temperature_c, activation_energy_kj_per_mol
    )
    return area * years * rate * factor


def creep_loss_g(wetted_perimeter_mm, life_years, creep_rate_g_per_mm_year,
                 barrier_effectiveness=0.0):
    """Return the mass lost to surface creep over the life, in g."""
    perimeter = validate_non_negative("wetted_perimeter_mm", wetted_perimeter_mm)
    years = validate_non_negative("life_years", life_years)
    rate = validate_non_negative("creep_rate_g_per_mm_year", creep_rate_g_per_mm_year)
    effectiveness = validate_fraction("barrier_effectiveness", barrier_effectiveness)
    return perimeter * years * rate * (1.0 - effectiveness)


def absorption_loss_g(retainer_mass_g, absorption_fraction):
    """Return the mass absorbed into a porous retainer, in g."""
    mass = validate_non_negative("retainer_mass_g", retainer_mass_g)
    fraction = validate_fraction("absorption_fraction", absorption_fraction)
    return mass * fraction


def consumption_loss_g(cycles, loss_per_million_cycles_g):
    """Return the mass consumed by the duty itself, in g."""
    count = validate_non_negative("cycles", cycles)
    rate = validate_non_negative("loss_per_million_cycles_g", loss_per_million_cycles_g)
    return count / 1.0e6 * rate


def loss_budget(spec):
    """Return the four life loss terms and their total, in g.

    spec keys: exposed_area_cm2, life_years, reference_rate_g_per_cm2_year,
    temperature_c, reference_temperature_c, activation_energy_kj_per_mol,
    wetted_perimeter_mm, creep_rate_g_per_mm_year, retainer_mass_g,
    absorption_fraction, cycles, loss_per_million_cycles_g, optional
    barrier_effectiveness.
    """
    if not isinstance(spec, dict):
        raise ValueError("loss spec must be a mapping")
    required = (
        "exposed_area_cm2",
        "life_years",
        "reference_rate_g_per_cm2_year",
        "temperature_c",
        "reference_temperature_c",
        "activation_energy_kj_per_mol",
        "wetted_perimeter_mm",
        "creep_rate_g_per_mm_year",
        "retainer_mass_g",
        "absorption_fraction",
        "cycles",
        "loss_per_million_cycles_g",
    )
    for key in required:
        if key not in spec:
            raise ValueError("loss spec missing required key '%s'" % key)
    evaporation = evaporation_loss_g(
        spec["exposed_area_cm2"],
        spec["life_years"],
        spec["reference_rate_g_per_cm2_year"],
        spec["temperature_c"],
        spec["reference_temperature_c"],
        spec["activation_energy_kj_per_mol"],
    )
    creep = creep_loss_g(
        spec["wetted_perimeter_mm"],
        spec["life_years"],
        spec["creep_rate_g_per_mm_year"],
        spec.get("barrier_effectiveness", 0.0),
    )
    absorption = absorption_loss_g(spec["retainer_mass_g"], spec["absorption_fraction"])
    consumption = consumption_loss_g(spec["cycles"], spec["loss_per_million_cycles_g"])
    total = evaporation + creep + absorption + consumption
    return {
        "evaporation_g": evaporation,
        "creep_g": creep,
        "absorption_g": absorption,
        "consumption_g": consumption,
        "total_g": total,
    }


def required_charge_g(operating_film_g, losses_total_g, quantity_factor=DEFAULT_QUANTITY_FACTOR):
    """Return the lubricant charge the mechanism is filled with, in g."""
    film = validate_positive("operating_film_g", operating_film_g)
    losses = validate_non_negative("losses_total_g", losses_total_g)
    factor = validate_positive("quantity_factor", quantity_factor)
    if factor < 1.0:
        raise ValueError("quantity_factor must be at least 1.0, got %r" % (quantity_factor,))
    return (film + losses) * factor


def fill_fraction(charge_g, density_g_per_cm3, free_volume_cm3):
    """Return the fraction of the free volume the charge occupies."""
    charge = validate_non_negative("charge_g", charge_g)
    density = validate_positive("density_g_per_cm3", density_g_per_cm3)
    volume = validate_positive("free_volume_cm3", free_volume_cm3)
    return charge / density / volume


def duty_indication(duty):
    """Say whether the duty belongs in the fluid-lubrication domain.

    duty keys: sliding_speed_m_s, required_cycles, temperature_c (pair),
    fluid_temperature_c (pair, the rated range of the candidate fluid).
    """
    if not isinstance(duty, dict):
        raise ValueError("duty must be a mapping")
    for key in ("sliding_speed_m_s", "required_cycles", "temperature_c", "fluid_temperature_c"):
        if key not in duty:
            raise ValueError("duty missing required key '%s'" % key)
    speed = validate_non_negative("sliding_speed_m_s", duty["sliding_speed_m_s"])
    cycles = validate_non_negative("required_cycles", duty["required_cycles"])
    ranges = {}
    for key in ("temperature_c", "fluid_temperature_c"):
        value = duty[key]
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError("duty '%s' must be a (low, high) pair" % key)
        low = float(value[0])
        high = float(value[1])
        if not math.isfinite(low) or not math.isfinite(high):
            raise ValueError("duty '%s' limits must be finite" % key)
        if low > high:
            raise ValueError("duty '%s' is inverted" % key)
        ranges[key] = (low, high)
    duty_low, duty_high = ranges["temperature_c"]
    fluid_low, fluid_high = ranges["fluid_temperature_c"]
    fast = speed >= FLUID_SPEED_FLOOR_M_S or math.isclose(
        speed, FLUID_SPEED_FLOOR_M_S, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    high_cycle = cycles >= FLUID_CYCLE_FLOOR or math.isclose(
        cycles, FLUID_CYCLE_FLOOR, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    )
    covered = (
        fluid_low <= duty_low
        or math.isclose(fluid_low, duty_low, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)
    ) and (
        fluid_high >= duty_high
        or math.isclose(fluid_high, duty_high, rel_tol=0.0, abs_tol=MARGIN_TOLERANCE)
    )
    findings = []
    if not (fast or high_cycle):
        findings.append(
            "duty is slow (%g m/s) and low-cycle (%g); a dry film is the indicated "
            "choice rather than a fluid" % (speed, cycles)
        )
    if not covered:
        findings.append(
            "fluid rated %g..%g C does not cover the duty range %g..%g C"
            % (fluid_low, fluid_high, duty_low, duty_high)
        )
    return {
        "fast_duty": fast,
        "high_cycle_duty": high_cycle,
        "temperature_covered": covered,
        "indicated": not findings,
        "findings": findings,
    }


def assess_lubricant_quantity(spec):
    """Run the full clause 4.7.3.3.1 and 4.7.3.3.2 assessment.

    spec keys: duty (see duty_indication), losses (see loss_budget),
    operating_film_g, density_g_per_cm3, free_volume_cm3, reservoir_capacity_g,
    optional quantity_factor and max_fill_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "duty",
        "losses",
        "operating_film_g",
        "density_g_per_cm3",
        "free_volume_cm3",
        "reservoir_capacity_g",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    indication = duty_indication(spec["duty"])
    losses = loss_budget(spec["losses"])
    charge = required_charge_g(
        spec["operating_film_g"],
        losses["total_g"],
        spec.get("quantity_factor", DEFAULT_QUANTITY_FACTOR),
    )
    capacity = validate_positive("reservoir_capacity_g", spec["reservoir_capacity_g"])
    fraction = fill_fraction(charge, spec["density_g_per_cm3"], spec["free_volume_cm3"])
    max_fraction = validate_fraction(
        "max_fill_fraction", spec.get("max_fill_fraction", DEFAULT_MAX_FILL_FRACTION)
    )
    findings = list(indication["findings"])
    if charge > capacity and not math.isclose(
        charge, capacity, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "required charge %.4f g exceeds the reservoir capacity %.4f g"
            % (charge, capacity)
        )
    if fraction > max_fraction and not math.isclose(
        fraction, max_fraction, rel_tol=MARGIN_TOLERANCE, abs_tol=0.0
    ):
        findings.append(
            "charge fills %.4f of the free volume, above the %.4f fill fraction; "
            "the mechanism will churn rather than lubricate" % (fraction, max_fraction)
        )
    dominant = max(
        ("evaporation", losses["evaporation_g"]),
        ("creep", losses["creep_g"]),
        ("absorption", losses["absorption_g"]),
        ("consumption", losses["consumption_g"]),
        key=lambda item: item[1],
    )[0]
    return {
        "indication": indication,
        "losses": losses,
        "dominant_loss": dominant,
        "required_charge_g": charge,
        "fill_fraction": fraction,
        "reservoir_capacity_g": capacity,
        "compliant": not findings,
        "findings": findings,
    }
