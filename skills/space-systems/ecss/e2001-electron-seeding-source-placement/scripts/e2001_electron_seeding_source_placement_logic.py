#!/usr/bin/env python3
"""Placement and aiming of a multipactor electron seeding source.

Anchor: ECSS-E-ST-20-01C clause 6.5.5 -- directing the selected seeding
technique at the gap where a multipactor discharge is predicted to
start. Paraphrased into an implementable procedure; no standard text is
reproduced.

Offline, deterministic, stdlib only.
"""

import math

REL_TOL = 1e-12
ABS_TOL = 1e-15

# Photon energy constant: hc expressed in electronvolt-nanometre.
HC_EV_NM = 1239.841984

# Representative photoelectric work-function of gap surfaces (eV).
WORK_FUNCTION_EV = {
    "silver": 4.26,
    "silver-plated-aluminium": 4.26,
    "aluminium": 4.28,
    "alodine-coated-aluminium": 4.60,
    "copper": 4.65,
    "gold": 5.10,
    "titanium": 4.33,
    "stainless-steel": 4.40,
}

SEEDING_TECHNIQUES = (
    "radioactive-source",
    "ultraviolet-illumination",
    "electron-gun",
)

# Katz-Penfold beta range fit validity window (MeV).
BETA_ENERGY_MIN_MEV = 0.01
BETA_ENERGY_MAX_MEV = 3.0

# Default useful landing-energy window for a seeding electron-gun (eV).
DEFAULT_LANDING_WINDOW_EV = (50.0, 2000.0)


