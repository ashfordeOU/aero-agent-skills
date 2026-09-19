"""Direct infrared reflection measurement of organic contamination on surfaces.

Anchor: ECSS-Q-ST-70-05C, direct method. Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the surface record: finish, specular reflectance, reachability and
   the measurement spot against the available aperture.
2. Select the reflection technique the finish supports (grazing-incidence
   reflection-absorption, diffuse reflectance, or attenuated total reflection).
3. Validate the incidence angle inside that technique's window and form the
   double-pass path enhancement 2 / cos(theta) where the geometry supports one.
4. Difference the contaminated reading against a clean reference area of the
   same substrate and finish.
5. Convert the net absorbance into a film thickness through the band
   absorptivity and the path enhancement, then into an areal mass through the
   contaminant density.
"""

import math

__all__ = [
    "ATR_SAMPLING_DEPTH_UM",
    "DIFFUSE_REFLECTANCE",
    "GRAZING_MAX_ANGLE_DEG",
    "GRAZING_MIN_ANGLE_DEG",
    "INTERNAL_REFLECTION",
    "MIN_SPECULAR_REFLECTANCE",
    "REFLECTION_ABSORPTION",
    "TECHNIQUE_ANGLE_WINDOW",
    "UM_TO_UG_PER_CM2_PER_UNIT_DENSITY",
    "areal_mass_ug_per_cm2",
    "assess_direct_measurement",
    "film_thickness_um",
    "net_reflection_absorbance",
    "path_enhancement",
    "select_technique",
    "validate_incidence_angle",
    "validate_surface",
]

REFLECTION_ABSORPTION = "grazing-incidence-reflection-absorption"
DIFFUSE_REFLECTANCE = "diffuse-reflectance"
INTERNAL_REFLECTION = "attenuated-total-reflection"

# A grazing reading needs a substrate that returns the specular beam; below
# this reflectance the technique has no beam to work with.
MIN_SPECULAR_REFLECTANCE = 0.60

GRAZING_MIN_ANGLE_DEG = 60.0
GRAZING_MAX_ANGLE_DEG = 88.0

TECHNIQUE_ANGLE_WINDOW = {
    REFLECTION_ABSORPTION: (GRAZING_MIN_ANGLE_DEG, GRAZING_MAX_ANGLE_DEG),
    DIFFUSE_REFLECTANCE: (0.0, 60.0),
    INTERNAL_REFLECTION: (30.0, 60.0),
}

# The evanescent field of an internal reflection element samples a bounded
# depth; a thicker film saturates and the reading becomes a lower bound.
ATR_SAMPLING_DEPTH_UM = 2.0

# 1 um of a 1 g/cm3 film is 1e-4 cm * 1 g/cm3 = 1e-4 g/cm2 = 100 ug/cm2.
UM_TO_UG_PER_CM2_PER_UNIT_DENSITY = 100.0

_FINISHES = ("specular", "diffuse", "compliant")


def _positive(label, value, allow_zero=False):
    """Return value as a finite float, raising on a non-numeric or non-positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _real(label, value):
    """Return value as a finite float of any sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_surface(record):
    """Return the normalised surface record for a direct reflection reading.

    Keys: finish, specular_reflectance (0..1), accessible (bool),
    spot_diameter_mm, aperture_diameter_mm.
    """
    if not isinstance(record, dict):
        raise ValueError("surface record must be a mapping")
    for key in ("finish", "specular_reflectance", "accessible",
                "spot_diameter_mm", "aperture_diameter_mm"):
        if key not in record:
            raise ValueError("surface record missing required key '%s'" % key)
    finish = record["finish"]
    if finish not in _FINISHES:
        raise ValueError(
            "finish must be one of %s, got %r" % (", ".join(_FINISHES), finish)
        )
    reflectance = _positive("specular_reflectance", record["specular_reflectance"],
                            allow_zero=True)
    if reflectance > 1.0:
        raise ValueError("specular_reflectance must not exceed unity, got %g"
                         % reflectance)
    accessible = record["accessible"]
    if not isinstance(accessible, bool):
        raise ValueError("accessible must be a boolean, got %r" % (accessible,))
    return {
        "finish": finish,
        "specular_reflectance": reflectance,
        "accessible": accessible,
        "spot_diameter_mm": _positive("spot_diameter_mm", record["spot_diameter_mm"]),
        "aperture_diameter_mm": _positive("aperture_diameter_mm",
                                          record["aperture_diameter_mm"]),
    }


def select_technique(surface):
    """Return (technique, reason) for the validated surface record."""
    norm = validate_surface(surface)
    if not norm["accessible"]:
        raise ValueError(
            "surface is not reachable by the instrument; the direct route does "
            "not apply and the extract route is the alternative"
        )
    if norm["finish"] == "specular":
        if norm["specular_reflectance"] < MIN_SPECULAR_REFLECTANCE and not (
            abs(norm["specular_reflectance"] - MIN_SPECULAR_REFLECTANCE) <= 1e-12
        ):
            return (DIFFUSE_REFLECTANCE, "specular-beam-too-weak-for-grazing")
        return (REFLECTION_ABSORPTION, "specular-substrate-returns-the-beam")
    if norm["finish"] == "diffuse":
        return (DIFFUSE_REFLECTANCE, "scattering-finish-has-no-specular-beam")
    return (INTERNAL_REFLECTION, "compliant-surface-contacts-the-element")


