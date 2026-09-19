"""Cleanliness verification by visual and black-light inspection.

Anchor: ECSS-Q-ST-70-01C, verification clause -- establishing what a visual or
ultraviolet inspection can substantiate, checking the conditions it is
performed under, and deciding when an instrumented measurement has to take
over. Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Compute the smallest particle an observer can resolve from the viewing
   distance and the angular acuity assumed for the inspection.
2. Degrade that limit for illuminance below the reference level and for a
   viewing angle away from normal, giving the detectable size actually
   achieved by the conditions on the day.
3. Check the ultraviolet conditions separately: the lamp has to sit inside
   the long-wave band, deliver enough irradiance at the surface, and the
   observer has to have dark adapted before the inspection starts.
4. Compare the achieved detectable size with the size the requirement needs
   observed, and state plainly when inspection cannot substantiate it.
5. Reduce the inspected fraction of the surface and grade the observation
   into an accept, a re-clean or an escalation to an instrumented method.
"""

import math

__all__ = [
    "REFERENCE_ILLUMINANCE_LUX",
    "MIN_UV_IRRADIANCE_W_PER_M2",
    "UV_A_BAND_NM",
    "MIN_DARK_ADAPTATION_MIN",
    "SIZE_TOLERANCE",
    "resolvable_particle_um",
    "illuminance_derating",
    "angle_derating",
    "detectable_size_um",
    "uv_band_ok",
    "uv_irradiance_ok",
    "dark_adaptation_ok",
    "inspected_fraction",
    "inspection_duration_min",
    "can_substantiate",
    "grade_inspection",
    "assess_inspection",
]

# Illuminance the acuity assumption is stated at; below it the eye resolves
# less, above it the gain flattens out and is not credited.
REFERENCE_ILLUMINANCE_LUX = 1000.0

# Long-wave ultraviolet irradiance needed at the surface for a fluorescence
# observation to mean anything.
MIN_UV_IRRADIANCE_W_PER_M2 = 10.0

# Long-wave ultraviolet band, in nanometres.
UV_A_BAND_NM = (315.0, 400.0)

# Time in the dark before the observer's response is stable.
MIN_DARK_ADAPTATION_MIN = 5.0

# Detectable-size comparisons involve a tangent and a square root; absorb
# representation error at the boundary instead of relaxing the requirement.
SIZE_TOLERANCE = 1e-9


