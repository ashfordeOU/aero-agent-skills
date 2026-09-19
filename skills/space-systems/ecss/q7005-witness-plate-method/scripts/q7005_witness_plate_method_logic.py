"""Witness plate and crystal microbalance sampling of organic deposition.

Anchor: ECSS-Q-ST-70-05C, direct method (deposition sampling with witness
hardware). Paraphrased into an implementable procedure; no standard text is
reproduced.

Procedure implemented here
--------------------------
1. Validate each witness coupon: area, exposure duration, pre- and
   post-exposure areal readings, and the view factor at its location.
2. Subtract the gain seen on the unexposed control coupon so handling and
   storage are not reported as deposition.
3. Convert a crystal microbalance frequency shift into an areal mass through
   the crystal's own sensitivity, refusing a shift whose sign means mass left.
4. Cross-check the coupon and the crystal and record a disagreement rather
   than averaging them.
5. Scale the coupon areal mass onto the represented surface by the ratio of
   view factors, form the deposition rate, project to the end of exposure and
   compare with the allocated budget.
"""

import math

__all__ = [
    "AGREEMENT_TOLERANCE",
    "AREAL_READING_NOISE_UG_PER_CM2",
    "areal_mass_from_frequency_shift",
    "assess_witness_sampling",
    "control_corrected_gain",
    "coupon_gross_gain",
    "cross_check_coupon_and_crystal",
    "deposition_rate_ug_per_cm2_per_h",
    "project_accumulation_ug_per_cm2",
    "scale_to_represented_surface",
    "validate_coupon",
    "validate_crystal",
    "view_factor_ratio",
]

# Below this the difference of two areal readings is weighing noise, not a
# measured deposition.
AREAL_READING_NOISE_UG_PER_CM2 = 0.02

# Coupon and crystal sample different areas and may legitimately differ by
# this relative amount before the disagreement is a finding.
AGREEMENT_TOLERANCE = 0.25


def _positive(label, value, allow_zero=False):
    """Return value as a finite float, raising on a non-numeric or non-positive."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if allow_zero:
        if out < 0.0:
            raise ValueError("%s must be non-negative, got %r" % (label, value))
    elif out <= 0.0:
        raise ValueError("%s must be strictly positive, got %r" % (label, value))
    return out


def _real(label, value):
    """Return value as a finite float of any sign."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return out


def validate_coupon(record):
    """Return the normalised witness coupon record.

    Keys: id, area_cm2, exposure_hours, pre_areal_ug_per_cm2,
    post_areal_ug_per_cm2, view_factor (0 < f <= 1), exposed (bool).
    """
    if not isinstance(record, dict):
        raise ValueError("coupon record must be a mapping")
    for key in ("id", "area_cm2", "exposure_hours", "pre_areal_ug_per_cm2",
                "post_areal_ug_per_cm2", "view_factor", "exposed"):
        if key not in record:
            raise ValueError("coupon record missing required key '%s'" % key)
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("coupon id must be a non-empty string")
    exposed = record["exposed"]
    if not isinstance(exposed, bool):
        raise ValueError("exposed must be a boolean, got %r" % (exposed,))
    view_factor = _positive("view_factor", record["view_factor"])
    if view_factor > 1.0:
        raise ValueError("view_factor must not exceed unity, got %g" % view_factor)
    return {
        "id": identifier.strip(),
        "area_cm2": _positive("area_cm2", record["area_cm2"]),
        "exposure_hours": _positive("exposure_hours", record["exposure_hours"],
                                    allow_zero=not exposed),
        "pre_areal_ug_per_cm2": _positive("pre_areal_ug_per_cm2",
                                          record["pre_areal_ug_per_cm2"],
                                          allow_zero=True),
        "post_areal_ug_per_cm2": _positive("post_areal_ug_per_cm2",
                                           record["post_areal_ug_per_cm2"],
                                           allow_zero=True),
        "view_factor": view_factor,
        "exposed": exposed,
    }


def coupon_gross_gain(coupon):
    """Return the post-minus-pre areal gain of one coupon in ug/cm2."""
    norm = validate_coupon(coupon)
    gain = norm["post_areal_ug_per_cm2"] - norm["pre_areal_ug_per_cm2"]
    if gain < -AREAL_READING_NOISE_UG_PER_CM2:
        raise ValueError(
            "coupon %s lost %g ug/cm2 past the reading noise; resolve the "
            "readings before reducing them" % (norm["id"], -gain)
        )
    return gain if gain > 0.0 else 0.0