def validate_incidence_angle(angle_deg, technique):
    """Return the incidence angle in degrees, inside the technique's window."""
    if technique not in TECHNIQUE_ANGLE_WINDOW:
        raise ValueError("unknown technique %r" % (technique,))
    angle = _positive("angle_deg", angle_deg, allow_zero=True)
    if angle >= 90.0:
        raise ValueError("angle_deg must be below 90 degrees, got %g" % angle)
    low, high = TECHNIQUE_ANGLE_WINDOW[technique]
    below = angle < low and abs(angle - low) > 1e-12
    above = angle > high and abs(angle - high) > 1e-12
    if below or above:
        raise ValueError(
            "incidence angle %g deg is outside the %s window [%g, %g]"
            % (angle, technique, low, high)
        )
    return angle


def path_enhancement(angle_deg, technique=REFLECTION_ABSORPTION):
    """Return the path-length enhancement factor of the reflection geometry.

    A double-pass specular reflection crosses the film twice at 1/cos(theta)
    each way. Diffuse collection has no single path, so the factor is unity.
    """
    angle = validate_incidence_angle(angle_deg, technique)
    if technique == DIFFUSE_REFLECTANCE:
        return 1.0
    if technique == INTERNAL_REFLECTION:
        return 1.0
    return 2.0 / math.cos(math.radians(angle))


def net_reflection_absorbance(sample_absorbance, reference_absorbance,
                              sample_substrate, reference_substrate):
    """Return the net absorbance after differencing against the clean reference."""
    if not isinstance(sample_substrate, str) or not sample_substrate.strip():
        raise ValueError("sample_substrate must be a non-empty string")
    if not isinstance(reference_substrate, str) or not reference_substrate.strip():
        raise ValueError("reference_substrate must be a non-empty string")
    if sample_substrate != reference_substrate:
        raise ValueError(
            "reference area is %r but the sample is %r; the substrate "
            "absorptions do not cancel" % (reference_substrate, sample_substrate)
        )
    sample = _real("sample_absorbance", sample_absorbance)
    reference = _real("reference_absorbance", reference_absorbance)
    net = sample - reference
    if net < -1.0e-4:
        raise ValueError(
            "clean reference %g absorbs more than the sample %g; the reference "
            "area is not clean" % (reference, sample)
        )
    return net if net > 0.0 else 0.0


def film_thickness_um(net_abs, absorptivity_abs_per_um, enhancement):
    """Return the contaminant film thickness in micrometres."""
    net = _positive("net_abs", net_abs, allow_zero=True)
    absorptivity = _positive("absorptivity_abs_per_um", absorptivity_abs_per_um)
    factor = _positive("enhancement", enhancement)
    return net / (absorptivity * factor)


def areal_mass_ug_per_cm2(thickness_um, density_g_per_cm3):
    """Return the areal mass of the film in ug/cm2."""
    thickness = _positive("thickness_um", thickness_um, allow_zero=True)
    density = _positive("density_g_per_cm3", density_g_per_cm3)
    return thickness * density * UM_TO_UG_PER_CM2_PER_UNIT_DENSITY


def assess_direct_measurement(spec):
    """Run the full direct reflection assessment.

    spec keys: surface, incidence_angle_deg, sample_absorbance,
    reference_absorbance, sample_substrate, reference_substrate,
    absorptivity_abs_per_um, density_g_per_cm3.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("surface", "incidence_angle_deg", "sample_absorbance",
                "reference_absorbance", "sample_substrate", "reference_substrate",
                "absorptivity_abs_per_um", "density_g_per_cm3"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    surface = validate_surface(spec["surface"])
    technique, reason = select_technique(spec["surface"])
    angle = validate_incidence_angle(spec["incidence_angle_deg"], technique)
    factor = path_enhancement(angle, technique)
    net = net_reflection_absorbance(
        spec["sample_absorbance"], spec["reference_absorbance"],
        spec["sample_substrate"], spec["reference_substrate"],
    )
    thickness = film_thickness_um(net, spec["absorptivity_abs_per_um"], factor)
    areal = areal_mass_ug_per_cm2(thickness, spec["density_g_per_cm3"])
    findings = []
    if surface["spot_diameter_mm"] > surface["aperture_diameter_mm"] and abs(
        surface["spot_diameter_mm"] - surface["aperture_diameter_mm"]
    ) > 1e-12:
        findings.append(
            "measurement spot %.2f mm exceeds the available aperture %.2f mm; "
            "part of the beam misses the area of interest"
            % (surface["spot_diameter_mm"], surface["aperture_diameter_mm"])
        )
    if reason == "specular-beam-too-weak-for-grazing":
        findings.append(
            "specular reflectance %.2f is below the grazing-route floor %.2f; "
            "the reading fell back to diffuse collection"
            % (surface["specular_reflectance"], MIN_SPECULAR_REFLECTANCE)
        )
    bounded = False
    if technique == INTERNAL_REFLECTION and thickness > ATR_SAMPLING_DEPTH_UM and abs(
        thickness - ATR_SAMPLING_DEPTH_UM
    ) > 1e-12:
        bounded = True
        findings.append(
            "film thickness %.3f um exceeds the %.3f um sampled by the "
            "evanescent field; report the areal mass as a lower bound"
            % (thickness, ATR_SAMPLING_DEPTH_UM)
        )
    if technique == DIFFUSE_REFLECTANCE:
        findings.append(
            "diffuse collection has no geometric path factor; the areal mass is "
            "a comparative figure against a like-for-like reference, not an "
            "absolute thickness"
        )
    return {
        "technique": technique,
        "technique_reason": reason,
        "incidence_angle_deg": angle,
        "path_enhancement": factor,
        "net_absorbance": net,
        "film_thickness_um": thickness,
        "areal_mass_ug_per_cm2": areal,
        "bounded_lower_limit": bounded,
        "findings": findings,
        "acceptable": not findings,
    }
