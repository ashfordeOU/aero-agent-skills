#!/usr/bin/env python3
"""Radiation-hazard provisions for an electromagnetic compatibility run.

Anchor: ECSS-E-ST-20-07C clause 5.2.5.1 -- whenever a run energizes
high-drive radiating equipment or high-voltage equipment, the radiation
hazard provisions apply to the personnel working the run. The clause is
paraphrased here into an implementable procedure; no normative text is
reproduced.

The module answers four questions that the clause makes checkable:

1. which hazard category (or categories) each energized asset falls into;
2. what field power-density reaches the operator position from a radiating
   asset, and how that compares with the permissible exposure limit of the
   emitting frequency band;
3. how far back the operator position has to move when the limit is
   exceeded, and whether that position is even in the far-field where the
   inverse-square estimate is valid;
4. whether the safeguards each hazard category demands were declared
   present before the run is allowed to start.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

# Recognised asset kinds on an electromagnetic bench.
ASSET_KINDS = (
    "radiating-amplifier-chain",
    "field-generating-antenna",
    "high-voltage-supply",
    "pulse-forming-network",
    "measurement-receiver",
    "support-instrument",
)

# Hazard entry thresholds. A drive level at or above the radiating
# threshold, or an open-circuit voltage / stored energy at or above the
# electrical thresholds, pulls the asset into the clause 5.2.5.1 regime.
RADIATING_DRIVE_THRESHOLD_W = 10.0
HIGH_VOLTAGE_THRESHOLD_V = 50.0
STORED_ENERGY_THRESHOLD_J = 10.0

RADIATED_HAZARD = "radiated-field-hazard"
ELECTRICAL_HAZARD = "high-voltage-hazard"
LOW_HAZARD = "low-hazard"

# Safeguards demanded by each hazard category.
RADIATED_PROVISIONS = (
    "hazard-zone-demarcation",
    "access-interlock",
    "warning-indicator",
    "emission-cutoff-control",
)
ELECTRICAL_PROVISIONS = (
    "discharge-and-ground-tooling",
    "access-interlock",
    "warning-indicator",
    "insulated-barrier",
)
KNOWN_PROVISIONS = tuple(sorted(set(RADIATED_PROVISIONS) | set(ELECTRICAL_PROVISIONS)))

# Permissible exposure limits for occupational personnel, as a piecewise
# band table over frequency: (lower_hz, upper_hz, limit_w_per_m2). None in
# the limit slot means the band scales with frequency in megahertz.
_EXPOSURE_BANDS = (
    (1.0e5, 3.0e6, 100.0),
    (3.0e6, 3.0e7, 60.0),
    (3.0e7, 3.0e8, 10.0),
    (3.0e8, 1.5e9, None),
    (1.5e9, 3.0e11, 50.0),
)

BOUNDARY_REL_TOL = 1e-12
BOUNDARY_ABS_TOL = 1e-15


def _not_above(value, limit):
    """Return True when value <= limit, absorbing representation error.

    A power-density assembled from a product and a square can land a few
    units in the last place above a limit it is physically equal to. That
    error is absorbed at the comparison; the exposure limit itself is never
    relaxed.
    """
    if value <= limit:
        return True
    return math.isclose(value, limit, rel_tol=BOUNDARY_REL_TOL, abs_tol=BOUNDARY_ABS_TOL)


def _require_number(value, label):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return float(value)


def permissible_exposure_limit(frequency_hz):
    """Occupational power-density limit, in W/m2, for one frequency.

    The table is flat inside the low bands, falls to its minimum across the
    very-high-frequency band where whole-body absorption peaks, then rises
    again with frequency through the microwave band before flattening.
    """
    frequency = _require_number(frequency_hz, "frequency_hz")
    if frequency < _EXPOSURE_BANDS[0][0] or frequency > _EXPOSURE_BANDS[-1][1]:
        raise ValueError(
            "frequency_hz %g lies outside the tabulated exposure range" % frequency
        )
    for lower, upper, limit in _EXPOSURE_BANDS:
        if lower <= frequency <= upper:
            if limit is None:
                return (frequency / 1.0e6) / 30.0
            return limit
    raise ValueError("frequency_hz %g fell between tabulated bands" % frequency)


def far_field_power_density(drive_watt, antenna_gain_linear, distance_m):
    """Power-density at a distance from a radiating asset, in W/m2.

    Inverse-square spreading of the effective radiated level:
    S = drive * gain / (4 * pi * distance^2).
    """
    drive = _require_number(drive_watt, "drive_watt")
    gain = _require_number(antenna_gain_linear, "antenna_gain_linear")
    distance = _require_number(distance_m, "distance_m")
    if drive <= 0.0:
        raise ValueError("drive_watt must be positive")
    if gain <= 0.0:
        raise ValueError("antenna_gain_linear must be positive")
    if distance <= 0.0:
        raise ValueError("distance_m must be positive")
    return (drive * gain) / (4.0 * math.pi * distance * distance)


def minimum_standoff_distance(drive_watt, antenna_gain_linear, limit_w_per_m2):
    """Closest distance at which the power-density still meets the limit."""
    drive = _require_number(drive_watt, "drive_watt")
    gain = _require_number(antenna_gain_linear, "antenna_gain_linear")
    limit = _require_number(limit_w_per_m2, "limit_w_per_m2")
    if drive <= 0.0:
        raise ValueError("drive_watt must be positive")
    if gain <= 0.0:
        raise ValueError("antenna_gain_linear must be positive")
    if limit <= 0.0:
        raise ValueError("limit_w_per_m2 must be positive")
    return math.sqrt((drive * gain) / (4.0 * math.pi * limit))


def far_field_boundary(aperture_m, frequency_hz):
    """Distance beyond which the inverse-square estimate is trustworthy.

    Uses the usual aperture criterion 2 * D^2 / wavelength; inside it the
    field is reactive or still forming and a measured survey replaces the
    computed estimate.
    """
    aperture = _require_number(aperture_m, "aperture_m")
    frequency = _require_number(frequency_hz, "frequency_hz")
    if aperture <= 0.0:
        raise ValueError("aperture_m must be positive")
    if frequency <= 0.0:
        raise ValueError("frequency_hz must be positive")
    wavelength = 299792458.0 / frequency
    return (2.0 * aperture * aperture) / wavelength


def categorize_asset(asset):
    """Sort one energized asset into its hazard categories.

    Returns a tuple of category tokens; an asset below every threshold is
    uncategorized for clause 5.2.5.1 and comes back as low-hazard.
    """
    if not isinstance(asset, dict):
        raise ValueError("asset must be a mapping")
    kind = asset.get("kind")
    if kind not in ASSET_KINDS:
        raise ValueError(
            "unrecognized asset kind %r (expected one of %s)"
            % (kind, ", ".join(ASSET_KINDS))
        )
    drive = _require_number(asset.get("drive_watt", 0.0), "drive_watt")
    voltage = _require_number(
        asset.get("open_circuit_voltage_v", 0.0), "open_circuit_voltage_v"
    )
    energy = _require_number(asset.get("stored_energy_j", 0.0), "stored_energy_j")
    if drive < 0.0 or voltage < 0.0 or energy < 0.0:
        raise ValueError("drive, voltage and stored energy must not be negative")
    categories = []
    if drive >= RADIATING_DRIVE_THRESHOLD_W and kind in (
        "radiating-amplifier-chain",
        "field-generating-antenna",
    ):
        categories.append(RADIATED_HAZARD)
    if voltage >= HIGH_VOLTAGE_THRESHOLD_V or energy >= STORED_ENERGY_THRESHOLD_J:
        categories.append(ELECTRICAL_HAZARD)
    if not categories:
        return (LOW_HAZARD,)
    return tuple(categories)


def required_provisions(categories):
    """Safeguards demanded by a set of hazard categories."""
    if isinstance(categories, str) or not isinstance(categories, (list, tuple)):
        raise ValueError("categories must be a list or tuple of category tokens")
    required = set()
    for category in categories:
        if category == RADIATED_HAZARD:
            required.update(RADIATED_PROVISIONS)
        elif category == ELECTRICAL_HAZARD:
            required.update(ELECTRICAL_PROVISIONS)
        elif category == LOW_HAZARD:
            continue
        else:
            raise ValueError("unrecognized hazard category %r" % (category,))
    return frozenset(required)


def evaluate_asset(asset, operator_standoff_m):
    """Full clause 5.2.5.1 evaluation of one energized asset."""
    standoff = _require_number(operator_standoff_m, "operator_standoff_m")
    if standoff <= 0.0:
        raise ValueError("operator_standoff_m must be positive")
    asset_id = asset.get("id") if isinstance(asset, dict) else None
    if not asset_id or not isinstance(asset_id, str):
        raise ValueError("each asset needs a non-empty string 'id'")
    categories = categorize_asset(asset)
    declared = asset.get("provisions", ())
    if isinstance(declared, str) or not isinstance(declared, (list, tuple, set, frozenset)):
        raise ValueError("asset 'provisions' must be a collection of provision tokens")
    for provision in declared:
        if provision not in KNOWN_PROVISIONS:
            raise ValueError("unrecognized provision %r" % (provision,))
    missing = sorted(required_provisions(categories) - set(declared))
    findings = []
    for provision in missing:
        findings.append(
            {"asset": asset_id, "finding": "provision-absent", "provision": provision}
        )
    exposure = None
    if RADIATED_HAZARD in categories:
        frequency = asset.get("frequency_hz")
        if frequency is None:
            raise ValueError("a radiating asset must declare 'frequency_hz'")
        limit = permissible_exposure_limit(frequency)
        density = far_field_power_density(
            asset["drive_watt"], asset.get("antenna_gain_linear", 1.0), standoff
        )
        compliant = _not_above(density, limit)
        required_distance = minimum_standoff_distance(
            asset["drive_watt"], asset.get("antenna_gain_linear", 1.0), limit
        )
        exposure = {
            "frequency_hz": float(frequency),
            "limit_w_per_m2": limit,
            "power_density_w_per_m2": density,
            "within_limit": compliant,
            "minimum_standoff_m": required_distance,
        }
        if not compliant:
            findings.append(
                {
                    "asset": asset_id,
                    "finding": "operator-position-inside-hazard-zone",
                    "minimum_standoff_m": required_distance,
                }
            )
        aperture = asset.get("aperture_m")
        if aperture is not None:
            boundary = far_field_boundary(aperture, frequency)
            exposure["far_field_boundary_m"] = boundary
            if standoff < boundary:
                findings.append(
                    {
                        "asset": asset_id,
                        "finding": "standoff-inside-far-field-boundary",
                        "far_field_boundary_m": boundary,
                    }
                )
    return {
        "asset": asset_id,
        "categories": list(categories),
        "missing_provisions": missing,
        "exposure": exposure,
        "findings": findings,
    }


def assess_run_safety_provisions(assets, operator_standoff_m):
    """Aggregate the clause 5.2.5.1 verdict for one bench configuration."""
    if not isinstance(assets, (list, tuple)) or not assets:
        raise ValueError("at least one energized asset must be declared")
    seen = set()
    evaluations = []
    findings = []
    for asset in assets:
        evaluation = evaluate_asset(asset, operator_standoff_m)
        if evaluation["asset"] in seen:
            raise ValueError("duplicate asset id %r" % evaluation["asset"])
        seen.add(evaluation["asset"])
        evaluations.append(evaluation)
        findings.extend(evaluation["findings"])
    hazardous = [
        item["asset"] for item in evaluations if LOW_HAZARD not in item["categories"]
    ]
    return {
        "assets": evaluations,
        "hazardous_assets": hazardous,
        "findings": findings,
        "run_permitted": not findings,
    }
