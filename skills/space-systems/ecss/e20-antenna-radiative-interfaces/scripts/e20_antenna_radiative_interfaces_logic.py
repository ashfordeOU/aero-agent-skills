"""Radiative interfaces between an antenna and its surrounding structure.

Anchor: ECSS-E-ST-20C clause 7.2.3.2 (electromagnetic interaction between the
antenna and surrounding structure or appendages, assessed from phase B).
Paraphrased into an implementable procedure; no standard text is reproduced.

Offline, deterministic, stdlib only. The module turns a declared antenna plus
its neighbouring hardware into:

  * the field-region each item sits in (reactive, radiating near field, far
    field) and the beam sector it falls in,
  * an interaction path per item (main-beam-blockage, near-field-coupling,
    side-lobe-scattering, port-to-port-coupling, no-interaction-path),
  * a re-radiated level, the pattern-ripple it drives and the
    boresight-pointing perturbation it causes,
  * a port-to-port-isolation figure for a neighbouring radiating port,
  * a finding list judged against the declared allowables.
"""

import math

SPEED_OF_LIGHT_M_S = 299792458.0

#: Absolute tolerance applied when a computed figure meets a declared limit
#: exactly. Such a figure is a difference or sum of logarithms and can land a
#: few ULPs on the wrong side of a limit it physically satisfies; the
#: engineering limit itself is never widened.
LIMIT_TOLERANCE = 1e-9

#: Level reported for a re-radiated contribution of exactly zero amplitude.
FLOOR_LEVEL_DBC = -300.0

#: Reactive near-field boundary 0.62*sqrt(D^3/lambda) and far-field boundary
#: 2*D^2/lambda, the standard aperture-antenna zone radii.
REACTIVE_NEAR_FIELD_FACTOR = 0.62
FAR_FIELD_FACTOR = 2.0

#: First-null half-angle of a uniformly illuminated circular aperture,
#: expressed as a multiple of the half-power half-angle.
FIRST_NULL_TO_HALF_BEAM = 2.39

FIELD_REGIONS = ("reactive-near-field", "radiating-near-field", "far-field")
BEAM_SECTORS = ("main-beam", "main-lobe-skirt", "side-lobe-region")

#: Project phases in order; the clause places this assessment from phase B.
PHASE_ORDER = ("a", "b", "c", "d", "e")
ASSESSMENT_FIRST_PHASE = "b"


def _positive(value, label):
    try:
        out = float(value)
    except (TypeError, ValueError):
        raise ValueError("%s must be a number, got %r" % (label, value))
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return out


def _within_limit(value, limit):
    return value <= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def _at_least(value, limit):
    return value >= limit or math.isclose(
        value, limit, rel_tol=0.0, abs_tol=LIMIT_TOLERANCE
    )


def wavelength_m(frequency_hz):
    """Free-space wavelength at the given frequency."""
    return SPEED_OF_LIGHT_M_S / _positive(frequency_hz, "frequency_hz")


def reactive_near_field_radius_m(aperture_diameter_m, wave_length_m):
    """Outer radius of the reactive near field of an aperture antenna."""
    d = _positive(aperture_diameter_m, "aperture_diameter_m")
    lam = _positive(wave_length_m, "wave_length_m")
    return REACTIVE_NEAR_FIELD_FACTOR * math.sqrt(d ** 3 / lam)


def far_field_distance_m(aperture_diameter_m, wave_length_m):
    """Distance beyond which the aperture pattern is fully formed."""
    d = _positive(aperture_diameter_m, "aperture_diameter_m")
    lam = _positive(wave_length_m, "wave_length_m")
    return FAR_FIELD_FACTOR * d * d / lam


def field_region_at(distance_m, aperture_diameter_m, wave_length_m):
    """Field region an item at the given distance from the antenna sits in."""
    dist = _positive(distance_m, "distance_m")
    reactive = reactive_near_field_radius_m(aperture_diameter_m, wave_length_m)
    far = far_field_distance_m(aperture_diameter_m, wave_length_m)
    if _at_least(dist, far):
        return "far-field"
    if _within_limit(dist, reactive):
        return "reactive-near-field"
    return "radiating-near-field"


def beam_sector(angular_offset_deg, half_power_beamwidth_deg):
    """Sector of the antenna pattern an item at the given offset falls in."""
    offset = float(angular_offset_deg)
    if not 0.0 <= offset <= 180.0:
        raise ValueError(
            "angular_offset_deg must lie in [0, 180], got %r" % (angular_offset_deg,)
        )
    hpbw = _positive(half_power_beamwidth_deg, "half_power_beamwidth_deg")
    if hpbw >= 180.0:
        raise ValueError(
            "half_power_beamwidth_deg must be < 180, got %r" % (half_power_beamwidth_deg,)
        )
    half_beam = hpbw / 2.0
    if _within_limit(offset, half_beam):
        return "main-beam"
    if _within_limit(offset, FIRST_NULL_TO_HALF_BEAM * half_beam):
        return "main-lobe-skirt"
    return "side-lobe-region"


