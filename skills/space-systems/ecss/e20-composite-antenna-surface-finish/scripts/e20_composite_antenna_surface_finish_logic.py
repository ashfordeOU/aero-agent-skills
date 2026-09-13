#!/usr/bin/env python3
"""Surface finish of composite antenna parts and its radiating consequence.

Anchor: ECSS-E-ST-20C clause 7.2.2.4.2 (paraphrased into an implementable
procedure; no verbatim standard text).

The module turns the clause into a checkable chain:

1. categorize the finish of the radiating face and decide whether it can
   reflect at all without a metallization layer;
2. convert the root-mean-square surface error into the Ruze
   aperture-efficiency loss at the operating wavelength;
3. derive the ohmic reflection loss from the sheet resistance of the
   conducting face and the loss from incomplete metallization coverage;
4. add the two-way absorption of any coating carried over the
   metallization;
5. sum the terms and check them against the allocation the
   antenna-gain-budget holds for surface finish.

Deterministic, offline, python3 standard library only.
"""

import math

SPEED_OF_LIGHT_M_PER_S = 299792458.0
FREE_SPACE_IMPEDANCE_OHM = 376.730313668

# Ruze closed form is a small-error result; beyond this ratio of
# root-mean-square error to wavelength the face is no longer described by it
# and the analysis has to move to a scattered-field computation.
SMALL_ERROR_RATIO_LIMIT = 0.0625

# Absorbs the representation error of a decibel value that is a sum of
# logarithmic terms. It never moves an engineering limit.
DECIBEL_TOLERANCE_DB = 1e-9

# Finish families of a composite radiating face.
SURFACE_FINISH_FAMILIES = {
    "bare-woven-carbon-face": {
        "rf_reflective": False,
        "carries_coating": False,
        "depolarising_weave": True,
    },
    "resin-rich-face": {
        "rf_reflective": False,
        "carries_coating": False,
        "depolarising_weave": False,
    },
    "metallized-face": {
        "rf_reflective": True,
        "carries_coating": False,
        "depolarising_weave": False,
    },
    "coated-metallized-face": {
        "rf_reflective": True,
        "carries_coating": True,
        "depolarising_weave": False,
    },
}


def _finite(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def _positive(value, label):
    out = _finite(value, label)
    if out <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (label, value))
    return out


def _non_negative(value, label):
    out = _finite(value, label)
    if out < 0.0:
        raise ValueError("%s cannot be negative, got %r" % (label, value))
    return out


def wavelength_m(frequency_hz):
    """Free-space wavelength of the operating frequency."""
    return SPEED_OF_LIGHT_M_PER_S / _positive(frequency_hz, "frequency_hz")


def categorize_surface_finish(finish_type):
    """Categorize the finish of a composite radiating face.

    Returns the family attributes plus whether a metallization layer is
    still owed before the face can act as a reflector.
    """
    if not isinstance(finish_type, str) or not finish_type.strip():
        raise ValueError("finish_type must be a non-empty string, got %r" % (finish_type,))
    key = finish_type.strip().lower()
    if key not in SURFACE_FINISH_FAMILIES:
        raise ValueError(
            "uncategorized surface finish %r; known families: %s"
            % (finish_type, ", ".join(sorted(SURFACE_FINISH_FAMILIES)))
        )
    attributes = dict(SURFACE_FINISH_FAMILIES[key])
    attributes["finish_type"] = key
    attributes["metallization_required"] = not attributes["rf_reflective"]
    return attributes


def ruze_gain_loss_db(rms_surface_error_m, wavelength_value_m):
    """Aperture-efficiency loss caused by the residual surface error.

    Closed-form small-error result: the loss grows with the square of the
    error-to-wavelength ratio, so halving the operating wavelength
    quadruples the penalty a given finish costs.
    """
    error = _non_negative(rms_surface_error_m, "rms_surface_error_m")
    lam = _positive(wavelength_value_m, "wavelength_value_m")
    if error > lam:
        raise ValueError(
            "rms_surface_error_m %r exceeds the wavelength %r; the face is not a "
            "finish deviation but a different geometry" % (rms_surface_error_m, lam)
        )
    ratio = error / lam
    return 10.0 * math.log10(math.e) * (4.0 * math.pi * ratio) ** 2


