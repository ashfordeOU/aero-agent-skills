#!/usr/bin/env python3
"""Representativeness of secondary-emission-yield coupons.

Anchor: ECSS-E-ST-20-01C clause 9.4.3 (multipaction design and test) --
a coupon submitted for a secondary-emission-yield measurement is
manufactured so that its material, production route and surface
treatment match the hardware whose multipactor margin the measurement
will feed.

Paraphrased into an implementable procedure; no standard text is
reproduced. Stdlib only, offline, deterministic.

Units used throughout:
  surface finish (Ra)   um    (micrometre)
  measurement area      mm^2
  probe-beam footprint  mm^2
  storage age           days
"""

import math

__all__ = [
    "GOVERNING_ATTRIBUTES",
    "SUPPORTING_ATTRIBUTES",
    "REQUIRED_ATTRIBUTES",
    "DEFAULT_FINISH_TOLERANCE_FRACTION",
    "DEFAULT_KEEP_OUT_FACTOR",
    "DEFAULT_SHELF_LIFE_DAYS",
    "REL_TOL",
    "normalize_attribute",
    "validate_definition",
    "compare_governing_attributes",
    "surface_finish_deviation",
    "finish_within_tolerance",
    "compare_supporting_attributes",
    "coupon_area_adequate",
    "storage_age_finding",
    "assess_sample_representativeness",
]

# Attributes that govern the emitting layer: a mismatch voids the
# coupon and no written justification recovers it.
GOVERNING_ATTRIBUTES = ("base_material", "surface_treatment", "production_route")

# Attributes that shift the yield within a narrower band: a mismatch is
# a finding a recorded justification can close.
SUPPORTING_ATTRIBUTES = ("cleaning_process", "bake_out_state", "surface_finish_ra_um")

REQUIRED_ATTRIBUTES = GOVERNING_ATTRIBUTES + SUPPORTING_ATTRIBUTES

# Allowed fractional deviation of coupon roughness from flight roughness.
DEFAULT_FINISH_TOLERANCE_FRACTION = 0.25

# The coupon measurement area must exceed the probe-beam footprint by
# this factor so the beam never samples the edge or the mount.
DEFAULT_KEEP_OUT_FACTOR = 4.0

# Age beyond which an uncontrolled-storage coupon no longer represents
# freshly produced hardware.
DEFAULT_SHELF_LIFE_DAYS = 180.0

# Representation tolerance for the finish-tolerance boundary; a ratio of
# measured values can land a few ULPs above an exactly equal allowance.
# It never widens the allowance itself.
REL_TOL = 1e-9


def _positive_number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (name, value))
    number = float(value)
    if not math.isfinite(number):
        raise ValueError("%s must be finite, got %r" % (name, value))
    if number <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (name, value))
    return number


def normalize_attribute(value, name):
    """Normalize one textual attribute for comparison.

    Raises ValueError on a non-string or an empty/whitespace value: an
    attribute that was never stated is never treated as a match.
    """
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    normalized = " ".join(value.strip().lower().split())
    if not normalized:
        raise ValueError("%s is blank: the attribute was never stated" % name)
    return normalized


def validate_definition(definition, label):
    """Validate a coupon or flight-hardware definition.

    Every attribute in REQUIRED_ATTRIBUTES must be present; the textual
    ones are normalized, the surface finish must be a positive number.
    Returns the normalized definition. Raises ValueError otherwise.
    """
    if not isinstance(definition, dict):
        raise ValueError("%s definition must be a mapping, got %r" % (label, definition))
    missing = [key for key in REQUIRED_ATTRIBUTES if key not in definition]
    if missing:
        raise ValueError(
            "%s definition missing attribute(s): %s"
            % (label, ", ".join(sorted(missing)))
        )
    normalized = {}
    for key in REQUIRED_ATTRIBUTES:
        if key == "surface_finish_ra_um":
            normalized[key] = _positive_number(definition[key], "%s.%s" % (label, key))
        else:
            normalized[key] = normalize_attribute(
                definition[key], "%s.%s" % (label, key)
            )
    return normalized


