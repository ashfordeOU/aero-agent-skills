#!/usr/bin/env python3
"""Array-fed reflector antenna assessment (ECSS-E-ST-20C clause 7.2.2.2.4).

Deterministic, offline, stdlib-only engineering logic for the clause
7.2.2.2.4 case: an antenna whose feed is itself a radiating array focused
into a reflector is subject to the reflector provision family AND the
radiating-array provision family at the same time. Neither family alone
closes the design.

The procedure implemented here is a paraphrase of the clause intent, not a
reproduction of the standard: the clause is cited as the traceability anchor
only.

Pipeline
--------
1. Declared provisions -> coverage of both provision families.
2. Reflector side -> surface, illumination and spillover efficiency.
3. Feed-array side -> feed-cluster excitation efficiency and arrangement.
4. Feed offset -> beam deviation, beam squint, offset in beamwidths.
5. Offset in beamwidths -> scan loss.
6. Efficiencies + scan loss + network loss -> realized per-beam gain.
7. Per-beam gain vs required gain -> findings and a verdict.
"""

from __future__ import annotations

import math

__all__ = [
    "PROVISION_FAMILIES",
    "provision_coverage",
    "categorize_feed_arrangement",
    "surface_efficiency",
    "illumination_efficiency",
    "spillover_efficiency",
    "feed_cluster_efficiency",
    "total_aperture_efficiency",
    "beam_deviation_factor",
    "beam_squint_deg",
    "beamwidth_deg",
    "scan_loss_db",
    "reflector_gain_dbi",
    "beam_gain_budget",
    "assess_array_fed_reflector",
]

PROVISION_FAMILIES = ("reflector", "radiating-array")

MAX_RUZE_RATIO = 0.25
MIN_F_OVER_D = 0.15
MAX_F_OVER_D = 10.0
BEAMWIDTH_CONSTANT_DEG = 65.9
DEFAULT_SCAN_LOSS_COEFFICIENT = 0.4
MAX_SCAN_OFFSET_BEAMWIDTHS = 20.0

REL_TOL = 1e-9
ABS_TOL = 1e-12


# --- small helpers ---------------------------------------------------------


