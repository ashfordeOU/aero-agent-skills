#!/usr/bin/env python3
"""Incident electron dose limits for secondary-emission-yield coupons.

Anchor: ECSS-E-ST-20-01C clause 9.4.2.3 (multipaction design and test) --
the incident electron dose delivered to a coupon during a
secondary-emission-yield measurement is kept low enough that the beam
neither conditions nor charges the surface being measured.

Paraphrased into an implementable procedure; no standard text is
reproduced. Stdlib only, offline, deterministic.

Units used throughout:
  beam current        nA      (nanoampere)
  dwell time          s       (second)
  spot area           mm^2    (square millimetre)
  landing energy      eV      (electronvolt)
  charge density      uC/cm^2 (microcoulomb per square centimetre)
  coupon area         mm^2
"""

import math

__all__ = [
    "COUPON_CATEGORIES",
    "CAUTION_FRACTION",
    "MIN_LANDING_ENERGY_EV",
    "MAX_LANDING_ENERGY_EV",
    "REL_TOL",
    "validate_beam_settings",
    "incident_charge_density",
    "accumulated_spot_dose",
    "landing_energy_derating",
    "allowable_spot_dose",
    "is_within_allowance",
    "categorize_dose_margin",
    "max_dwell_time",
    "max_points_per_spot",
    "fresh_spots_required",
    "spots_available_on_coupon",
    "assess_incident_dose_plan",
]

# Base allowable accumulated dose on one irradiated spot, uC/cm^2, before
# electron-beam conditioning or trapped charge measurably moves the yield.
# The ordering reflects the escape route available to the deposited charge.
COUPON_CATEGORIES = {
    "grounded-metal": 5.0,
    "coated-conductor": 2.0,
    "rear-grounded-dielectric": 0.5,
    "floating-dielectric": 0.1,
}

# Dose inside this fraction of the allowance is reported as marginal.
CAUTION_FRACTION = 0.8

MIN_LANDING_ENERGY_EV = 1.0
MAX_LANDING_ENERGY_EV = 5000.0

# Representation tolerance for boundary comparisons. It absorbs the few
# ULPs a product or a sum of products can land above an exactly equal
# limit; it never widens the engineering limit itself.
REL_TOL = 1e-9


def _positive_number(value, name):
    """Return value as a float, or raise ValueError if it is not usable."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def _positive_int(value, name):
    """Return value as an int >= 1, or raise ValueError."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least 1, got %r" % (name, value))
    return value


def validate_beam_settings(beam):
    """Validate one electron-gun setting set for a yield measurement.

    beam is a mapping with beam_current_na, dwell_time_s, spot_area_mm2
    and landing_energy_ev. Returns a normalized dict of floats.
    Raises ValueError on a missing key, a non-numeric or non-positive
    value, or a landing energy outside the usable facility band.
    """
    if not isinstance(beam, dict):
        raise ValueError("beam settings must be a mapping, got %r" % (beam,))
    required = (
        "beam_current_na",
        "dwell_time_s",
        "spot_area_mm2",
        "landing_energy_ev",
    )
    missing = [key for key in required if key not in beam]
    if missing:
        raise ValueError("beam settings missing key(s): %s" % ", ".join(sorted(missing)))
    normalized = {key: _positive_number(beam[key], key) for key in required}
    energy = normalized["landing_energy_ev"]
    if energy < MIN_LANDING_ENERGY_EV or energy > MAX_LANDING_ENERGY_EV:
        raise ValueError(
            "landing_energy_ev %.3f outside usable band %.1f-%.1f eV"
            % (energy, MIN_LANDING_ENERGY_EV, MAX_LANDING_ENERGY_EV)
        )
    return normalized


def incident_charge_density(beam):
    """Incident charge density of one measurement point, uC/cm^2.

    current[nA] * dwell[s] = charge[nC]; spot[mm^2] / 100 = spot[cm^2];
    nC / 1000 = uC, so the combined factor is current*dwell/(10*area).
    """
    settings = validate_beam_settings(beam)
    return (settings["beam_current_na"] * settings["dwell_time_s"]) / (
        10.0 * settings["spot_area_mm2"]
    )


def accumulated_spot_dose(beam, points_per_spot):
    """Dose accumulated on one spot over points_per_spot measurements."""
    count = _positive_int(points_per_spot, "points_per_spot")
    return incident_charge_density(beam) * count