def _ge(value, limit):
    return value > limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _le(value, limit):
    return value < limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def _number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    value = float(value)
    if not math.isfinite(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return value


def _positive(value, label):
    value = _number(value, label)
    if value <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return value


def _non_negative(value, label):
    value = _number(value, label)
    if value < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return value


def _beta_energy(beta_energy_mev):
    energy = _number(beta_energy_mev, "beta_energy_mev")
    if not BETA_ENERGY_MIN_MEV <= energy <= BETA_ENERGY_MAX_MEV:
        raise ValueError(
            "beta_energy_mev must lie in [%s, %s] MeV, got %r"
            % (BETA_ENERGY_MIN_MEV, BETA_ENERGY_MAX_MEV, energy)
        )
    return energy


def beta_range_mg_cm2(beta_energy_mev):
    """Katz-Penfold practical range of a beta particle, in mg/cm2."""
    energy = _beta_energy(beta_energy_mev)
    exponent = 1.265 - 0.0954 * math.log(energy)
    return 412.0 * math.pow(energy, exponent)


def beta_absorption_coefficient_cm2_g(beta_energy_mev):
    """Empirical beta mass-absorption coefficient, in cm2/g."""
    energy = _beta_energy(beta_energy_mev)
    return 17.0 / math.pow(energy, 1.14)


def path_areal_density_mg_cm2(obstructions):
    """Accumulate thickness x density over every item in the sight-line."""
    if not isinstance(obstructions, (list, tuple)):
        raise ValueError("obstructions must be a list or tuple")
    total = 0.0
    for i, item in enumerate(obstructions):
        if not isinstance(item, dict):
            raise ValueError("obstructions[%d] must be a dict" % i)
        for key in ("thickness_cm", "density_g_cm3"):
            if key not in item:
                raise ValueError("obstructions[%d] missing %r" % (i, key))
        thickness = _positive(item["thickness_cm"], "obstructions[%d].thickness_cm" % i)
        density = _positive(item["density_g_cm3"], "obstructions[%d].density_g_cm3" % i)
        total += thickness * density * 1000.0
    return total


def sight_line_blocked(obstructions):
    """True when any item in the path is opaque to the seeding photons."""
    if not isinstance(obstructions, (list, tuple)):
        raise ValueError("obstructions must be a list or tuple")
    for i, item in enumerate(obstructions):
        if not isinstance(item, dict):
            raise ValueError("obstructions[%d] must be a dict" % i)
        if bool(item.get("opaque", False)):
            return True
    return False


def beta_reaches_gap(beta_energy_mev, areal_density_mg_cm2):
    """True when the particle range outruns the intervening areal density."""
    reach = beta_range_mg_cm2(beta_energy_mev)
    blocked_by = _non_negative(areal_density_mg_cm2, "areal_density_mg_cm2")
    return reach > blocked_by and not math.isclose(
        reach, blocked_by, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def beta_transmission(beta_energy_mev, areal_density_mg_cm2):
    """Surviving fraction of the beta flux after the intervening material."""
    if not beta_reaches_gap(beta_energy_mev, areal_density_mg_cm2):
        return 0.0
    mu = beta_absorption_coefficient_cm2_g(beta_energy_mev)
    grams_per_cm2 = _non_negative(areal_density_mg_cm2, "areal_density_mg_cm2") / 1000.0
    return math.exp(-mu * grams_per_cm2)


def photon_energy_ev(wavelength_nm):
    """Photon energy of the illumination, in electronvolt."""
    wavelength = _positive(wavelength_nm, "wavelength_nm")
    return HC_EV_NM / wavelength


def work_function_ev(surface_material):
    """Work-function of a named gap surface material."""
    if not isinstance(surface_material, str) or not surface_material.strip():
        raise ValueError("surface_material must be a non-empty string")
    key = surface_material.strip().lower()
    if key not in WORK_FUNCTION_EV:
        raise ValueError(
            "unknown surface_material %r; known: %s"
            % (surface_material, ", ".join(sorted(WORK_FUNCTION_EV)))
        )
    return WORK_FUNCTION_EV[key]


def photoemission_margin_ev(wavelength_nm, surface_material):
    """Photon energy minus the surface work-function."""
    return photon_energy_ev(wavelength_nm) - work_function_ev(surface_material)


def photoemission_possible(wavelength_nm, surface_material):
    """True only when the photon clears the work-function with margin."""
    margin = photoemission_margin_ev(wavelength_nm, surface_material)
    return margin > 0.0 and not math.isclose(
        margin, 0.0, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def solid_angle_capture_fraction(gap_aperture_area_cm2, source_to_gap_distance_cm):
    """Fraction of an isotropic emission that enters the gap aperture."""
    area = _positive(gap_aperture_area_cm2, "gap_aperture_area_cm2")
    distance = _positive(source_to_gap_distance_cm, "source_to_gap_distance_cm")
    fraction = area / (4.0 * math.pi * distance * distance)
    return min(fraction, 1.0)


def delivered_rate_per_s(emission_rate_per_s, transmission, capture_fraction):
    """Seed electrons per second actually arriving inside the gap."""
    emission = _positive(emission_rate_per_s, "emission_rate_per_s")
    transmitted = _non_negative(transmission, "transmission")
    captured = _non_negative(capture_fraction, "capture_fraction")
    if not _le(transmitted, 1.0):
        raise ValueError("transmission must be <= 1, got %r" % transmitted)
    if not _le(captured, 1.0):
        raise ValueError("capture_fraction must be <= 1, got %r" % captured)
    return emission * transmitted * captured


def aim_point_matches_initiation_site(aim_point, initiation_site):
    """True when the source is directed at the predicted initiation gap."""
    for label, value in (("aim_point", aim_point), ("initiation_site", initiation_site)):
        if not isinstance(value, str) or not value.strip():
            raise ValueError("%s must be a non-empty string" % label)
    return aim_point.strip().lower() == initiation_site.strip().lower()


def gun_aim_check(aim_offset_mm, gap_height_mm, landing_energy_ev, window_ev=None):
    """Grade an electron-gun beam against the gap and its yield window."""
    offset = abs(_number(aim_offset_mm, "aim_offset_mm"))
    gap = _positive(gap_height_mm, "gap_height_mm")
    energy = _positive(landing_energy_ev, "landing_energy_ev")
    if window_ev is None:
        window_ev = DEFAULT_LANDING_WINDOW_EV
    if not isinstance(window_ev, (list, tuple)) or len(window_ev) != 2:
        raise ValueError("window_ev must be a (low, high) pair")
    low = _positive(window_ev[0], "window_ev[0]")
    high = _positive(window_ev[1], "window_ev[1]")
    if not low < high:
        raise ValueError("window_ev must satisfy low < high, got %r" % (window_ev,))
    findings = []
    if not _le(offset, gap / 2.0):
        findings.append("beam-misses-critical-gap")
    if not (_ge(energy, low) and _le(energy, high)):
        findings.append("landing-energy-outside-yield-window")
    return {
        "aim_offset_mm": offset,
        "half_gap_mm": gap / 2.0,
        "landing_energy_ev": energy,
        "window_ev": (low, high),
        "findings": findings,
        "inside_gap": "beam-misses-critical-gap" not in findings,
    }


def assess_source_placement(spec):
    """Full clause 6.5.5 placement assessment for one seeding source."""
    if not isinstance(spec, dict):
        raise ValueError("spec must be a dict")
    required = (
        "technique",
        "aim_point",
        "initiation_site",
        "source_to_gap_distance_cm",
        "gap_aperture_area_cm2",
        "emission_rate_per_s",
        "required_rate_per_s",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key %r" % key)
    technique = spec["technique"]
    if technique not in SEEDING_TECHNIQUES:
        raise ValueError(
            "unknown technique %r; known: %s"
            % (technique, ", ".join(SEEDING_TECHNIQUES))
        )
    obstructions = spec.get("obstructions", [])
    areal = path_areal_density_mg_cm2(obstructions)
    capture = solid_angle_capture_fraction(
        spec["gap_aperture_area_cm2"], spec["source_to_gap_distance_cm"]
    )
    findings = []
    if not aim_point_matches_initiation_site(spec["aim_point"], spec["initiation_site"]):
        findings.append("aim-point-not-the-predicted-initiation-gap")
    transmission = 1.0
    detail = {}
    if technique == "radioactive-source":
        if "beta_energy_mev" not in spec:
            raise ValueError("radioactive-source spec missing 'beta_energy_mev'")
        reach = beta_range_mg_cm2(spec["beta_energy_mev"])
        transmission = beta_transmission(spec["beta_energy_mev"], areal)
        if not beta_reaches_gap(spec["beta_energy_mev"], areal):
            findings.append("beta-range-shorter-than-intervening-areal-density")
        detail = {"beta_range_mg_cm2": reach, "path_areal_density_mg_cm2": areal}
    elif technique == "ultraviolet-illumination":
        for key in ("wavelength_nm", "target_surface_material"):
            if key not in spec:
                raise ValueError("ultraviolet-illumination spec missing %r" % key)
        margin = photoemission_margin_ev(
            spec["wavelength_nm"], spec["target_surface_material"]
        )
        if not photoemission_possible(
            spec["wavelength_nm"], spec["target_surface_material"]
        ):
            findings.append("photon-energy-below-surface-work-function")
            transmission = 0.0
        if sight_line_blocked(obstructions):
            findings.append("sight-line-obstructed-by-opaque-barrier")
            transmission = 0.0
        detail = {
            "photon_energy_ev": photon_energy_ev(spec["wavelength_nm"]),
            "photoemission_margin_ev": margin,
        }
    else:
        for key in ("aim_offset_mm", "gap_height_mm", "landing_energy_ev"):
            if key not in spec:
                raise ValueError("electron-gun spec missing %r" % key)
        gun = gun_aim_check(
            spec["aim_offset_mm"],
            spec["gap_height_mm"],
            spec["landing_energy_ev"],
            spec.get("landing_window_ev"),
        )
        findings.extend(gun["findings"])
        if not gun["inside_gap"]:
            transmission = 0.0
        detail = gun
    delivered = delivered_rate_per_s(spec["emission_rate_per_s"], transmission, capture)
    needed = _positive(spec["required_rate_per_s"], "required_rate_per_s")
    if not _ge(delivered, needed):
        findings.append("delivered-rate-below-required-rate")
    return {
        "technique": technique,
        "capture_fraction": capture,
        "transmission": transmission,
        "path_areal_density_mg_cm2": areal,
        "delivered_rate_per_s": delivered,
        "required_rate_per_s": needed,
        "detail": detail,
        "findings": findings,
        "acceptable": not findings,
    }