def _as_float(value, name):
    """Coerce to a finite float or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _ge(value, limit):
    """True when value >= limit, absorbing float representation error.

    A realized gain assembled from a sum of dB terms can land a few ULPs
    below a requirement it physically meets; the requirement itself is never
    relaxed, only the binary representation of an equal value is tolerated.
    """
    return value >= limit or math.isclose(value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL)


# --- 1. both provision families --------------------------------------------


def provision_coverage(provisions):
    """Check that both provision families are declared and verified.

    The clause point of an array-fed reflector is that the reflector
    provisions and the radiating-array provisions both apply; a design
    dossier that carries only one family is incomplete by construction.
    """
    if not isinstance(provisions, (list, tuple)):
        raise ValueError("provisions must be a list of mappings")
    if not provisions:
        raise ValueError("provisions must not be empty: both families are required")
    seen = []
    covered = set()
    unverified = []
    for entry in provisions:
        if not isinstance(entry, dict):
            raise ValueError("each provision must be a mapping, got %r" % (entry,))
        ident = entry.get("id")
        if not isinstance(ident, str) or not ident:
            raise ValueError("each provision needs a non-empty string id, got %r" % (ident,))
        if ident in seen:
            raise ValueError("duplicate provision id %r" % (ident,))
        seen.append(ident)
        family = entry.get("family")
        if family not in PROVISION_FAMILIES:
            raise ValueError(
                "provision %r has family %r; expected one of %s"
                % (ident, family, list(PROVISION_FAMILIES))
            )
        verified = entry.get("verified", False)
        if not isinstance(verified, bool):
            raise ValueError("provision %r: 'verified' must be a boolean" % (ident,))
        covered.add(family)
        if not verified:
            unverified.append(ident)
    missing = [family for family in PROVISION_FAMILIES if family not in covered]
    return {
        "covered_families": sorted(covered),
        "missing_families": missing,
        "unverified": sorted(unverified),
        "complete": not missing and not unverified,
    }


def categorize_feed_arrangement(feeds_per_beam):
    """Categorize the feed cluster that forms one beam."""
    if isinstance(feeds_per_beam, bool) or not isinstance(feeds_per_beam, int):
        raise ValueError("feeds_per_beam must be an int, got %r" % (feeds_per_beam,))
    if feeds_per_beam < 1:
        raise ValueError("feeds_per_beam must be >= 1, got %r" % (feeds_per_beam,))
    if feeds_per_beam == 1:
        return "single-feed-per-beam"
    return "multiple-feed-per-beam"


# --- 2. reflector side -----------------------------------------------------


def surface_efficiency(surface_rms_wavelengths):
    """Reflector surface efficiency from the RMS profile error (Ruze)."""
    rms = _as_float(surface_rms_wavelengths, "surface_rms_wavelengths")
    if rms < 0.0:
        raise ValueError("surface_rms_wavelengths must be >= 0, got %r" % (surface_rms_wavelengths,))
    if rms > MAX_RUZE_RATIO:
        raise ValueError(
            "surface_rms_wavelengths %.3f exceeds the %.2f small-error regime of the "
            "Ruze model; a dedicated scattering assessment is required"
            % (rms, MAX_RUZE_RATIO)
        )
    return math.exp(-((4.0 * math.pi * rms) ** 2))


def _edge_voltage(edge_taper_db):
    taper = _as_float(edge_taper_db, "edge_taper_db")
    if taper <= 0.0:
        raise ValueError(
            "edge_taper_db must be > 0 (the rim is illuminated below the centre), got %r"
            % (edge_taper_db,)
        )
    return taper, 10.0 ** (-taper / 20.0)


def illumination_efficiency(edge_taper_db):
    """Taper efficiency of a quadratic-on-pedestal reflector illumination."""
    _taper, t = _edge_voltage(edge_taper_db)
    numerator = 2.0 * ((1.0 + t) / 4.0) ** 2
    denominator = (t * t) / 2.0 + (t * (1.0 - t)) / 2.0 + ((1.0 - t) ** 2) / 6.0
    if denominator <= 0.0:
        raise ValueError("degenerate illumination distribution")
    return numerator / denominator


def spillover_efficiency(edge_taper_db):
    """Fraction of feed-cluster radiation intercepted by the reflector rim."""
    taper, _t = _edge_voltage(edge_taper_db)
    return 1.0 - 10.0 ** (-taper / 10.0)


# --- 3. feed-array side ----------------------------------------------------


def feed_cluster_efficiency(amplitudes):
    """Excitation efficiency of the feed cluster: (sum a)^2 / (N * sum a^2)."""
    if not isinstance(amplitudes, (list, tuple)) or not amplitudes:
        raise ValueError("amplitudes must be a non-empty sequence")
    total = 0.0
    power = 0.0
    for index, value in enumerate(amplitudes):
        amplitude = _as_float(value, "amplitudes[%d]" % index)
        if amplitude < 0.0:
            raise ValueError("amplitudes[%d] must be >= 0, got %r" % (index, value))
        total += amplitude
        power += amplitude * amplitude
    if power <= 0.0:
        raise ValueError("the feed cluster carries no excitation")
    return (total * total) / (len(amplitudes) * power)


def total_aperture_efficiency(
    surface_rms_wavelengths, edge_taper_db, amplitudes, extra_efficiency=1.0
):
    """Product of the reflector-side and feed-array-side efficiency terms."""
    extra = _as_float(extra_efficiency, "extra_efficiency")
    if not 0.0 < extra <= 1.0:
        raise ValueError("extra_efficiency must lie in (0, 1], got %r" % (extra_efficiency,))
    return (
        surface_efficiency(surface_rms_wavelengths)
        * illumination_efficiency(edge_taper_db)
        * spillover_efficiency(edge_taper_db)
        * feed_cluster_efficiency(amplitudes)
        * extra
    )


# --- 4/5. offset feeds and scan loss ---------------------------------------


def beam_deviation_factor(f_over_d):
    """Beam deviation factor of a reflector fed off its focal point."""
    ratio = _as_float(f_over_d, "f_over_d")
    if ratio <= 0.0:
        raise ValueError("f_over_d must be > 0, got %r" % (f_over_d,))
    if ratio < MIN_F_OVER_D or ratio > MAX_F_OVER_D:
        raise ValueError(
            "f_over_d %.3f is outside the %.2f-%.1f range this model covers"
            % (ratio, MIN_F_OVER_D, MAX_F_OVER_D)
        )
    k = 1.0 / (4.0 * ratio)
    return (1.0 + 0.36 * k * k) / (1.0 + k * k)


def beam_squint_deg(lateral_offset_wavelengths, focal_length_wavelengths, f_over_d):
    """Beam direction produced by a feed displaced laterally from the focus."""
    offset = _as_float(lateral_offset_wavelengths, "lateral_offset_wavelengths")
    focal = _as_float(focal_length_wavelengths, "focal_length_wavelengths")
    if focal <= 0.0:
        raise ValueError("focal_length_wavelengths must be > 0, got %r" % (focal_length_wavelengths,))
    if offset < 0.0:
        raise ValueError("lateral_offset_wavelengths must be >= 0, got %r" % (lateral_offset_wavelengths,))
    factor = beam_deviation_factor(f_over_d)
    return math.degrees(math.atan(offset / focal)) * factor


def beamwidth_deg(diameter_wavelengths):
    """Angular width of the reflector main beam between half-power points."""
    diameter = _as_float(diameter_wavelengths, "diameter_wavelengths")
    if diameter <= 0.0:
        raise ValueError("diameter_wavelengths must be > 0, got %r" % (diameter_wavelengths,))
    return BEAMWIDTH_CONSTANT_DEG / diameter


def scan_loss_db(offset_beamwidths, coefficient=DEFAULT_SCAN_LOSS_COEFFICIENT):
    """Gain lost by a beam formed off the focal point, in dB."""
    offset = _as_float(offset_beamwidths, "offset_beamwidths")
    if offset < 0.0:
        raise ValueError("offset_beamwidths must be >= 0, got %r" % (offset_beamwidths,))
    if offset > MAX_SCAN_OFFSET_BEAMWIDTHS:
        raise ValueError(
            "offset_beamwidths %.2f is beyond the %.1f-beamwidth validity of this model"
            % (offset, MAX_SCAN_OFFSET_BEAMWIDTHS)
        )
    factor = _as_float(coefficient, "coefficient")
    if factor < 0.0:
        raise ValueError("coefficient must be >= 0, got %r" % (coefficient,))
    return factor * offset * offset


def reflector_gain_dbi(diameter_wavelengths, efficiency):
    """On-axis gain of the reflector at the stated total efficiency."""
    diameter = _as_float(diameter_wavelengths, "diameter_wavelengths")
    if diameter <= 0.0:
        raise ValueError("diameter_wavelengths must be > 0, got %r" % (diameter_wavelengths,))
    eta = _as_float(efficiency, "efficiency")
    if not 0.0 < eta <= 1.0:
        raise ValueError("efficiency must lie in (0, 1], got %r" % (efficiency,))
    return 10.0 * math.log10(eta * (math.pi * diameter) ** 2)


# --- 6/7. per-beam budget and verdict --------------------------------------


def beam_gain_budget(beam, reflector, feed_array, scan_loss_coefficient=DEFAULT_SCAN_LOSS_COEFFICIENT):
    """Realized gain and margin of one beam of an array-fed reflector."""
    for item, name in ((beam, "beam"), (reflector, "reflector"), (feed_array, "feed_array")):
        if not isinstance(item, dict):
            raise ValueError("%s must be a mapping, got %r" % (name, item))
    ident = beam.get("id")
    if not isinstance(ident, str) or not ident:
        raise ValueError("each beam needs a non-empty string id, got %r" % (ident,))

    diameter = reflector.get("diameter_wavelengths")
    f_over_d = reflector.get("f_over_d")
    focal = _as_float(f_over_d, "reflector.f_over_d") * _as_float(
        diameter, "reflector.diameter_wavelengths"
    )
    efficiency = total_aperture_efficiency(
        reflector.get("surface_rms_wavelengths", 0.0),
        reflector.get("edge_taper_db"),
        feed_array.get("element_amplitudes"),
    )
    on_axis = reflector_gain_dbi(diameter, efficiency)

    squint = beam_squint_deg(
        beam.get("lateral_offset_wavelengths", 0.0), focal, f_over_d
    )
    offset_beamwidths = squint / beamwidth_deg(diameter)
    scan_loss = scan_loss_db(offset_beamwidths, scan_loss_coefficient)

    network_loss = _as_float(feed_array.get("network_loss_db", 0.0), "feed_array.network_loss_db")
    if network_loss < 0.0:
        raise ValueError("feed_array.network_loss_db must be >= 0, got %r" % (network_loss,))

    realized = on_axis - scan_loss - network_loss
    required = _as_float(beam.get("required_gain_dbi"), "beam.required_gain_dbi")
    arrangement = categorize_feed_arrangement(feed_array.get("feeds_per_beam", 1))
    return {
        "beam": ident,
        "arrangement": arrangement,
        "total_efficiency": efficiency,
        "on_axis_gain_dbi": on_axis,
        "beam_squint_deg": squint,
        "offset_beamwidths": offset_beamwidths,
        "scan_loss_db": scan_loss,
        "network_loss_db": network_loss,
        "realized_gain_dbi": realized,
        "required_gain_dbi": required,
        "margin_db": realized - required,
        "meets_requirement": _ge(realized, required),
    }


def assess_array_fed_reflector(config):
    """Full clause 7.2.2.2.4 assessment of one array-fed reflector antenna."""
    if not isinstance(config, dict):
        raise ValueError("config must be a mapping")
    reflector = config.get("reflector")
    feed_array = config.get("feed_array")
    beams = config.get("beams")
    if not isinstance(reflector, dict):
        raise ValueError("config['reflector'] must be a mapping")
    if not isinstance(feed_array, dict):
        raise ValueError("config['feed_array'] must be a mapping")
    if not isinstance(beams, (list, tuple)) or not beams:
        raise ValueError("config['beams'] must be a non-empty list")

    coverage = provision_coverage(config.get("provisions", []))
    coefficient = _as_float(
        config.get("scan_loss_coefficient", DEFAULT_SCAN_LOSS_COEFFICIENT),
        "scan_loss_coefficient",
    )

    budgets = []
    seen = []
    for beam in beams:
        budget = beam_gain_budget(beam, reflector, feed_array, coefficient)
        if budget["beam"] in seen:
            raise ValueError("duplicate beam id %r" % (budget["beam"],))
        seen.append(budget["beam"])
        budgets.append(budget)

    findings = []
    for family in coverage["missing_families"]:
        findings.append(
            "no %s provision is declared; clause 7.2.2.2.4 applies both families" % family
        )
    for ident in coverage["unverified"]:
        findings.append("provision %s is declared but not verified" % ident)
    for budget in budgets:
        if not budget["meets_requirement"]:
            findings.append(
                "beam %s realizes %.2f dBi against %.2f dBi required (%.2f dB short)"
                % (
                    budget["beam"],
                    budget["realized_gain_dbi"],
                    budget["required_gain_dbi"],
                    -budget["margin_db"],
                )
            )

    worst = min(budgets, key=lambda entry: entry["margin_db"])
    return {
        "provision_coverage": coverage,
        "beam_budgets": budgets,
        "worst_beam": worst["beam"],
        "worst_margin_db": worst["margin_db"],
        "findings": findings,
        "compliant": not findings,
    }