def compare_governing_attributes(coupon, flight):
    """Findings for the attributes that govern the emitting layer."""
    findings = []
    for key in GOVERNING_ATTRIBUTES:
        if coupon[key] != flight[key]:
            findings.append(
                {
                    "attribute": key,
                    "severity": "voiding",
                    "coupon": coupon[key],
                    "flight": flight[key],
                    "detail": "%s differs from the flight definition (%r vs %r)"
                    % (key, coupon[key], flight[key]),
                }
            )
    return findings


def surface_finish_deviation(coupon_ra_um, flight_ra_um):
    """Fractional deviation of coupon roughness from the flight value."""
    coupon = _positive_number(coupon_ra_um, "coupon_ra_um")
    flight = _positive_number(flight_ra_um, "flight_ra_um")
    return abs(coupon - flight) / flight


def finish_within_tolerance(
    coupon_ra_um, flight_ra_um, tolerance_fraction=DEFAULT_FINISH_TOLERANCE_FRACTION
):
    """True when the roughness deviation is at or inside the allowance.

    A deviation exactly at the allowance is inside it; REL_TOL absorbs
    the representation error a ratio of measured values can carry. The
    allowance is never widened to make a coupon pass.
    """
    deviation = surface_finish_deviation(coupon_ra_um, flight_ra_um)
    allowance = _positive_number(tolerance_fraction, "tolerance_fraction")
    return deviation <= allowance or math.isclose(
        deviation, allowance, rel_tol=REL_TOL
    )


def compare_supporting_attributes(
    coupon, flight, tolerance_fraction=DEFAULT_FINISH_TOLERANCE_FRACTION
):
    """Findings for the attributes a written justification can close."""
    findings = []
    for key in ("cleaning_process", "bake_out_state"):
        if coupon[key] != flight[key]:
            findings.append(
                {
                    "attribute": key,
                    "severity": "justification-required",
                    "coupon": coupon[key],
                    "flight": flight[key],
                    "detail": "%s differs from the flight definition (%r vs %r)"
                    % (key, coupon[key], flight[key]),
                }
            )
    if not finish_within_tolerance(
        coupon["surface_finish_ra_um"], flight["surface_finish_ra_um"],
        tolerance_fraction,
    ):
        deviation = surface_finish_deviation(
            coupon["surface_finish_ra_um"], flight["surface_finish_ra_um"]
        )
        findings.append(
            {
                "attribute": "surface_finish_ra_um",
                "severity": "justification-required",
                "coupon": coupon["surface_finish_ra_um"],
                "flight": flight["surface_finish_ra_um"],
                "detail": "roughness deviates %.4f of the flight value, allowance "
                "%.4f" % (deviation, tolerance_fraction),
            }
        )
    return findings


def coupon_area_adequate(
    measurement_area_mm2, beam_footprint_mm2, keep_out_factor=DEFAULT_KEEP_OUT_FACTOR
):
    """True when the coupon carries the beam footprint plus keep-out."""
    area = _positive_number(measurement_area_mm2, "measurement_area_mm2")
    footprint = _positive_number(beam_footprint_mm2, "beam_footprint_mm2")
    factor = _positive_number(keep_out_factor, "keep_out_factor")
    if factor < 1.0:
        raise ValueError(
            "keep_out_factor must be >= 1.0 (no keep-out is not a margin), got %r"
            % (keep_out_factor,)
        )
    needed = footprint * factor
    return area >= needed or math.isclose(area, needed, rel_tol=REL_TOL)


