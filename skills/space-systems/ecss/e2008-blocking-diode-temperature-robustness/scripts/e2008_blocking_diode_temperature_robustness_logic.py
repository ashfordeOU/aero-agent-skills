#!/usr/bin/env python3
"""Blocking diode survival at the temperature extremes of service.

Anchor: ECSS-E-ST-20-08C clause 12.6.10. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause before this one maps what a blocking diode does across
temperature. This one asks a narrower and harsher question: does the
device still work after it has been taken to the ends of its service
environment and held there. The two are not the same evidence. A sweep
passes through the cold end on its way somewhere else; an exposure sits
at it, long enough for the die attach, the wire bonds and the
encapsulant to take up the strain the temperature imposes, and then the
device is measured again against what it was before.

Three things decide whether the exposure is worth anything.

The soak has to go past the service extreme, not to it. A soak that
stops exactly at the coldest temperature the mission predicts leaves no
allowance for a prediction that was optimistic, and it demonstrates only
that the device survived the nominal case. The margin is declared and
the soak is held against the extreme plus that margin.

It also has to stop short of the package rating. A soak driven past what
the part is rated to store is not a service demonstration; it is a
destructive test wearing the same name, and a device that fails it has
told the project nothing about flight.

And both ends have to be covered. A programme that soaks hot and calls
the job done has not looked at the cold end at all, where the failure
mechanism is different: hot exposure drives diffusion and intermetallic
growth, cold exposure drives differential contraction between materials
that shrink at different rates.

What survival means is then arithmetic on the before and after readings.
A device is degraded when its forward drop has moved by more than the
declared share, or when its reverse leakage has grown by more than the
declared ratio. Leakage is graded as a ratio and not as a difference
because it spans decades: a change that is negligible on a leaky part is
a total failure on a tight one.

The bands below are declared project values, not physical constants: a
project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

EXPOSURE_PLAN_INVALID = "exposure-plan-invalid"
SERVICE_EXTREME_NOT_COVERED = "service-extreme-not-covered"
EXPOSURE_SAMPLE_BELOW_FLOOR = "exposure-sample-below-floor"
EXPOSED_DEVICES_DEGRADED = "exposed-devices-degraded"
ROBUSTNESS_DEMONSTRATED = "temperature-extreme-robustness-demonstrated"

HOT = "hot"
COLD = "cold"
EXTREMES = (COLD, HOT)

DEFAULT_EXPOSURE_POLICY = {
    "required_hot_margin_c": 10.0,
    "required_cold_margin_c": 10.0,
    "min_dwell_hours": 2.0,
    "max_ramp_rate_c_per_min": 5.0,
    "min_sample_size": 5,
    "max_forward_drift_fraction": 0.05,
    "max_leakage_growth_ratio": 3.0,
    "required_survivor_fraction": 1.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-15


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(name, value):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (name, value))
    return float(value)


def _require_positive(name, value):
    number = _require_number(name, value)
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_count(name, value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError("%s must be a whole number, got %r" % (name, value))
    if value < 1:
        raise ValueError("%s must be at least one, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    label = value.strip()
    if not label:
        raise ValueError("%s must not be blank" % name)
    return label


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_exposure_policy(policy):
    """Check the exposure policy is complete and sensible."""
    if not isinstance(policy, dict):
        raise ValueError("policy must be a mapping, got %r" % (policy,))
    for key in ("required_hot_margin_c", "required_cold_margin_c"):
        margin = _require_number(key, policy.get(key))
        if margin < 0.0:
            raise ValueError(
                "%s must not be negative; a soak inside the service extreme "
                "demonstrates less than the mission asks" % key
            )
    _require_positive("min_dwell_hours", policy.get("min_dwell_hours"))
    _require_positive(
        "max_ramp_rate_c_per_min", policy.get("max_ramp_rate_c_per_min")
    )
    _require_count("min_sample_size", policy.get("min_sample_size"))
    drift = _require_positive(
        "max_forward_drift_fraction", policy.get("max_forward_drift_fraction")
    )
    if drift >= 1.0:
        raise ValueError(
            "max_forward_drift_fraction %g admits a device whose forward drop "
            "vanished" % drift
        )
    growth = _require_number(
        "max_leakage_growth_ratio", policy.get("max_leakage_growth_ratio")
    )
    if growth < 1.0:
        raise ValueError(
            "max_leakage_growth_ratio %g demands the exposure improve the "
            "device, which is not a survival criterion" % growth
        )
    fraction = _require_positive(
        "required_survivor_fraction", policy.get("required_survivor_fraction")
    )
    if fraction > 1.0:
        raise ValueError(
            "required_survivor_fraction %g asks for more devices than were "
            "exposed" % fraction
        )
    return policy


def validate_service_range(service_range):
    """Read the coldest and hottest temperatures the mission predicts."""
    if not isinstance(service_range, dict):
        raise ValueError("service_range must be a mapping, got %r" % (service_range,))
    low = _require_number("service_range min_c", service_range.get("min_c"))
    high = _require_number("service_range max_c", service_range.get("max_c"))
    if not high > low:
        raise ValueError(
            "service range is inverted or empty: %g C floor against %g C "
            "ceiling" % (low, high)
        )
    return low, high


def validate_package_rating(rating):
    """Read the storage temperatures the part itself is rated between."""
    if not isinstance(rating, dict):
        raise ValueError("package_rating_c must be a mapping, got %r" % (rating,))
    low = _require_number("package_rating min_c", rating.get("min_c"))
    high = _require_number("package_rating max_c", rating.get("max_c"))
    if not high > low:
        raise ValueError(
            "package rating is inverted or empty: %g C floor against %g C "
            "ceiling" % (low, high)
        )
    return low, high


def required_soak_temperature_c(extreme, service_range, policy=DEFAULT_EXPOSURE_POLICY):
    """Temperature a soak has to reach past the service extreme."""
    validate_exposure_policy(policy)
    low, high = validate_service_range(service_range)
    if extreme == HOT:
        return high + float(policy["required_hot_margin_c"])
    if extreme == COLD:
        return low - float(policy["required_cold_margin_c"])
    raise ValueError(
        "extreme must be %r or %r, got %r" % (COLD, HOT, extreme)
    )


def soak_margin_c(extreme, soak_temperature_c, service_range):
    """How far past the service extreme the soak actually went."""
    low, high = validate_service_range(service_range)
    soak = _require_number("soak_temperature_c", soak_temperature_c)
    if extreme == HOT:
        return soak - high
    if extreme == COLD:
        return low - soak
    raise ValueError("extreme must be %r or %r, got %r" % (COLD, HOT, extreme))


def soak_reaches_extreme(
    extreme, soak_temperature_c, service_range, policy=DEFAULT_EXPOSURE_POLICY
):
    """True when the soak went past the service extreme by the declared margin."""
    validate_exposure_policy(policy)
    achieved = soak_margin_c(extreme, soak_temperature_c, service_range)
    required = (
        float(policy["required_hot_margin_c"])
        if extreme == HOT
        else float(policy["required_cold_margin_c"])
    )
    return _at_least(achieved, required)


def soak_within_package_rating(extreme, soak_temperature_c, package_rating_c):
    """True when the soak stayed inside what the part is rated to store."""
    low, high = validate_package_rating(package_rating_c)
    soak = _require_number("soak_temperature_c", soak_temperature_c)
    if extreme == HOT:
        return _at_most(soak, high)
    if extreme == COLD:
        return _at_least(soak, low)
    raise ValueError("extreme must be %r or %r, got %r" % (COLD, HOT, extreme))


def validate_exposure(exposure):
    """Read one soak: which end it sits at, how hot, how long, how fast."""
    if not isinstance(exposure, dict):
        raise ValueError("exposure must be a mapping, got %r" % (exposure,))
    extreme = _require_label("exposure extreme", exposure.get("extreme")).lower()
    if extreme not in EXTREMES:
        raise ValueError(
            "exposure extreme must be %r or %r, got %r" % (COLD, HOT, extreme)
        )
    soak = _require_number("soak_temperature_c", exposure.get("soak_temperature_c"))
    dwell = _require_positive("dwell_hours", exposure.get("dwell_hours"))
    ramp = _require_positive(
        "ramp_rate_c_per_min", exposure.get("ramp_rate_c_per_min")
    )
    return extreme, soak, dwell, ramp


def dwell_sufficient(dwell_hours, policy=DEFAULT_EXPOSURE_POLICY):
    """True when the device was held long enough to take up the strain."""
    validate_exposure_policy(policy)
    dwell = _require_positive("dwell_hours", dwell_hours)
    return _at_least(dwell, float(policy["min_dwell_hours"]))


def ramp_within_limit(ramp_rate_c_per_min, policy=DEFAULT_EXPOSURE_POLICY):
    """True when the transition was slow enough to be an exposure, not a shock."""
    validate_exposure_policy(policy)
    ramp = _require_positive("ramp_rate_c_per_min", ramp_rate_c_per_min)
    return _at_most(ramp, float(policy["max_ramp_rate_c_per_min"]))


def extremes_covered(exposures):
    """Which of the two service extremes the programme actually soaks at."""
    if not isinstance(exposures, (list, tuple)) or not exposures:
        raise ValueError("no exposure was planned, so nothing is demonstrated")
    covered = set()
    for exposure in exposures:
        extreme, _soak, _dwell, _ramp = validate_exposure(exposure)
        covered.add(extreme)
    return sorted(covered)


def missing_extremes(exposures):
    """The service extremes the programme never takes a device to."""
    covered = set(extremes_covered(exposures))
    return [extreme for extreme in EXTREMES if extreme not in covered]


def forward_drift_fraction(before_v, after_v):
    """Share of the pre-exposure forward drop the reading moved by."""
    before = _require_positive("forward_voltage_before_v", before_v)
    after = _require_positive("forward_voltage_after_v", after_v)
    return abs(after - before) / before


def leakage_growth_ratio(before_ua, after_ua):
    """How many times the reverse leakage the exposure multiplied."""
    before = _require_positive("reverse_leakage_before_ua", before_ua)
    after = _require_positive("reverse_leakage_after_ua", after_ua)
    return after / before


def validate_device_readings(device):
    """Read one exposed device's before and after electrical readings."""
    if not isinstance(device, dict):
        raise ValueError("device must be a mapping, got %r" % (device,))
    identifier = _require_label("device id", device.get("id"))
    before_v = _require_positive(
        "forward_voltage_before_v on %s" % identifier,
        device.get("forward_voltage_before_v"),
    )
    after_v = _require_positive(
        "forward_voltage_after_v on %s" % identifier,
        device.get("forward_voltage_after_v"),
    )
    before_ua = _require_positive(
        "reverse_leakage_before_ua on %s" % identifier,
        device.get("reverse_leakage_before_ua"),
    )
    after_ua = _require_positive(
        "reverse_leakage_after_ua on %s" % identifier,
        device.get("reverse_leakage_after_ua"),
    )
    return identifier, before_v, after_v, before_ua, after_ua


