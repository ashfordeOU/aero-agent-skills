"""Support-structure scattering for a spacecraft antenna.

Anchor: ECSS-E-ST-20C clause 7.2.2.3.6 (scattering caused by support
structures and its influence on antenna performance). Paraphrased into an
implementable procedure; no standard text is reproduced.

The module is offline, deterministic and stdlib-only. It converts a declared
set of feed supports, subreflector legs and rim fittings into:

  * a scattering mechanism per support (which field the support intercepts),
  * an equivalent projected aperture-blockage area,
  * the blockage-efficiency antenna-gain loss,
  * the peak scattered side-lobe level and its co-polar/cross-polar split,
  * a finding list judged against the declared allowables.
"""

import math

#: Absolute tolerance used when a computed decibel figure is compared with a
#: declared allowable. A value that lands a few ULPs above the allowable
#: because it is a sum or a difference of logarithms is still compliant; the
#: engineering limit itself is never widened.
LIMIT_TOLERANCE_DB = 1e-9

#: Level reported for a scattered component whose amplitude is exactly zero
#: (a strut aligned with the incident electric field produces no cross-polar
#: term). Decibels have no representation for zero, so a floor is reported.
FLOOR_LEVEL_DBC = -300.0

#: A polarisation share at or below this value is exactly zero in intent and
#: only non-zero because cos(90 deg) and sin(0 deg) are not exactly zero in
#: binary floating point. Shares at or below it report the decibel floor.
NEGLIGIBLE_POWER_SHARE = 1e-15

#: Field a support intercepts -> the scattering mechanism it drives.
MECHANISM_BY_FIELD_REGION = {
    "collimated-aperture-field": "plane-wave-scattering",
    "feed-spherical-wave": "spherical-wave-scattering",
    "reflector-rim": "edge-diffraction",
    "outside-illuminated-volume": "no-scattering-path",
}

BLOCKING_MECHANISMS = ("plane-wave-scattering", "spherical-wave-scattering")


def _positive(value, label):
    """Return value as a float, rejecting non-numeric and non-positive input."""
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _within_limit_db(value_db, limit_db):
    """True when value_db does not exceed limit_db, absorbing float error."""
    return value_db <= limit_db or math.isclose(
        value_db, limit_db, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE_DB
    )


def categorize_scattering_mechanism(field_region):
    """Map the field a support sits in onto its scattering mechanism."""
    if not isinstance(field_region, str):
        raise ValueError("field_region must be a string, got %r" % (field_region,))
    key = field_region.strip().lower()
    if key not in MECHANISM_BY_FIELD_REGION:
        raise ValueError(
            "uncategorized field_region %r; expected one of %s"
            % (field_region, ", ".join(sorted(MECHANISM_BY_FIELD_REGION)))
        )
    return MECHANISM_BY_FIELD_REGION[key]


def aperture_area_m2(diameter_m):
    """Physical area of a circular aperture of the given diameter."""
    d = _positive(diameter_m, "diameter_m")
    return math.pi * d * d / 4.0


def strut_projected_area_m2(width_m, length_m, count=1, tilt_deg=0.0):
    """Shadow a straight strut casts on the aperture plane.

    tilt_deg is the angle between the strut axis and the aperture plane; a
    strut normal to the aperture (90 deg) casts no elongated shadow.
    """
    w = _positive(width_m, "width_m")
    ln = _positive(length_m, "length_m")
    if not isinstance(count, int) or isinstance(count, bool) or count < 1:
        raise ValueError("count must be an integer >= 1, got %r" % (count,))
    tilt = float(tilt_deg)
    if not 0.0 <= tilt <= 90.0:
        raise ValueError("tilt_deg must lie in [0, 90], got %r" % (tilt_deg,))
    projection = 0.0 if math.isclose(tilt, 90.0) else math.cos(math.radians(tilt))
    return count * w * ln * projection