def surface_error_ratio(rms_surface_error_m, wavelength_value_m):
    """Ratio of root-mean-square surface error to wavelength."""
    error = _non_negative(rms_surface_error_m, "rms_surface_error_m")
    lam = _positive(wavelength_value_m, "wavelength_value_m")
    return error / lam


def ohmic_reflection_loss_db(sheet_resistance_ohm_per_square):
    """Reflection loss of a conducting face of finite sheet resistance.

    The face is treated as a surface impedance against free space; a
    perfectly conducting face returns everything and costs nothing, and the
    loss climbs as the sheet resistance approaches the free-space impedance.
    """
    sheet = _non_negative(
        sheet_resistance_ohm_per_square, "sheet_resistance_ohm_per_square"
    )
    if sheet >= FREE_SPACE_IMPEDANCE_OHM:
        raise ValueError(
            "sheet_resistance_ohm_per_square %r reaches the free-space impedance; "
            "the face no longer behaves as a reflector and needs a metallization "
            "layer, not a loss figure" % (sheet_resistance_ohm_per_square,)
        )
    reflection_magnitude = (FREE_SPACE_IMPEDANCE_OHM - sheet) / (
        FREE_SPACE_IMPEDANCE_OHM + sheet
    )
    return -20.0 * math.log10(reflection_magnitude)


def coverage_loss_db(metallization_coverage_fraction):
    """Loss from the part of the face the metallization does not cover."""
    coverage = _finite(
        metallization_coverage_fraction, "metallization_coverage_fraction"
    )
    if not 0.0 < coverage <= 1.0:
        raise ValueError(
            "metallization_coverage_fraction must sit in (0, 1], got %r"
            % (metallization_coverage_fraction,)
        )
    if coverage == 1.0:
        return 0.0
    return -10.0 * math.log10(coverage)


def coating_absorption_loss_db(
    thickness_m,
    relative_permittivity,
    loss_tangent,
    wavelength_value_m,
    incidence_angle_deg=0.0,
):
    """Two-way absorption of a coating carried over a reflecting face.

    The wave crosses the coating, reflects off the metallization and crosses
    it again, so the absorbed path is twice the refracted thickness.
    """
    thickness = _non_negative(thickness_m, "thickness_m")
    permittivity = _finite(relative_permittivity, "relative_permittivity")
    if permittivity < 1.0:
        raise ValueError(
            "relative_permittivity must be at least 1.0, got %r" % (relative_permittivity,)
        )
    tangent = _non_negative(loss_tangent, "loss_tangent")
    if tangent >= 1.0:
        raise ValueError(
            "loss_tangent %r is not a low-loss coating; the layer has to be "
            "treated as a lossy medium in its own right" % (loss_tangent,)
        )
    lam = _positive(wavelength_value_m, "wavelength_value_m")
    angle = _finite(incidence_angle_deg, "incidence_angle_deg")
    if not 0.0 <= angle < 90.0:
        raise ValueError(
            "incidence_angle_deg must sit in [0, 90), got %r" % (incidence_angle_deg,)
        )
    if thickness == 0.0:
        return 0.0
    sine_refracted = math.sin(math.radians(angle)) / math.sqrt(permittivity)
    cosine_refracted = math.sqrt(1.0 - sine_refracted * sine_refracted)
    attenuation_np_per_m = math.pi * math.sqrt(permittivity) * tangent / lam
    path_m = 2.0 * thickness / cosine_refracted
    return 20.0 * math.log10(math.e) * attenuation_np_per_m * path_m


