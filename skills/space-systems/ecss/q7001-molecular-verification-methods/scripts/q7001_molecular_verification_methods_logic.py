"""Molecular cleanliness measurement methods and their reduction to a density.

Anchor: ECSS-Q-ST-70-01C, verification clause -- applying the molecular
measurement methods (solvent rinse reduced gravimetrically or by infrared
absorbance, and witness plates standing in for a surface that cannot be
rinsed) and reducing what each returns to a non-volatile residue surface
density comparable with the requirement. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Reduce a gravimetric rinse: the residue weighed from an evaporated aliquot
   is corrected by the solvent blank, divided by the aliquot fraction to
   recover the whole rinse, and divided by the rinsed area.
2. Reduce an infrared rinse: the absorbance is converted to a concentration
   through the path length and the absorptivity of the calibration compound,
   multiplied by the rinse volume for a mass, then treated like the
   gravimetric mass.
3. Correct either for the rinse recovery -- the fraction of the residue the
   solvent and the technique actually lift off the surface.
4. Transfer a witness plate reading to the hardware through the ratio of
   view factors and the ratio of exposure times, and refuse a transfer whose
   ratios have not been declared.
5. Compute the detection floor the method achieves for the area and aliquot
   in use, and report a value below it as a non-detect rather than a number.
6. Grade the density against the requirement, absorbing representation error
   at the boundary with a named tolerance.
"""

import math

__all__ = [
    "DENSITY_TOLERANCE",
    "MG_PER_G",
    "validate_positive",
    "validate_fraction",
    "net_residue_mg",
    "infrared_mass_mg",
    "surface_density_mg_per_m2",
    "apply_rinse_recovery",
    "detection_floor_mg_per_m2",
    "is_non_detect",
    "witness_transfer_ratio",
    "transfer_witness_density",
    "assess_molecular_measurement",
]

# Densities are quotients of measured quantities; absorb representation error
# at the limit instead of relaxing the limit itself.
DENSITY_TOLERANCE = 1e-9

MG_PER_G = 1000.0

_METHODS = ("rinse-gravimetric", "rinse-infrared", "witness-plate")