def spherical_wave_magnification(strut_distance_m, reflector_distance_m):
    """Shadow magnification for a support lit by the diverging feed wave."""
    ds = _positive(strut_distance_m, "strut_distance_m")
    dr = _positive(reflector_distance_m, "reflector_distance_m")
    if dr < ds:
        raise ValueError(
            "reflector_distance_m (%r) must be >= strut_distance_m (%r)"
            % (reflector_distance_m, strut_distance_m)
        )
    return dr / ds


def blockage_fraction(blocked_area_m2, total_aperture_area_m2):
    """Fraction of the aperture area removed by the supports."""
    total = _positive(total_aperture_area_m2, "total_aperture_area_m2")
    blocked = float(blocked_area_m2)
    if blocked < 0.0:
        raise ValueError("blocked_area_m2 must be >= 0, got %r" % (blocked_area_m2,))
    if blocked >= total:
        raise ValueError(
            "blocked_area_m2 (%r) reaches or exceeds the aperture area (%r); "
            "the geometry is not a blockage case" % (blocked_area_m2, total)
        )
    return blocked / total


def blockage_gain_loss_db(fraction):
    """Antenna-gain loss from coherent removal of the blocked aperture field."""
    f = float(fraction)
    if not 0.0 <= f < 1.0:
        raise ValueError("fraction must lie in [0, 1), got %r" % (fraction,))
    return -20.0 * math.log10(1.0 - f)


def scattered_side_lobe_level_dbc(fraction, angular_spread_factor):
    """Peak of the scattered lobe relative to the unblocked main-beam peak.

    The intercepted power reappears spread over a solid angle
    angular_spread_factor times wider than the main beam, so the peak
    intensity ratio is fraction / ((1 - fraction) * spread).
    """
    f = float(fraction)
    if not 0.0 < f < 1.0:
        raise ValueError("fraction must lie in (0, 1), got %r" % (fraction,))
    spread = float(angular_spread_factor)
    if spread < 1.0:
        raise ValueError(
            "angular_spread_factor must be >= 1 (a scattered lobe cannot be "
            "narrower than the main beam), got %r" % (angular_spread_factor,)
        )
    return 10.0 * math.log10(f / ((1.0 - f) * spread))


def depolarised_split_dbc(total_level_dbc, tilt_to_e_field_deg):
    """Split a scattered lobe into its co-polar and cross-polar parts.

    A thin strut at angle t to the incident electric field radiates cos^2(t)
    of the scattered power co-polar and sin^2(t) cross-polar.
    """
    level = float(total_level_dbc)
    if not math.isfinite(level):
        raise ValueError("total_level_dbc must be finite, got %r" % (total_level_dbc,))
    tilt = float(tilt_to_e_field_deg)
    if not 0.0 <= tilt <= 90.0:
        raise ValueError(
            "tilt_to_e_field_deg must lie in [0, 90], got %r" % (tilt_to_e_field_deg,)
        )
    rad = math.radians(tilt)
    co = math.cos(rad) ** 2
    cross = math.sin(rad) ** 2
    co_db = (
        level + 10.0 * math.log10(co)
        if co > NEGLIGIBLE_POWER_SHARE
        else FLOOR_LEVEL_DBC
    )
    cross_db = (
        level + 10.0 * math.log10(cross)
        if cross > NEGLIGIBLE_POWER_SHARE
        else FLOOR_LEVEL_DBC
    )
    return {"co_polar_dbc": co_db, "cross_polar_dbc": cross_db}


def _support_blocked_area_m2(support):
    """Equivalent aperture-blockage area contributed by one support entry."""
    mechanism = categorize_scattering_mechanism(support.get("field_region"))
    if mechanism not in BLOCKING_MECHANISMS:
        return mechanism, 0.0
    geometric = strut_projected_area_m2(
        support.get("width_m"),
        support.get("length_m"),
        support.get("count", 1),
        support.get("tilt_deg", 0.0),
    )
    if mechanism == "plane-wave-scattering":
        return mechanism, geometric
    if "strut_distance_m" not in support or "reflector_distance_m" not in support:
        raise ValueError(
            "support %r sits in the feed spherical wave and needs both "
            "strut_distance_m and reflector_distance_m"
            % (support.get("id", "<unnamed>"),)
        )
    mag = spherical_wave_magnification(
        support["strut_distance_m"], support["reflector_distance_m"]
    )
    return mechanism, geometric * mag * mag


