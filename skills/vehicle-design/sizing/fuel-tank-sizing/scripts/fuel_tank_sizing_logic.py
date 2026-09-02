#!/usr/bin/env python3
"""Fuel tank sizing logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, far-25/cs-25: gated
false): the fuel volume is the fuel mass divided by the fuel density;
jet fuel density is commonly about 0.8 kg per liter, or 800 kg per
cubic meter. The tank must hold the usable fuel volume plus the
ullage allowance for fuel expansion and venting space, so the required
tank volume is the usable fuel volume times (1 + ullage fraction).
The fits verdict subtracts the required tank volume from the volume
available in the wing and fuselage tanks; a non-negative margin fits,
and the margin percent is relative to the required volume.

Units: fuel mass in kg, fuel density in kg per liter, volumes in
liters (cubic meters for the structure check), ullage as a unitless
fraction. Invalid inputs raise ValueError throughout.
"""


def fuel_volume_liters(fuel_mass_kg, fuel_density_kg_per_l):
    """Usable fuel volume in liters.

    Returns fuel_mass_kg / fuel_density_kg_per_l. Raises ValueError if
    either input is not positive.
    """
    if fuel_mass_kg <= 0:
        raise ValueError("fuel mass must be positive, got %r" % (fuel_mass_kg,))
    if fuel_density_kg_per_l <= 0:
        raise ValueError(
            "fuel density must be positive, got %r" % (fuel_density_kg_per_l,)
        )
    return fuel_mass_kg / fuel_density_kg_per_l


def fuel_volume_m3(fuel_mass_kg, fuel_density_kg_per_l):
    """Usable fuel volume in cubic meters.

    Returns fuel_volume_liters / 1000. Raises ValueError if either
    input is not positive.
    """
    return fuel_volume_liters(fuel_mass_kg, fuel_density_kg_per_l) / 1000.0


def tank_volume_with_ullage(usable_volume_liters, ullage_fraction):
    """Required tank volume including the ullage allowance (liters).

    Returns usable_volume_liters * (1 + ullage_fraction). Raises
    ValueError if usable volume is not positive or ullage_fraction is
    negative.
    """
    if usable_volume_liters <= 0:
        raise ValueError(
            "usable volume must be positive, got %r" % (usable_volume_liters,)
        )
    if ullage_fraction < 0:
        raise ValueError(
            "ullage fraction must be non-negative, got %r" % (ullage_fraction,)
        )
    return usable_volume_liters * (1.0 + ullage_fraction)


def required_tank_volume(fuel_mass_kg, fuel_density_kg_per_l, ullage_fraction):
    """Required tank volume for the fuel mass (liters).

    Convenience wrapper: fuel volume at the given density, then the
    ullage allowance applied. Raises ValueError if any input is
    invalid per the underlying functions.
    """
    usable = fuel_volume_liters(fuel_mass_kg, fuel_density_kg_per_l)
    return tank_volume_with_ullage(usable, ullage_fraction)


def check_available_volume(required_volume_liters, available_volume_liters):
    """Fits verdict for the required tank volume.

    margin_volume = available - required; fits is True when the margin
    is non-negative; margin_percent is margin_volume / required * 100.
    Returns {"fits": bool, "margin_volume": ..., "margin_percent": ...}.

    Raises ValueError if either volume is not positive.
    """
    if required_volume_liters <= 0:
        raise ValueError(
            "required volume must be positive, got %r" % (required_volume_liters,)
        )
    if available_volume_liters <= 0:
        raise ValueError(
            "available volume must be positive, got %r" % (available_volume_liters,)
        )
    margin_volume = available_volume_liters - required_volume_liters
    margin_percent = margin_volume / required_volume_liters * 100.0
    return {
        "fits": margin_volume >= 0,
        "margin_volume": margin_volume,
        "margin_percent": margin_percent,
    }
