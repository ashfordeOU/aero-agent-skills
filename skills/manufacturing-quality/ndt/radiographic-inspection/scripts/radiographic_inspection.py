"""Radiographic inspection (RT) math for aerospace NDT.

Deterministic, offline, stdlib-only helpers for industrial radiography:
geometric unsharpness from the focal spot and the source-object-detector
geometry, exposure-time scaling by the inverse-square law, image quality
indicator (IQI) percent sensitivity, film density verdict against the
2.0 to 4.0 optical density band, discontinuity classification from the
radiographic image geometry, and the combined technique verdict that
gates acceptance.

Units: focal spot, distances, and thicknesses in millimeters; exposure
time in minutes (the inverse-square law is a ratio, so any consistent
time unit works); film density in optical density (unitless).

Contract exercised by scripts/test_radiographic_inspection.py.
"""

import math

DENSITY_BAND_MIN = 2.0  # typical acceptable film density, lower edge
DENSITY_BAND_MAX = 4.0  # typical acceptable film density, upper edge
DEFAULT_UNSHARPNESS_LIMIT_MM = 0.25  # fine-detail geometric unsharpness limit
DEFAULT_SENSITIVITY_LIMIT_PERCENT = 2.0  # typical IQI sensitivity requirement


def geometric_unsharpness(focal_spot_mm, sod_mm, odd_mm):
    """Return the geometric unsharpness Ug in millimeters: Ug = F * ODD / SOD.

    F is the effective focal spot size, SOD the source-to-object distance,
    and ODD the object-to-detector distance. A larger focal spot and a
    larger object-to-detector distance increase unsharpness; a longer
    source-to-object distance reduces it.

    Raises ValueError for a non-finite or non-positive focal spot or SOD,
    or a negative ODD. A zero ODD (detector against the object surface)
    gives zero unsharpness.
    """
    if not math.isfinite(focal_spot_mm) or focal_spot_mm <= 0:
        raise ValueError(
            "focal spot size must be a finite value > 0, got %r" % (focal_spot_mm,)
        )
    if not math.isfinite(sod_mm) or sod_mm <= 0:
        raise ValueError(
            "source-to-object distance must be a finite value > 0, got %r"
            % (sod_mm,)
        )
    if not math.isfinite(odd_mm) or odd_mm < 0:
        raise ValueError(
            "object-to-detector distance must be a finite value >= 0, got %r"
            % (odd_mm,)
        )
    return focal_spot_mm * odd_mm / sod_mm


def exposure_time(base_time, distance, reference_distance):
    """Return the new exposure time by the inverse-square law.

    t_new = base_time * (distance / reference_distance) ** 2. Doubling the
    source-to-detector distance quadruples the required exposure time;
    halving it quarters the time.

    Raises ValueError for a non-finite or non-positive base time, distance,
    or reference distance.
    """
    if not math.isfinite(base_time) or base_time <= 0:
        raise ValueError(
            "base exposure time must be a finite value > 0, got %r" % (base_time,)
        )
    if not math.isfinite(distance) or distance <= 0:
        raise ValueError("distance must be a finite value > 0, got %r" % (distance,))
    if not math.isfinite(reference_distance) or reference_distance <= 0:
        raise ValueError(
            "reference distance must be a finite value > 0, got %r"
            % (reference_distance,)
        )
    return base_time * (distance / reference_distance) ** 2


def iqi_sensitivity_percent(visible_thickness_mm, part_thickness_mm):
    """Return the IQI (penetrameter) sensitivity in percent.

    sensitivity = visible_thickness / part_thickness * 100, where
    visible_thickness is the thinnest IQI feature (hole or step) seen on
    the radiograph and part_thickness is the section thickness being
    examined. A typical aerospace requirement is 2 percent or better.

    Raises ValueError for non-positive thicknesses or a visible thickness
    larger than the part thickness.
    """
    if not math.isfinite(visible_thickness_mm) or visible_thickness_mm <= 0:
        raise ValueError(
            "visible thickness must be a finite value > 0, got %r"
            % (visible_thickness_mm,)
        )
    if not math.isfinite(part_thickness_mm) or part_thickness_mm <= 0:
        raise ValueError(
            "part thickness must be a finite value > 0, got %r" % (part_thickness_mm,)
        )
    if visible_thickness_mm > part_thickness_mm:
        raise ValueError(
            "visible thickness %r exceeds part thickness %r"
            % (visible_thickness_mm, part_thickness_mm)
        )
    return visible_thickness_mm / part_thickness_mm * 100.0