def landing_energy_derating(landing_energy_ev):
    """Derating factor applied to the base dose allowance for energy.

    Shallow landing energies deposit the whole dose inside the emitting
    layer; high energies implant below the escape depth and build an
    embedded charge layer. Only the mid band keeps the full allowance.
    """
    energy = _positive_number(landing_energy_ev, "landing_energy_ev")
    if energy < MIN_LANDING_ENERGY_EV or energy > MAX_LANDING_ENERGY_EV:
        raise ValueError(
            "landing_energy_ev %.3f outside usable band %.1f-%.1f eV"
            % (energy, MIN_LANDING_ENERGY_EV, MAX_LANDING_ENERGY_EV)
        )
    if energy < 50.0:
        return 0.5
    if energy < 200.0:
        return 0.75
    if energy <= 2000.0:
        return 1.0
    return 0.8


def allowable_spot_dose(coupon_category, landing_energy_ev):
    """Allowable accumulated dose on one spot, uC/cm^2.

    Raises ValueError on an unrecognized coupon category: an unknown
    coupon is never defaulted to the most permissive allowance.
    """
    if not isinstance(coupon_category, str) or not coupon_category.strip():
        raise ValueError("coupon_category must be a non-empty string")
    key = coupon_category.strip().lower()
    if key not in COUPON_CATEGORIES:
        raise ValueError(
            "unknown coupon_category %r; known: %s"
            % (coupon_category, ", ".join(sorted(COUPON_CATEGORIES)))
        )
    return COUPON_CATEGORIES[key] * landing_energy_derating(landing_energy_ev)


def is_within_allowance(dose_uc_cm2, allowance_uc_cm2):
    """True when an accumulated dose is at or below its allowance.

    A dose exactly at the allowance is inside it. Because an accumulated
    dose is a sum of products, an exactly-equal case can land a few ULPs
    high; REL_TOL absorbs that representation error. The engineering
    allowance itself is never widened.
    """
    dose = _positive_number(dose_uc_cm2, "dose_uc_cm2")
    allowance = _positive_number(allowance_uc_cm2, "allowance_uc_cm2")
    return dose <= allowance or math.isclose(dose, allowance, rel_tol=REL_TOL)


def categorize_dose_margin(dose_uc_cm2, allowance_uc_cm2):
    """Categorize an accumulated dose against its allowance.

    Returns "compliant" below the caution band, "marginal" inside it and
    up to the allowance inclusive, and "exceeded" above the allowance.
    """
    if not is_within_allowance(dose_uc_cm2, allowance_uc_cm2):
        return "exceeded"
    dose = float(dose_uc_cm2)
    caution = float(allowance_uc_cm2) * CAUTION_FRACTION
    if dose > caution and not math.isclose(dose, caution, rel_tol=REL_TOL):
        return "marginal"
    return "compliant"


def max_dwell_time(beam, allowance_uc_cm2, points_per_spot):
    """Longest per-point dwell time that keeps the spot dose in allowance."""
    settings = validate_beam_settings(beam)
    allowance = _positive_number(allowance_uc_cm2, "allowance_uc_cm2")
    count = _positive_int(points_per_spot, "points_per_spot")
    return (allowance * 10.0 * settings["spot_area_mm2"]) / (
        settings["beam_current_na"] * count
    )


def max_points_per_spot(beam, allowance_uc_cm2):
    """Measurement points one spot can take before the allowance is used up.

    Returns 0 when a single point already exceeds the allowance, which is
    a hard finding: no dwell count makes that setting acceptable.
    """
    per_point = incident_charge_density(beam)
    allowance = _positive_number(allowance_uc_cm2, "allowance_uc_cm2")
    ratio = allowance / per_point
    floor = math.floor(ratio)
    # A ratio that is an exact integer in exact arithmetic can land a few
    # ULPs below it; recover that point instead of discarding it.
    if math.isclose(ratio, floor + 1.0, rel_tol=REL_TOL):
        floor += 1
    return int(floor)