def assess_support_structure_scattering(config):
    """Full clause 7.2.2.3.6 assessment for one reflector antenna."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping, got %r" % (type(config).__name__,))
    supports = config.get("supports")
    if not isinstance(supports, list) or not supports:
        raise ValueError("config['supports'] must be a non-empty list")
    aperture = aperture_area_m2(config.get("aperture_diameter_m"))
    spread = config.get("angular_spread_factor", 1.0)

    per_support = []
    seen = set()
    blocked_total = 0.0
    for support in supports:
        if not isinstance(support, dict):
            raise ValueError("each support must be a mapping, got %r" % (support,))
        sid = support.get("id")
        if not sid:
            raise ValueError("each support needs a non-empty 'id'")
        if sid in seen:
            raise ValueError("duplicate support id %r" % (sid,))
        seen.add(sid)
        mechanism, area = _support_blocked_area_m2(support)
        blocked_total += area
        per_support.append(
            {"id": sid, "mechanism": mechanism, "blocked_area_m2": area}
        )

    fraction = blockage_fraction(blocked_total, aperture)
    gain_loss = blockage_gain_loss_db(fraction)
    findings = []
    side_lobe = None
    split = {"co_polar_dbc": FLOOR_LEVEL_DBC, "cross_polar_dbc": FLOOR_LEVEL_DBC}
    if fraction > 0.0:
        side_lobe = scattered_side_lobe_level_dbc(fraction, spread)
        split = depolarised_split_dbc(
            side_lobe, config.get("strut_tilt_to_e_field_deg", 0.0)
        )

    allowable_gain_loss = config.get("allowable_gain_loss_db")
    if allowable_gain_loss is None:
        findings.append("no-allowable-gain-loss-on-record")
    elif not _within_limit_db(gain_loss, float(allowable_gain_loss)):
        findings.append("blockage-gain-loss-exceeds-allowable")

    allowable_side_lobe = config.get("allowable_side_lobe_level_dbc")
    if allowable_side_lobe is None:
        findings.append("no-allowable-side-lobe-level-on-record")
    elif side_lobe is not None and not _within_limit_db(
        split["co_polar_dbc"], float(allowable_side_lobe)
    ):
        findings.append("scattered-side-lobe-exceeds-allowable")

    allowable_cross = config.get("allowable_cross_polar_level_dbc")
    if allowable_cross is not None and not _within_limit_db(
        split["cross_polar_dbc"], float(allowable_cross)
    ):
        findings.append("cross-polar-scattering-exceeds-allowable")

    for support in supports:
        mechanism = categorize_scattering_mechanism(support.get("field_region"))
        if mechanism != "edge-diffraction":
            continue
        level = support.get("edge_diffraction_level_dbc")
        if level is None:
            raise ValueError(
                "rim support %r needs a declared edge_diffraction_level_dbc"
                % (support.get("id"),)
            )
        if allowable_side_lobe is not None and not _within_limit_db(
            float(level), float(allowable_side_lobe)
        ):
            findings.append("edge-diffraction-exceeds-allowable")

    return {
        "aperture_area_m2": aperture,
        "blocked_area_m2": blocked_total,
        "blockage_fraction": fraction,
        "gain_loss_db": gain_loss,
        "side_lobe_level_dbc": side_lobe,
        "co_polar_level_dbc": split["co_polar_dbc"],
        "cross_polar_level_dbc": split["cross_polar_dbc"],
        "per_support": per_support,
        "findings": findings,
        "compliant": not findings,
    }