def density_verdict(film_density):
    """Return the film density verdict dict for the 2.0 to 4.0 band.

    The verdict is 'acceptable' inside the band (edges inclusive),
    'too-low' below it (underexposure), and 'too-high' above it
    (overexposure). Returns a dict with keys density, acceptable, verdict,
    and band. The band is typical practice; the governing specification
    may set a different range.

    Raises ValueError for a non-finite or negative density.
    """
    if not math.isfinite(film_density) or film_density < 0:
        raise ValueError(
            "film density must be a finite value >= 0, got %r" % (film_density,)
        )
    band = (DENSITY_BAND_MIN, DENSITY_BAND_MAX)
    if DENSITY_BAND_MIN <= film_density <= DENSITY_BAND_MAX:
        return {
            "density": film_density,
            "acceptable": True,
            "verdict": "acceptable",
            "band": band,
        }
    if film_density < DENSITY_BAND_MIN:
        return {
            "density": film_density,
            "acceptable": False,
            "verdict": "too-low",
            "band": band,
        }
    return {
        "density": film_density,
        "acceptable": False,
        "verdict": "too-high",
        "band": band,
    }


def discontinuity_class(geometry_descriptor):
    """Classify a discontinuity from its radiographic image geometry.

    Keyword-driven mapping, first match wins:
    - porosity: round, globular, spherical, gas (isolated or clustered
      round voids, typically from solidification)
    - crack: elongated, linear, sharp, hairline, tight (narrow and sharp
      image, follows grain or residual-stress paths)
    - inclusion: compact, dense, metallic, high-density (foreign material,
      metallic inclusions appear brighter on the film)
    - slag: flat, planar, layered, angular, slag (weld context, nonmetallic
      residue with angular or planar outline)

    Raises ValueError for an empty or unrecognized descriptor.
    """
    desc = (geometry_descriptor or "").strip().lower()
    if not desc:
        raise ValueError("geometry descriptor must be non-empty")
    if any(k in desc for k in ("round", "globular", "spherical", "gas")):
        return "porosity"
    if any(k in desc for k in ("elongated", "linear", "sharp", "hairline", "tight")):
        return "crack"
    if any(k in desc for k in ("compact", "dense", "metallic", "high-density")):
        return "inclusion"
    if any(k in desc for k in ("flat", "planar", "layered", "angular", "slag")):
        return "slag"
    raise ValueError(
        "unknown geometry descriptor %r (expect porosity, crack, inclusion, "
        "or slag keywords)" % (geometry_descriptor,)
    )


def rt_setup_verdict(
    unsharpness_mm,
    sensitivity_percent,
    film_density,
    unsharpness_limit_mm=DEFAULT_UNSHARPNESS_LIMIT_MM,
    sensitivity_limit_percent=DEFAULT_SENSITIVITY_LIMIT_PERCENT,
):
    """Return the combined radiographic technique verdict dict.

    The technique is acceptable only when all three checks pass: geometric
    unsharpness at or below the limit (default 0.25 mm for fine detail),
    IQI sensitivity at or below the limit (default 2.0 percent), and film
    density inside the 2.0 to 4.0 band. Returns a dict with keys
    acceptable, checks, and reasons (one string per failed check).

    Raises ValueError for a negative unsharpness, a non-positive
    sensitivity or limit, or an invalid film density.
    """
    if not math.isfinite(unsharpness_mm) or unsharpness_mm < 0:
        raise ValueError(
            "unsharpness must be a finite value >= 0, got %r" % (unsharpness_mm,)
        )
    if not math.isfinite(sensitivity_percent) or sensitivity_percent <= 0:
        raise ValueError(
            "sensitivity must be a finite value > 0, got %r" % (sensitivity_percent,)
        )
    if not math.isfinite(unsharpness_limit_mm) or unsharpness_limit_mm <= 0:
        raise ValueError(
            "unsharpness limit must be a finite value > 0, got %r"
            % (unsharpness_limit_mm,)
        )
    if not math.isfinite(sensitivity_limit_percent) or sensitivity_limit_percent <= 0:
        raise ValueError(
            "sensitivity limit must be a finite value > 0, got %r"
            % (sensitivity_limit_percent,)
        )
    dv = density_verdict(film_density)
    checks = {
        "unsharpness": {
            "value": unsharpness_mm,
            "limit": unsharpness_limit_mm,
            "acceptable": unsharpness_mm <= unsharpness_limit_mm,
        },
        "sensitivity": {
            "value": sensitivity_percent,
            "limit": sensitivity_limit_percent,
            "acceptable": sensitivity_percent <= sensitivity_limit_percent,
        },
        "density": {
            "value": film_density,
            "band": dv["band"],
            "acceptable": dv["acceptable"],
        },
    }
    reasons = []
    if not checks["unsharpness"]["acceptable"]:
        reasons.append(
            "geometric unsharpness %.3f mm exceeds the %.3f mm limit"
            % (unsharpness_mm, unsharpness_limit_mm)
        )
    if not checks["sensitivity"]["acceptable"]:
        reasons.append(
            "IQI sensitivity %.2f percent exceeds the %.2f percent limit"
            % (sensitivity_percent, sensitivity_limit_percent)
        )
    if not checks["density"]["acceptable"]:
        reasons.append(
            "film density %.2f is %s (band %.1f to %.1f)"
            % (film_density, dv["verdict"], DENSITY_BAND_MIN, DENSITY_BAND_MAX)
        )
    return {"acceptable": not reasons, "checks": checks, "reasons": reasons}