def total_gain_degradation_db(components):
    """Sum the finish loss terms, rejecting a term that is not a loss."""
    if not isinstance(components, dict) or not components:
        raise ValueError("components must be a non-empty mapping of label to decibels")
    total = 0.0
    values = []
    for label in sorted(components):
        value = components[label]
        if value is None:
            continue
        loss = _finite(value, "loss term %s" % label)
        if loss < 0.0:
            raise ValueError(
                "loss term %s is negative (%r); a surface finish cannot add gain"
                % (label, value)
            )
        values.append(loss)
    if not values:
        raise ValueError("components carried no usable loss term")
    total = math.fsum(values)
    return total


def assess_composite_surface_finish(
    finish_type,
    frequency_hz,
    rms_surface_error_m,
    allocated_degradation_db,
    sheet_resistance_ohm_per_square=None,
    metallization_coverage_fraction=1.0,
    coating_thickness_m=0.0,
    coating_relative_permittivity=1.0,
    coating_loss_tangent=0.0,
    incidence_angle_deg=0.0,
):
    """Run the whole clause 7.2.2.4.2 assessment and return the findings."""
    allocation = _positive(allocated_degradation_db, "allocated_degradation_db")
    finish = categorize_surface_finish(finish_type)
    lam = wavelength_m(frequency_hz)
    findings = []

    ratio = surface_error_ratio(rms_surface_error_m, lam)
    ruze_db = ruze_gain_loss_db(rms_surface_error_m, lam)
    if ratio > SMALL_ERROR_RATIO_LIMIT:
        findings.append(
            "surface error is %.4f wavelengths, beyond the small-error validity "
            "limit of %.4f; the closed-form loss understates the face"
            % (ratio, SMALL_ERROR_RATIO_LIMIT)
        )

    components = {"ruze-surface-error": ruze_db}

    if finish["metallization_required"]:
        findings.append(
            "finish %s cannot reflect as delivered; a metallization layer is owed "
            "before the face radiates" % finish["finish_type"]
        )
        components["ohmic-reflection"] = None
        components["metallization-coverage"] = None
    else:
        if sheet_resistance_ohm_per_square is None:
            raise ValueError(
                "a reflecting finish needs sheet_resistance_ohm_per_square on record"
            )
        components["ohmic-reflection"] = ohmic_reflection_loss_db(
            sheet_resistance_ohm_per_square
        )
        coverage_db = coverage_loss_db(metallization_coverage_fraction)
        components["metallization-coverage"] = coverage_db
        if metallization_coverage_fraction < 1.0:
            findings.append(
                "metallization covers %.4f of the face, leaving an uncovered area "
                "that costs %.4f dB" % (metallization_coverage_fraction, coverage_db)
            )

    if finish["carries_coating"]:
        thickness = _non_negative(coating_thickness_m, "coating_thickness_m")
        if thickness == 0.0:
            raise ValueError(
                "finish %s carries a coating; coating_thickness_m must be positive"
                % finish["finish_type"]
            )
        components["coating-absorption"] = coating_absorption_loss_db(
            thickness,
            coating_relative_permittivity,
            coating_loss_tangent,
            lam,
            incidence_angle_deg,
        )
    else:
        components["coating-absorption"] = 0.0

    if finish["depolarising_weave"]:
        findings.append(
            "finish %s exposes the fibre weave; the cross-polarisation the weave "
            "introduces is not covered by the co-polar loss terms"
            % finish["finish_type"]
        )

    total_db = total_gain_degradation_db(components)
    within_allocation = total_db <= allocation or math.isclose(
        total_db, allocation, rel_tol=0.0, abs_tol=DECIBEL_TOLERANCE_DB
    )
    if not within_allocation:
        findings.append(
            "surface finish costs %.4f dB against an allocation of %.4f dB"
            % (total_db, allocation)
        )

    return {
        "finish": finish,
        "wavelength_m": lam,
        "surface_error_ratio": ratio,
        "components_db": components,
        "total_degradation_db": total_db,
        "allocated_degradation_db": allocation,
        "within_allocation": within_allocation,
        "findings": findings,
        "compliant": not findings,
    }