def _finite(label, value):
    """Return value as a finite float or raise."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number" % label)
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite" % label)
    return number


def _positive(label, value):
    """Return value as a strictly positive finite float or raise."""
    number = _finite(label, value)
    if number <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return number


def resolvable_particle_um(distance_mm, acuity_arcmin):
    """Return the smallest resolvable particle diameter in micrometres."""
    distance = _positive("distance_mm", distance_mm)
    acuity = _positive("acuity_arcmin", acuity_arcmin)
    if acuity > 60.0:
        raise ValueError(
            "acuity_arcmin above one degree is not an inspection assumption, "
            "got %r" % (acuity_arcmin,)
        )
    half_angle_rad = math.radians(acuity / 60.0) / 2.0
    # Chord subtended at the viewing distance, millimetres to micrometres.
    return 2.0 * distance * math.tan(half_angle_rad) * 1000.0


def illuminance_derating(illuminance_lux):
    """Return the factor the detectable size grows by at this illuminance."""
    lux = _positive("illuminance_lux", illuminance_lux)
    if lux >= REFERENCE_ILLUMINANCE_LUX:
        return 1.0
    # Acuity falls off gradually as light is removed; the square root of the
    # illuminance shortfall is the derating credited here.
    return math.sqrt(REFERENCE_ILLUMINANCE_LUX / lux)


def angle_derating(viewing_angle_deg):
    """Return the factor the detectable size grows by away from normal viewing."""
    angle = _finite("viewing_angle_deg", viewing_angle_deg)
    if angle < 0.0 or angle >= 90.0:
        raise ValueError(
            "viewing_angle_deg must lie in [0, 90), got %r" % (viewing_angle_deg,)
        )
    # The surface foreshortens as the cosine of the angle from normal.
    return 1.0 / math.cos(math.radians(angle))


def detectable_size_um(distance_mm, acuity_arcmin, illuminance_lux,
                       viewing_angle_deg=0.0):
    """Return the detectable particle size achieved by the inspection conditions."""
    base = resolvable_particle_um(distance_mm, acuity_arcmin)
    return base * illuminance_derating(illuminance_lux) * angle_derating(
        viewing_angle_deg
    )


def uv_band_ok(wavelength_nm):
    """Return True when the lamp sits inside the long-wave ultraviolet band."""
    value = _positive("wavelength_nm", wavelength_nm)
    low, high = UV_A_BAND_NM
    return low <= value <= high


def uv_irradiance_ok(irradiance_w_per_m2):
    """Return True when the surface irradiance supports a fluorescence observation."""
    value = _finite("irradiance_w_per_m2", irradiance_w_per_m2)
    if value < 0.0:
        raise ValueError("irradiance_w_per_m2 must not be negative")
    return value > MIN_UV_IRRADIANCE_W_PER_M2 or math.isclose(
        value, MIN_UV_IRRADIANCE_W_PER_M2, rel_tol=SIZE_TOLERANCE, abs_tol=0.0
    )


def dark_adaptation_ok(minutes):
    """Return True when the observer has been in the dark long enough."""
    value = _finite("minutes", minutes)
    if value < 0.0:
        raise ValueError("minutes must not be negative")
    return value > MIN_DARK_ADAPTATION_MIN or math.isclose(
        value, MIN_DARK_ADAPTATION_MIN, rel_tol=SIZE_TOLERANCE, abs_tol=0.0
    )


def inspected_fraction(inspected_area_m2, total_area_m2):
    """Return the fraction of the surface actually looked at."""
    inspected = _finite("inspected_area_m2", inspected_area_m2)
    if inspected < 0.0:
        raise ValueError("inspected_area_m2 must not be negative")
    total = _positive("total_area_m2", total_area_m2)
    if inspected > total * (1.0 + SIZE_TOLERANCE):
        raise ValueError(
            "inspected area %g m2 exceeds the total area %g m2" % (inspected, total)
        )
    return min(inspected / total, 1.0)


def inspection_duration_min(area_m2, rate_m2_per_min):
    """Return the time the inspection takes at the declared coverage rate."""
    area = _positive("area_m2", area_m2)
    rate = _positive("rate_m2_per_min", rate_m2_per_min)
    return area / rate


def can_substantiate(detectable_um, required_um):
    """Return True when the conditions resolve the size the requirement needs."""
    achieved = _positive("detectable_um", detectable_um)
    required = _positive("required_um", required_um)
    return achieved < required or math.isclose(
        achieved, required, rel_tol=SIZE_TOLERANCE, abs_tol=0.0
    )


def grade_inspection(substantiated, contamination_seen, recleanable=True):
    """Return the disposition an inspection observation earns."""
    if not isinstance(substantiated, bool):
        raise ValueError("substantiated must be a boolean")
    if not isinstance(contamination_seen, bool):
        raise ValueError("contamination_seen must be a boolean")
    if not isinstance(recleanable, bool):
        raise ValueError("recleanable must be a boolean")
    if not substantiated:
        return "escalate-to-instrumented-method"
    if not contamination_seen:
        return "accept"
    if recleanable:
        return "reclean-and-reinspect"
    return "escalate-to-instrumented-method"


def assess_inspection(spec):
    """Grade one cleanliness inspection against the size it has to substantiate.

    spec keys: distance_mm, acuity_arcmin, illuminance_lux, required_um,
    inspected_area_m2, total_area_m2, contamination_seen; optional
    viewing_angle_deg, black_light (mapping with wavelength_nm,
    irradiance_w_per_m2, dark_adaptation_min), coverage_required,
    recleanable, rate_m2_per_min.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("distance_mm", "acuity_arcmin", "illuminance_lux", "required_um",
                "inspected_area_m2", "total_area_m2", "contamination_seen"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    if not isinstance(spec["contamination_seen"], bool):
        raise ValueError("contamination_seen must be a boolean")
    detectable = detectable_size_um(
        spec["distance_mm"],
        spec["acuity_arcmin"],
        spec["illuminance_lux"],
        spec.get("viewing_angle_deg", 0.0),
    )
    required = _positive("required_um", spec["required_um"])
    findings = []
    substantiated = can_substantiate(detectable, required)
    if not substantiated:
        findings.append(
            "conditions resolve %.4g um but the requirement needs %.4g um "
            "observed; inspection cannot substantiate it" % (detectable, required)
        )
    black_light = spec.get("black_light")
    if black_light is not None:
        if not isinstance(black_light, dict):
            raise ValueError("black_light must be a mapping")
        for key in ("wavelength_nm", "irradiance_w_per_m2", "dark_adaptation_min"):
            if key not in black_light:
                raise ValueError("black_light missing required key '%s'" % key)
        if not uv_band_ok(black_light["wavelength_nm"]):
            findings.append(
                "lamp at %.4g nm is outside the long-wave ultraviolet band"
                % float(black_light["wavelength_nm"])
            )
        if not uv_irradiance_ok(black_light["irradiance_w_per_m2"]):
            findings.append(
                "surface irradiance %.4g W/m2 is below the %.4g W/m2 needed for a "
                "fluorescence observation"
                % (float(black_light["irradiance_w_per_m2"]),
                   MIN_UV_IRRADIANCE_W_PER_M2)
            )
        if not dark_adaptation_ok(black_light["dark_adaptation_min"]):
            findings.append(
                "observer dark adapted for %.4g min, below the %.4g min the "
                "observation assumes"
                % (float(black_light["dark_adaptation_min"]),
                   MIN_DARK_ADAPTATION_MIN)
            )
    coverage = inspected_fraction(spec["inspected_area_m2"], spec["total_area_m2"])
    required_coverage = _finite(
        "coverage_required", spec.get("coverage_required", 1.0)
    )
    if required_coverage <= 0.0 or required_coverage > 1.0:
        raise ValueError("coverage_required must lie in (0, 1]")
    coverage_ok = coverage > required_coverage or math.isclose(
        coverage, required_coverage, rel_tol=SIZE_TOLERANCE, abs_tol=0.0
    )
    if not coverage_ok:
        findings.append(
            "only %.4g of the surface was inspected against a required %.4g"
            % (coverage, required_coverage)
        )
    result = {
        "detectable_size_um": detectable,
        "required_um": required,
        "substantiated": substantiated and not findings,
        "inspected_fraction": coverage,
        "disposition": grade_inspection(
            substantiated and not findings,
            spec["contamination_seen"],
            bool(spec.get("recleanable", True)),
        ),
        "findings": findings,
    }
    if spec.get("rate_m2_per_min") is not None:
        result["duration_min"] = inspection_duration_min(
            spec["total_area_m2"], spec["rate_m2_per_min"]
        )
    return result