def categorize_radiative_interaction(region, sector, is_radiating_port, illuminated):
    """Reduce geometry and hardware type to one interaction path."""
    if region not in FIELD_REGIONS:
        raise ValueError(
            "uncategorized field region %r; expected one of %s"
            % (region, ", ".join(FIELD_REGIONS))
        )
    if sector not in BEAM_SECTORS:
        raise ValueError(
            "uncategorized beam sector %r; expected one of %s"
            % (sector, ", ".join(BEAM_SECTORS))
        )
    if not isinstance(is_radiating_port, bool):
        raise ValueError("is_radiating_port must be a bool, got %r" % (is_radiating_port,))
    if not isinstance(illuminated, bool):
        raise ValueError("illuminated must be a bool, got %r" % (illuminated,))
    if is_radiating_port:
        return "port-to-port-coupling"
    if not illuminated:
        return "no-interaction-path"
    if sector == "main-beam":
        return "main-beam-blockage"
    if region != "far-field":
        return "near-field-coupling"
    if sector == "main-lobe-skirt":
        return "main-lobe-scattering"
    return "side-lobe-scattering"


def free_space_transmission_loss_db(distance_m, wave_length_m):
    """Spreading loss between two isotropic points, positive decibels."""
    dist = _positive(distance_m, "distance_m")
    lam = _positive(wave_length_m, "wave_length_m")
    return 20.0 * math.log10(4.0 * math.pi * dist / lam)


def port_to_port_isolation_db(tx_gain_dbi, rx_gain_dbi, distance_m, wave_length_m):
    """Isolation between two radiating ports, positive decibels."""
    loss = free_space_transmission_loss_db(distance_m, wave_length_m)
    return loss - float(tx_gain_dbi) - float(rx_gain_dbi)


def reradiated_level_dbc(
    gain_toward_item_dbi, peak_gain_dbi, radar_cross_section_m2, distance_m
):
    """Level of an appendage's re-radiation relative to the main-beam peak."""
    sigma = _positive(radar_cross_section_m2, "radar_cross_section_m2")
    dist = _positive(distance_m, "distance_m")
    illumination = float(gain_toward_item_dbi) - float(peak_gain_dbi)
    if illumination > 0.0:
        raise ValueError(
            "gain_toward_item_dbi (%r) cannot exceed peak_gain_dbi (%r)"
            % (gain_toward_item_dbi, peak_gain_dbi)
        )
    intercept = 10.0 * math.log10(sigma / (4.0 * math.pi * dist * dist))
    return illumination + intercept


def pattern_ripple_db(scattered_level_dbc):
    """Peak-to-peak pattern ripple caused by a coherent scattered field."""
    level = float(scattered_level_dbc)
    if not math.isfinite(level):
        raise ValueError("scattered_level_dbc must be finite, got %r" % (scattered_level_dbc,))
    ratio = 10.0 ** (level / 20.0)
    if ratio >= 1.0:
        raise ValueError(
            "scattered_level_dbc (%r) reaches the direct field; the ripple model "
            "no longer applies and a full-wave model is required"
            % (scattered_level_dbc,)
        )
    return 20.0 * math.log10((1.0 + ratio) / (1.0 - ratio))


def pointing_perturbation_deg(scattered_level_dbc, half_power_beamwidth_deg):
    """First-order boresight-pointing shift caused by a scattered field."""
    hpbw = _positive(half_power_beamwidth_deg, "half_power_beamwidth_deg")
    level = float(scattered_level_dbc)
    if not math.isfinite(level):
        raise ValueError("scattered_level_dbc must be finite, got %r" % (scattered_level_dbc,))
    ratio = 10.0 ** (level / 20.0)
    if ratio >= 1.0:
        raise ValueError(
            "scattered_level_dbc (%r) reaches the direct field; the first-order "
            "pointing model no longer applies" % (scattered_level_dbc,)
        )
    return 0.5 * hpbw * ratio


def assessment_due(project_phase):
    """True once the project has reached the phase the clause anchors to."""
    if not isinstance(project_phase, str):
        raise ValueError("project_phase must be a string, got %r" % (project_phase,))
    key = project_phase.strip().lower()
    if key not in PHASE_ORDER:
        raise ValueError(
            "uncategorized project_phase %r; expected one of %s"
            % (project_phase, ", ".join(PHASE_ORDER))
        )
    return PHASE_ORDER.index(key) >= PHASE_ORDER.index(ASSESSMENT_FIRST_PHASE)