def grade_device(device, policy=DEFAULT_EXPOSURE_POLICY):
    """Decide whether one exposed device came through within its drift limits."""
    validate_exposure_policy(policy)
    identifier, before_v, after_v, before_ua, after_ua = validate_device_readings(
        device
    )
    drift = forward_drift_fraction(before_v, after_v)
    growth = leakage_growth_ratio(before_ua, after_ua)
    reasons = []
    if not _at_most(drift, float(policy["max_forward_drift_fraction"])):
        reasons.append(
            "forward drop moved by %.3g per cent of what it was" % (drift * 100.0)
        )
    if not _at_most(growth, float(policy["max_leakage_growth_ratio"])):
        reasons.append("reverse leakage grew %.3g times" % growth)
    return {
        "id": identifier,
        "forward_drift_fraction": drift,
        "leakage_growth_ratio": growth,
        "intact": not reasons,
        "reasons": reasons,
    }


def survivor_fraction(graded):
    """Share of the exposed devices that came through within their limits."""
    if not isinstance(graded, (list, tuple)) or not graded:
        raise ValueError("no device was graded, so there is no share to take")
    intact = sum(1 for entry in graded if entry["intact"])
    return intact / float(len(graded))


def assess_temperature_extreme_robustness(case, policy=DEFAULT_EXPOSURE_POLICY):
    """Full clause 12.6.10 run over one presented exposure programme."""
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    validate_exposure_policy(policy)

    findings = []
    exposure_records = []
    device_records = []
    result = {
        "exposures": exposure_records,
        "missing_extremes": [],
        "device_count": None,
        "devices": device_records,
        "survivor_fraction": None,
        "findings": findings,
    }

    service_range = case.get("service_range_c")
    if service_range is None:
        raise ValueError("case is missing the declared service range")
    validate_service_range(service_range)

    package_rating = case.get("package_rating_c")
    if package_rating is None:
        raise ValueError("case is missing the package storage rating")
    validate_package_rating(package_rating)

    exposures = case.get("exposures")
    absent = missing_extremes(exposures)
    result["missing_extremes"] = absent

    for exposure in exposures:
        extreme, soak, dwell, ramp = validate_exposure(exposure)
        record = {
            "extreme": extreme,
            "soak_temperature_c": soak,
            "dwell_hours": dwell,
            "ramp_rate_c_per_min": ramp,
            "achieved_margin_c": soak_margin_c(extreme, soak, service_range),
            "required_soak_temperature_c": required_soak_temperature_c(
                extreme, service_range, policy
            ),
        }
        exposure_records.append(record)

        if not soak_within_package_rating(extreme, soak, package_rating):
            findings.append(
                "the %s soak at %g C runs past the storage rating of the part, "
                "so it destroys rather than demonstrates" % (extreme, soak)
            )
        elif not soak_reaches_extreme(extreme, soak, service_range, policy):
            findings.append(
                "the %s soak at %g C clears the service extreme by only %g C, "
                "short of the declared margin, so only the nominal case is "
                "demonstrated" % (extreme, soak, record["achieved_margin_c"])
            )
        if not dwell_sufficient(dwell, policy):
            findings.append(
                "the %s soak was held %g hours, under the declared dwell, so "
                "the joints were never given time to take up the strain"
                % (extreme, dwell)
            )
        if not ramp_within_limit(ramp, policy):
            findings.append(
                "the %s transition ran at %g C per minute, above the declared "
                "rate, which turns an exposure into a shock test"
                % (extreme, ramp)
            )

    if findings:
        result["verdict"] = EXPOSURE_PLAN_INVALID
        return result

    if absent:
        findings.append(
            "no device was taken to the %s end of service, where the failure "
            "mechanism differs from the end that was covered"
            % " or ".join(absent)
        )
        result["verdict"] = SERVICE_EXTREME_NOT_COVERED
        return result

    devices = case.get("devices")
    if not isinstance(devices, (list, tuple)) or not devices:
        raise ValueError("no device was exposed, so there is nothing to read back")

    seen = set()
    for device in devices:
        graded = grade_device(device, policy)
        if graded["id"] in seen:
            raise ValueError("duplicate device id %r in the record" % graded["id"])
        seen.add(graded["id"])
        device_records.append(graded)

    result["device_count"] = len(device_records)
    result["survivor_fraction"] = survivor_fraction(device_records)

    if len(device_records) < int(policy["min_sample_size"]):
        findings.append(
            "%d device(s) were exposed against a floor of %d, so the result "
            "speaks for the pieces and not for the lot"
            % (len(device_records), int(policy["min_sample_size"]))
        )
        result["verdict"] = EXPOSURE_SAMPLE_BELOW_FLOOR
        return result

    if not _at_least(
        result["survivor_fraction"], float(policy["required_survivor_fraction"])
    ):
        for entry in device_records:
            if not entry["intact"]:
                findings.append(
                    "device %s came back degraded: %s"
                    % (entry["id"], "; ".join(entry["reasons"]))
                )
        result["verdict"] = EXPOSED_DEVICES_DEGRADED
        return result

    result["verdict"] = ROBUSTNESS_DEMONSTRATED
    return result