def fresh_spots_required(total_points, points_per_spot_allowed):
    """Fresh unirradiated spots a campaign of total_points needs."""
    total = _positive_int(total_points, "total_points")
    allowed = points_per_spot_allowed
    if isinstance(allowed, bool) or not isinstance(allowed, int):
        raise ValueError("points_per_spot_allowed must be an integer, got %r" % (allowed,))
    if allowed < 0:
        raise ValueError("points_per_spot_allowed must not be negative")
    if allowed == 0:
        raise ValueError(
            "points_per_spot_allowed is 0: a single point already exceeds the "
            "dose allowance, so no number of fresh spots recovers the plan"
        )
    return int(math.ceil(total / float(allowed)))


def spots_available_on_coupon(coupon_area_mm2, spot_area_mm2, packing_efficiency=0.5):
    """Non-overlapping irradiation spots a coupon can supply.

    packing_efficiency accounts for edge keep-out and the guard ring
    between adjacent spots; it must lie in (0, 1].
    """
    coupon = _positive_number(coupon_area_mm2, "coupon_area_mm2")
    spot = _positive_number(spot_area_mm2, "spot_area_mm2")
    packing = _positive_number(packing_efficiency, "packing_efficiency")
    if packing > 1.0:
        raise ValueError("packing_efficiency must be <= 1.0, got %r" % (packing_efficiency,))
    if spot > coupon:
        raise ValueError(
            "spot_area_mm2 %.4f exceeds coupon_area_mm2 %.4f" % (spot, coupon)
        )
    return int(math.floor((coupon * packing) / spot))


def assess_incident_dose_plan(plan):
    """Assess a full incident-dose plan for one coupon.

    plan keys: coupon_category, beam (mapping), points_per_spot,
    total_points, coupon_area_mm2, optional packing_efficiency.
    Returns a report dict; raises ValueError on any invalid input.
    """
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping, got %r" % (plan,))
    for key in ("coupon_category", "beam", "points_per_spot", "total_points",
                "coupon_area_mm2"):
        if key not in plan:
            raise ValueError("plan missing key %r" % key)

    beam = plan["beam"]
    settings = validate_beam_settings(beam)
    points_per_spot = _positive_int(plan["points_per_spot"], "points_per_spot")
    total_points = _positive_int(plan["total_points"], "total_points")
    if total_points < points_per_spot:
        raise ValueError(
            "total_points %d is fewer than points_per_spot %d"
            % (total_points, points_per_spot)
        )
    packing = plan.get("packing_efficiency", 0.5)

    per_point = incident_charge_density(beam)
    spot_dose = per_point * points_per_spot
    allowance = allowable_spot_dose(
        plan["coupon_category"], settings["landing_energy_ev"]
    )
    status = categorize_dose_margin(spot_dose, allowance)
    allowed_points = max_points_per_spot(beam, allowance)

    findings = []
    if status == "exceeded":
        findings.append(
            "accumulated spot dose %.4f uC/cm2 exceeds allowance %.4f uC/cm2"
            % (spot_dose, allowance)
        )
    elif status == "marginal":
        findings.append(
            "accumulated spot dose %.4f uC/cm2 is inside the caution band of "
            "allowance %.4f uC/cm2" % (spot_dose, allowance)
        )

    if allowed_points == 0:
        findings.append(
            "a single measurement point already exceeds the allowance; shorten "
            "dwell time, widen the spot or lower the beam current"
        )
        spots_needed = None
    else:
        spots_needed = fresh_spots_required(total_points, allowed_points)

    spots_free = spots_available_on_coupon(
        plan["coupon_area_mm2"], settings["spot_area_mm2"], packing
    )
    if spots_needed is not None and spots_needed > spots_free:
        findings.append(
            "campaign needs %d fresh spots but the coupon supplies %d"
            % (spots_needed, spots_free)
        )

    return {
        "coupon_category": plan["coupon_category"].strip().lower(),
        "per_point_dose_uc_cm2": per_point,
        "accumulated_spot_dose_uc_cm2": spot_dose,
        "allowance_uc_cm2": allowance,
        "derating_factor": landing_energy_derating(settings["landing_energy_ev"]),
        "status": status,
        "max_points_per_spot": allowed_points,
        "max_dwell_time_s": max_dwell_time(beam, allowance, points_per_spot),
        "fresh_spots_required": spots_needed,
        "fresh_spots_available": spots_free,
        "findings": findings,
        "acceptable": not findings,
    }