def assess_radiative_interface(antenna, item):
    """Assess one neighbouring item against the antenna."""
    if not isinstance(antenna, dict):
        raise ValueError("antenna must be a mapping, got %r" % (type(antenna).__name__,))
    if not isinstance(item, dict):
        raise ValueError("item must be a mapping, got %r" % (type(item).__name__,))
    item_id = item.get("id")
    if not item_id:
        raise ValueError("item needs a non-empty 'id'")

    lam = wavelength_m(antenna.get("frequency_hz"))
    diameter = antenna.get("aperture_diameter_m")
    hpbw = antenna.get("half_power_beamwidth_deg")
    peak_gain = antenna.get("peak_gain_dbi")
    if peak_gain is None:
        raise ValueError("antenna needs a peak_gain_dbi")

    distance = item.get("distance_m")
    region = field_region_at(distance, diameter, lam)
    sector = beam_sector(item.get("angular_offset_deg", 180.0), hpbw)
    path = categorize_radiative_interaction(
        region,
        sector,
        bool(item.get("is_radiating_port", False)),
        bool(item.get("illuminated", True)),
    )

    result = {
        "id": item_id,
        "field_region": region,
        "beam_sector": sector,
        "interaction_path": path,
        "reradiated_level_dbc": None,
        "pattern_ripple_db": None,
        "pointing_perturbation_deg": None,
        "port_isolation_db": None,
    }
    findings = []

    if path == "port-to-port-coupling":
        isolation = port_to_port_isolation_db(
            item.get("gain_toward_item_dbi", peak_gain),
            item.get("port_gain_dbi", 0.0),
            distance,
            lam,
        )
        result["port_isolation_db"] = isolation
        required = antenna.get("required_port_isolation_db")
        if required is None:
            findings.append("no-required-port-isolation-on-record")
        elif not _at_least(isolation, float(required)):
            findings.append("port-to-port-isolation-below-required")
        if region != "far-field":
            findings.append("near-field-coupling-requires-full-wave-model")
    elif path == "main-beam-blockage":
        findings.append("appendage-inside-the-main-beam")
    elif path == "near-field-coupling":
        findings.append("near-field-coupling-requires-full-wave-model")
    elif path in ("main-lobe-scattering", "side-lobe-scattering"):
        level = reradiated_level_dbc(
            item.get("gain_toward_item_dbi"),
            peak_gain,
            item.get("radar_cross_section_m2"),
            distance,
        )
        ripple = pattern_ripple_db(level)
        shift = pointing_perturbation_deg(level, hpbw)
        result["reradiated_level_dbc"] = level
        result["pattern_ripple_db"] = ripple
        result["pointing_perturbation_deg"] = shift
        allowable_ripple = antenna.get("allowable_pattern_ripple_db")
        if allowable_ripple is None:
            findings.append("no-allowable-pattern-ripple-on-record")
        elif not _within_limit(ripple, float(allowable_ripple)):
            findings.append("pattern-ripple-exceeds-allowable")
        allowable_shift = antenna.get("allowable_boresight_perturbation_deg")
        if allowable_shift is not None and not _within_limit(
            shift, float(allowable_shift)
        ):
            findings.append("boresight-perturbation-exceeds-allowable")

    result["findings"] = findings
    result["compliant"] = not findings
    return result


def assess_surrounding_items(antenna, items):
    """Clause 7.2.3.2 assessment of an antenna against all its neighbours."""
    if not isinstance(antenna, dict):
        raise ValueError("antenna must be a mapping, got %r" % (type(antenna).__name__,))
    if not assessment_due(antenna.get("project_phase", ASSESSMENT_FIRST_PHASE)):
        return {
            "assessment_due": False,
            "status": "deferred-until-phase-b",
            "items": [],
            "worst_pattern_ripple_db": None,
            "minimum_port_isolation_db": None,
            "non_compliant_items": [],
            "compliant": False,
        }
    if not isinstance(items, list) or not items:
        raise ValueError("items must be a non-empty list")
    seen = set()
    results = []
    for item in items:
        result = assess_radiative_interface(antenna, item)
        if result["id"] in seen:
            raise ValueError("duplicate item id %r" % (result["id"],))
        seen.add(result["id"])
        results.append(result)
    ripples = [r["pattern_ripple_db"] for r in results if r["pattern_ripple_db"] is not None]
    isolations = [r["port_isolation_db"] for r in results if r["port_isolation_db"] is not None]
    return {
        "assessment_due": True,
        "status": "assessed",
        "items": results,
        "worst_pattern_ripple_db": max(ripples) if ripples else None,
        "minimum_port_isolation_db": min(isolations) if isolations else None,
        "non_compliant_items": [r["id"] for r in results if not r["compliant"]],
        "compliant": all(r["compliant"] for r in results),
    }