def control_corrected_gain(exposed_coupon, control_coupon):
    """Return the exposed coupon gain with the control coupon gain removed."""
    exposed = validate_coupon(exposed_coupon)
    control = validate_coupon(control_coupon)
    if not exposed["exposed"]:
        raise ValueError("coupon %s is marked unexposed; it is not the exposed "
                         "coupon" % exposed["id"])
    if control["exposed"]:
        raise ValueError("coupon %s is marked exposed; it cannot serve as the "
                         "control" % control["id"])
    gross = coupon_gross_gain(exposed_coupon)
    handling = coupon_gross_gain(control_coupon)
    net = gross - handling
    if net < -AREAL_READING_NOISE_UG_PER_CM2:
        raise ValueError(
            "control coupon %s gained %g ug/cm2, more than exposed coupon %s "
            "gained %g; the handling chain is the dominant source"
            % (control["id"], handling, exposed["id"], gross)
        )
    net = net if net > 0.0 else 0.0
    return {
        "gross_gain_ug_per_cm2": gross,
        "control_gain_ug_per_cm2": handling,
        "net_gain_ug_per_cm2": net,
        "quantifiable": net > AREAL_READING_NOISE_UG_PER_CM2
        and abs(net - AREAL_READING_NOISE_UG_PER_CM2) > 1e-12,
    }


def validate_crystal(record):
    """Return the normalised crystal microbalance record.

    Keys: id, frequency_shift_hz (negative for deposition),
    sensitivity_hz_per_ug_per_cm2, temperature_compensated (bool).
    """
    if not isinstance(record, dict):
        raise ValueError("crystal record must be a mapping")
    for key in ("id", "frequency_shift_hz", "sensitivity_hz_per_ug_per_cm2",
                "temperature_compensated"):
        if key not in record:
            raise ValueError("crystal record missing required key '%s'" % key)
    identifier = record["id"]
    if not isinstance(identifier, str) or not identifier.strip():
        raise ValueError("crystal id must be a non-empty string")
    compensated = record["temperature_compensated"]
    if not isinstance(compensated, bool):
        raise ValueError("temperature_compensated must be a boolean")
    return {
        "id": identifier.strip(),
        "frequency_shift_hz": _real("frequency_shift_hz",
                                    record["frequency_shift_hz"]),
        "sensitivity_hz_per_ug_per_cm2": _positive(
            "sensitivity_hz_per_ug_per_cm2",
            record["sensitivity_hz_per_ug_per_cm2"],
        ),
        "temperature_compensated": compensated,
    }


def areal_mass_from_frequency_shift(crystal):
    """Return the areal mass in ug/cm2 implied by a crystal frequency shift."""
    norm = validate_crystal(crystal)
    shift = norm["frequency_shift_hz"]
    if shift > 0.0:
        raise ValueError(
            "crystal %s frequency rose by %g Hz; that is mass leaving or a "
            "thermal drift, not deposition" % (norm["id"], shift)
        )
    return (-shift) / norm["sensitivity_hz_per_ug_per_cm2"]


def cross_check_coupon_and_crystal(coupon_areal, crystal_areal,
                                   tolerance=AGREEMENT_TOLERANCE):
    """Compare the two areal masses and report whether they agree."""
    a = _positive("coupon_areal", coupon_areal, allow_zero=True)
    b = _positive("crystal_areal", crystal_areal, allow_zero=True)
    limit = _positive("tolerance", tolerance)
    mean = 0.5 * (a + b)
    if mean == 0.0:
        return {"relative_difference": 0.0, "agrees": True, "mean_ug_per_cm2": 0.0}
    relative = abs(a - b) / mean
    agrees = relative < limit or abs(relative - limit) <= 1e-12
    return {
        "relative_difference": relative,
        "agrees": agrees,
        "mean_ug_per_cm2": mean,
    }


def view_factor_ratio(surface_view_factor, coupon_view_factor):
    """Return the scaling ratio from the coupon location to the surface."""
    surface = _positive("surface_view_factor", surface_view_factor)
    coupon = _positive("coupon_view_factor", coupon_view_factor)
    for label, value in (("surface_view_factor", surface),
                         ("coupon_view_factor", coupon)):
        if value > 1.0:
            raise ValueError("%s must not exceed unity, got %g" % (label, value))
    return surface / coupon


def scale_to_represented_surface(coupon_areal, surface_view_factor,
                                 coupon_view_factor):
    """Scale a coupon areal mass onto the surface the coupon represents."""
    areal = _positive("coupon_areal", coupon_areal, allow_zero=True)
    return areal * view_factor_ratio(surface_view_factor, coupon_view_factor)