def storage_age_finding(
    storage_age_days,
    controlled_storage,
    shelf_life_days=DEFAULT_SHELF_LIFE_DAYS,
):
    """Finding for an aged coupon, or None when the age is acceptable."""
    if isinstance(storage_age_days, bool) or not isinstance(
        storage_age_days, (int, float)
    ):
        raise ValueError("storage_age_days must be a number, got %r" % (storage_age_days,))
    age = float(storage_age_days)
    if not math.isfinite(age) or age < 0.0:
        raise ValueError("storage_age_days must be finite and non-negative")
    if not isinstance(controlled_storage, bool):
        raise ValueError(
            "controlled_storage must be a boolean, got %r" % (controlled_storage,)
        )
    allowance = _positive_number(shelf_life_days, "shelf_life_days")
    if controlled_storage:
        return None
    if age <= allowance or math.isclose(age, allowance, rel_tol=REL_TOL):
        return None
    return {
        "attribute": "storage_age_days",
        "severity": "justification-required",
        "coupon": age,
        "flight": allowance,
        "detail": "coupon held %.1f days in uncontrolled storage against a "
        "%.1f day allowance" % (age, allowance),
    }


def assess_sample_representativeness(submission):
    """Assess one coupon submission against the flight-hardware definition.

    submission keys: coupon, flight, measurement_area_mm2,
    beam_footprint_mm2, storage_age_days, controlled_storage; optional
    tolerance_fraction, keep_out_factor, shelf_life_days, and
    justifications (a mapping attribute -> recorded justification text).
    Returns a report dict; raises ValueError on any invalid input.
    """
    if not isinstance(submission, dict):
        raise ValueError("submission must be a mapping, got %r" % (submission,))
    required = (
        "coupon",
        "flight",
        "measurement_area_mm2",
        "beam_footprint_mm2",
        "storage_age_days",
        "controlled_storage",
    )
    missing = [key for key in required if key not in submission]
    if missing:
        raise ValueError("submission missing key(s): %s" % ", ".join(sorted(missing)))

    coupon = validate_definition(submission["coupon"], "coupon")
    flight = validate_definition(submission["flight"], "flight")
    tolerance = _positive_number(
        submission.get("tolerance_fraction", DEFAULT_FINISH_TOLERANCE_FRACTION),
        "tolerance_fraction",
    )
    keep_out = submission.get("keep_out_factor", DEFAULT_KEEP_OUT_FACTOR)
    shelf_life = submission.get("shelf_life_days", DEFAULT_SHELF_LIFE_DAYS)

    justifications = submission.get("justifications", {})
    if not isinstance(justifications, dict):
        raise ValueError("justifications must be a mapping, got %r" % (justifications,))

    findings = []
    findings.extend(compare_governing_attributes(coupon, flight))
    findings.extend(compare_supporting_attributes(coupon, flight, tolerance))

    if not coupon_area_adequate(
        submission["measurement_area_mm2"], submission["beam_footprint_mm2"], keep_out
    ):
        findings.append(
            {
                "attribute": "measurement_area_mm2",
                "severity": "voiding",
                "coupon": float(submission["measurement_area_mm2"]),
                "flight": float(submission["beam_footprint_mm2"]),
                "detail": "measurement area does not carry the probe-beam "
                "footprint with the required keep-out margin",
            }
        )

    age_finding = storage_age_finding(
        submission["storage_age_days"], submission["controlled_storage"], shelf_life
    )
    if age_finding is not None:
        findings.append(age_finding)

    voiding = [f for f in findings if f["severity"] == "voiding"]
    conditional = [f for f in findings if f["severity"] == "justification-required"]
    unjustified = [
        f for f in conditional
        if not str(justifications.get(f["attribute"], "")).strip()
    ]

    if voiding:
        verdict = "not-representative"
    elif unjustified:
        verdict = "not-representative"
    elif conditional:
        verdict = "conditionally-representative"
    else:
        verdict = "representative"

    return {
        "verdict": verdict,
        "findings": findings,
        "voiding_findings": voiding,
        "justification_required_findings": conditional,
        "unjustified_findings": unjustified,
        "finish_deviation": surface_finish_deviation(
            coupon["surface_finish_ra_um"], flight["surface_finish_ra_um"]
        ),
        "measurement_usable": verdict != "not-representative",
    }