def _finite(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def validate_positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def validate_fraction(label, value):
    """Return value as a fraction in (0, 1] or raise."""
    number = _finite(label, value)
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must lie in (0, 1], got %r" % (label, value))
    return number


def net_residue_mg(weighed_mg, blank_mg=0.0, aliquot_fraction=1.0):
    """Return the whole-rinse residue mass in mg from a weighed aliquot.

    A blank at or above the weighed residue leaves nothing attributable to the
    surface; the result is then zero or negative and the caller treats it as a
    non-detect rather than as a measured mass.
    """
    weighed = _finite("weighed_mg", weighed_mg)
    if weighed < 0.0:
        raise ValueError("weighed_mg must not be negative, got %r" % (weighed_mg,))
    blank = _finite("blank_mg", blank_mg)
    if blank < 0.0:
        raise ValueError("blank_mg must not be negative, got %r" % (blank_mg,))
    fraction = validate_fraction("aliquot_fraction", aliquot_fraction)
    return (weighed - blank) / fraction


def infrared_mass_mg(absorbance, path_length_cm, absorptivity_l_per_g_cm, volume_ml):
    """Return the residue mass in mg behind an infrared rinse absorbance."""
    value = _finite("absorbance", absorbance)
    if value < 0.0:
        raise ValueError("absorbance must not be negative, got %r" % (absorbance,))
    path = validate_positive("path_length_cm", path_length_cm)
    absorptivity = validate_positive(
        "absorptivity_l_per_g_cm", absorptivity_l_per_g_cm
    )
    volume = validate_positive("volume_ml", volume_ml)
    # Beer-Lambert: concentration in g/L, volume in mL converted to litres.
    concentration_g_per_l = value / (absorptivity * path)
    return concentration_g_per_l * (volume / 1000.0) * MG_PER_G


def surface_density_mg_per_m2(mass_mg, area_m2):
    """Return the residue surface density in mg per square metre."""
    mass = _finite("mass_mg", mass_mg)
    area = validate_positive("area_m2", area_m2)
    return mass / area


def apply_rinse_recovery(density, recovery_fraction):
    """Return the density scaled up for the residue the rinse left behind."""
    value = _finite("density", density)
    recovery = validate_fraction("recovery_fraction", recovery_fraction)
    return value / recovery


def detection_floor_mg_per_m2(readability_mg, area_m2, aliquot_fraction=1.0,
                              recovery_fraction=1.0):
    """Return the smallest surface density the reduction chain can resolve."""
    readability = validate_positive("readability_mg", readability_mg)
    area = validate_positive("area_m2", area_m2)
    fraction = validate_fraction("aliquot_fraction", aliquot_fraction)
    recovery = validate_fraction("recovery_fraction", recovery_fraction)
    return readability / (fraction * recovery * area)


def is_non_detect(density, floor):
    """Return True when the density does not clear the method detection floor."""
    value = _finite("density", density)
    limit = validate_positive("floor", floor)
    return value < limit or math.isclose(value, limit, rel_tol=DENSITY_TOLERANCE,
                                         abs_tol=0.0)


def witness_transfer_ratio(view_factor_hardware, view_factor_witness,
                           exposure_hours_hardware, exposure_hours_witness):
    """Return the factor scaling a witness plate density onto the hardware."""
    vf_hardware = validate_positive("view_factor_hardware", view_factor_hardware)
    vf_witness = validate_positive("view_factor_witness", view_factor_witness)
    hours_hardware = validate_positive(
        "exposure_hours_hardware", exposure_hours_hardware
    )
    hours_witness = validate_positive("exposure_hours_witness", exposure_hours_witness)
    if vf_hardware > 1.0 or vf_witness > 1.0:
        raise ValueError("a view factor cannot exceed unity")
    return (vf_hardware / vf_witness) * (hours_hardware / hours_witness)


def transfer_witness_density(witness_density, transfer_ratio):
    """Return the hardware surface density implied by a witness plate reading."""
    density = _finite("witness_density", witness_density)
    if density < 0.0:
        raise ValueError("witness_density must not be negative")
    ratio = validate_positive("transfer_ratio", transfer_ratio)
    return density * ratio


def assess_molecular_measurement(spec):
    """Reduce one molecular measurement and grade it against the allowed density.

    spec keys: method, area_m2, allowed_density_mg_per_m2, readability_mg, plus
    the per-method inputs -- weighed_mg/blank_mg/aliquot_fraction for a
    gravimetric rinse, absorbance/path_length_cm/absorptivity_l_per_g_cm/
    volume_ml for an infrared rinse, witness_density_mg_per_m2 with the four
    transfer inputs for a witness plate. Optional recovery_fraction.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("method", "area_m2", "allowed_density_mg_per_m2", "readability_mg"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    method = spec["method"]
    if not isinstance(method, str) or method.strip().lower() not in _METHODS:
        raise ValueError("method must be one of %s, got %r" % (_METHODS, method))
    method = method.strip().lower()
    area = validate_positive("area_m2", spec["area_m2"])
    allowed = validate_positive(
        "allowed_density_mg_per_m2", spec["allowed_density_mg_per_m2"]
    )
    aliquot = validate_fraction("aliquot_fraction", spec.get("aliquot_fraction", 1.0))
    recovery = validate_fraction(
        "recovery_fraction", spec.get("recovery_fraction", 1.0)
    )
    findings = []
    if method == "rinse-gravimetric":
        if "weighed_mg" not in spec:
            raise ValueError("a gravimetric rinse needs weighed_mg")
        mass = net_residue_mg(spec["weighed_mg"], spec.get("blank_mg", 0.0), aliquot)
        density = surface_density_mg_per_m2(mass, area)
    elif method == "rinse-infrared":
        for key in ("absorbance", "path_length_cm", "absorptivity_l_per_g_cm",
                    "volume_ml"):
            if key not in spec:
                raise ValueError("an infrared rinse needs '%s'" % key)
        mass = infrared_mass_mg(
            spec["absorbance"],
            spec["path_length_cm"],
            spec["absorptivity_l_per_g_cm"],
            spec["volume_ml"],
        )
        mass = (mass - _finite("blank_mg", spec.get("blank_mg", 0.0))) / aliquot
        density = surface_density_mg_per_m2(mass, area)
    else:
        for key in ("witness_density_mg_per_m2", "view_factor_hardware",
                    "view_factor_witness", "exposure_hours_hardware",
                    "exposure_hours_witness"):
            if key not in spec:
                raise ValueError(
                    "a witness-plate transfer needs '%s'; an undeclared ratio "
                    "cannot be assumed to be unity" % key
                )
        ratio = witness_transfer_ratio(
            spec["view_factor_hardware"],
            spec["view_factor_witness"],
            spec["exposure_hours_hardware"],
            spec["exposure_hours_witness"],
        )
        density = transfer_witness_density(spec["witness_density_mg_per_m2"], ratio)
        findings.append(
            "density derived from a witness plate through a transfer ratio of "
            "%.6g; it stands in for the surface and does not measure it" % ratio
        )
    if method != "witness-plate":
        density = apply_rinse_recovery(density, recovery)
    floor = detection_floor_mg_per_m2(
        spec["readability_mg"], area, aliquot, recovery
    )
    non_detect = density <= 0.0 or is_non_detect(density, floor)
    if non_detect:
        findings.append(
            "reduced density %.6g mg/m2 does not clear the %.6g mg/m2 detection "
            "floor; report a non-detect, not a value" % (density, floor)
        )
    if floor > allowed:
        findings.append(
            "detection floor %.6g mg/m2 sits above the allowed %.6g mg/m2; the "
            "method cannot substantiate this requirement" % (floor, allowed)
        )
    compliant = density < allowed or math.isclose(
        density, allowed, rel_tol=DENSITY_TOLERANCE, abs_tol=0.0
    )
    if not compliant:
        findings.append(
            "residue density %.6g mg/m2 exceeds the allowed %.6g mg/m2"
            % (density, allowed)
        )
    return {
        "method": method,
        "density_mg_per_m2": density,
        "detection_floor_mg_per_m2": floor,
        "allowed_density_mg_per_m2": allowed,
        "non_detect": non_detect,
        "compliant": compliant and floor <= allowed,
        "findings": findings,
    }