def deposition_rate_ug_per_cm2_per_h(net_areal, exposure_hours):
    """Return the deposition rate over the measured exposure interval."""
    areal = _positive("net_areal", net_areal, allow_zero=True)
    hours = _positive("exposure_hours", exposure_hours)
    return areal / hours


def project_accumulation_ug_per_cm2(rate, projection_hours, measured_hours):
    """Project an accumulation, carrying the interval the rate came from."""
    value = _positive("rate", rate, allow_zero=True)
    hours = _positive("projection_hours", projection_hours)
    basis = _positive("measured_hours", measured_hours)
    extrapolated = hours > basis and abs(hours - basis) > 1e-12
    return {
        "projected_ug_per_cm2": value * hours,
        "measured_hours": basis,
        "projection_hours": hours,
        "beyond_measured_interval": extrapolated,
    }


def assess_witness_sampling(spec):
    """Run the full witness-hardware deposition assessment.

    spec keys: exposed_coupon, control_coupon, surface_view_factor,
    allocated_ug_per_cm2, projection_hours, and optionally crystal and
    agreement_tolerance.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("exposed_coupon", "control_coupon", "surface_view_factor",
                "allocated_ug_per_cm2", "projection_hours"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    exposed = validate_coupon(spec["exposed_coupon"])
    gains = control_corrected_gain(spec["exposed_coupon"], spec["control_coupon"])
    findings = []
    if not gains["quantifiable"]:
        findings.append(
            "net coupon gain %.4f ug/cm2 is at or below the reading noise "
            "%.4f; report it as an upper bound"
            % (gains["net_gain_ug_per_cm2"], AREAL_READING_NOISE_UG_PER_CM2)
        )
    crystal_areal = None
    agreement = None
    if "crystal" in spec and spec["crystal"] is not None:
        crystal = validate_crystal(spec["crystal"])
        crystal_areal = areal_mass_from_frequency_shift(spec["crystal"])
        if not crystal["temperature_compensated"]:
            findings.append(
                "crystal %s is not temperature compensated; the shift carries "
                "a thermal component that is not deposition" % crystal["id"]
            )
        agreement = cross_check_coupon_and_crystal(
            gains["net_gain_ug_per_cm2"], crystal_areal,
            spec.get("agreement_tolerance", AGREEMENT_TOLERANCE),
        )
        if not agreement["agrees"]:
            findings.append(
                "coupon %.4f and crystal %.4f ug/cm2 differ by %.1f%%, past the "
                "agreement tolerance; resolve which is sampling the deposit "
                "rather than averaging them"
                % (gains["net_gain_ug_per_cm2"], crystal_areal,
                   100.0 * agreement["relative_difference"])
            )
    ratio = view_factor_ratio(spec["surface_view_factor"], exposed["view_factor"])
    surface_areal = scale_to_represented_surface(
        gains["net_gain_ug_per_cm2"], spec["surface_view_factor"],
        exposed["view_factor"],
    )
    if abs(ratio - 1.0) > 1e-12:
        findings.append(
            "coupon and surface view factors differ; the coupon figure was "
            "scaled by %.4f onto the represented surface" % ratio
        )
    rate = deposition_rate_ug_per_cm2_per_h(surface_areal,
                                            exposed["exposure_hours"])
    projection = project_accumulation_ug_per_cm2(
        rate, spec["projection_hours"], exposed["exposure_hours"]
    )
    if projection["beyond_measured_interval"]:
        findings.append(
            "the projection runs to %.1f h from a rate measured over %.1f h; "
            "a decaying source will not hold that rate"
            % (projection["projection_hours"], projection["measured_hours"])
        )
    allocated = _positive("allocated_ug_per_cm2", spec["allocated_ug_per_cm2"])
    projected = projection["projected_ug_per_cm2"]
    within = projected < allocated or abs(projected - allocated) <= 1e-9
    if not within:
        findings.append(
            "projected %.4f ug/cm2 exceeds the allocated %.4f ug/cm2"
            % (projected, allocated)
        )
    return {
        "coupon_gains": gains,
        "crystal_areal_ug_per_cm2": crystal_areal,
        "agreement": agreement,
        "view_factor_ratio": ratio,
        "surface_areal_ug_per_cm2": surface_areal,
        "deposition_rate_ug_per_cm2_per_h": rate,
        "projection": projection,
        "allocated_ug_per_cm2": allocated,
        "within_allocation": within,
        "findings": findings,
    }
