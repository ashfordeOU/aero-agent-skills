#!/usr/bin/env python3
"""Pulsed-drive substitution logic for multipaction verification.

Anchor: ECSS-E-ST-20-01C clause 6.4.4 -- the conditions under which a
pulsed drive may stand in for a continuous-wave drive when verifying
equipment that operates continuously. The clause is paraphrased into an
implementable procedure; no verbatim standard text is reproduced here.

Engineering model
-----------------
A pulsed drive is attractive because the bench only has to deliver the
peak for a small fraction of the time, but a multipaction discharge is
not instantaneous: a seed electron has to cross the gap, liberate
secondaries, and repeat until the population is large enough to be
observable. Roughly twenty transits of the gap are needed, so the pulse
has to be long enough to contain them:

    transit_time = resonant_order / (2 * frequency)
    crossings_per_pulse = pulse_width / transit_time

A pulse shorter than that extinguishes the avalanche before it grows,
and the article passes a run that never stressed it.

Two further conditions ride on the duty cycle rather than the pulse
width. The detection chain integrates over the accumulated on-time in
the observation window, so a very low duty cycle starves the detector
even when each individual pulse is long enough. And the average
dissipation of a pulsed drive is the peak scaled by the duty cycle, so
a low-duty run never reaches the steady-state temperature the equipment
sits at in continuous-wave operation -- and surface temperature drives
both outgassing and the secondary-emission condition that sets the
multipaction threshold. That thermal gap has to be closed by a separate
measure, not assumed away.

Only the python3 standard library is used; every function is offline
and deterministic.
"""

import math

__all__ = [
    "MIN_GAP_CROSSINGS",
    "DEFAULT_MIN_THERMAL_DUTY",
    "THERMAL_COMPENSATIONS",
    "OPERATIONAL_MODES",
    "REL_TOL",
    "validate_operational_mode",
    "validate_thermal_compensation",
    "pulse_repetition_period_s",
    "duty_cycle",
    "validate_pulse_profile",
    "electron_transit_time_s",
    "gap_crossings_per_pulse",
    "rf_cycles_per_pulse",
    "minimum_pulse_width_s",
    "pulses_in_window",
    "accumulated_on_time_s",
    "pulsed_average_power_w",
    "required_peak_drive_w",
    "assess_pulsed_substitution",
    "categorize_pulsed_substitution",
    "summarize_report",
]

# Electron avalanche growth needs roughly twenty transits of the gap
# inside a single pulse before a discharge is observable.
MIN_GAP_CROSSINGS = 20

# Below this duty cycle a pulsed run cannot be treated as reaching the
# continuous-wave steady-state temperature on its own.
DEFAULT_MIN_THERMAL_DUTY = 0.8

# Measures that close the thermal gap a low-duty pulsed run leaves open.
THERMAL_COMPENSATIONS = (
    "none",
    "baseplate-preheat",
    "auxiliary-continuous-wave-soak",
    "separate-thermal-vacuum-run",
)

OPERATIONAL_MODES = ("continuous-wave", "pulsed")

REL_TOL = 1e-9

_MAX_RESONANT_ORDER = 21


def _is_finite_number(value):
    if isinstance(value, bool):
        return False
    if not isinstance(value, (int, float)):
        return False
    return math.isfinite(float(value))


def _not_below(value, limit, rel_tol=REL_TOL):
    """value >= limit, absorbing representation error at the boundary.

    A pulse width derived as twenty transit times divides back to
    twenty crossings only to within a few units in the last place; that
    is arithmetic, not a shortfall, so it is absorbed here rather than
    by lowering the crossing minimum.
    """
    if value >= limit:
        return True
    return math.isclose(value, limit, rel_tol=rel_tol, abs_tol=0.0)


def validate_operational_mode(mode):
    """Check the equipment's flight operating mode token."""
    if not isinstance(mode, str) or mode.strip() not in OPERATIONAL_MODES:
        raise ValueError(
            "operational_mode must be one of %s" % (", ".join(OPERATIONAL_MODES),)
        )
    return mode.strip()


def validate_thermal_compensation(compensation):
    """Check the declared measure that closes the thermal gap."""
    if not isinstance(compensation, str) or compensation.strip() not in THERMAL_COMPENSATIONS:
        raise ValueError(
            "thermal_compensation must be one of %s" % (", ".join(THERMAL_COMPENSATIONS),)
        )
    return compensation.strip()


def pulse_repetition_period_s(prf_hz):
    """Interval between successive pulse starts, in seconds."""
    if not _is_finite_number(prf_hz) or float(prf_hz) <= 0.0:
        raise ValueError("prf_hz must be a finite positive repetition frequency")
    return 1.0 / float(prf_hz)


def duty_cycle(pulse_width_s, prf_hz):
    """Fraction of the repetition period during which the drive is on."""
    if not _is_finite_number(pulse_width_s) or float(pulse_width_s) <= 0.0:
        raise ValueError("pulse_width_s must be a finite positive duration")
    period = pulse_repetition_period_s(prf_hz)
    ratio = float(pulse_width_s) / period
    if ratio >= 1.0:
        raise ValueError(
            "pulse_width_s %g s does not fit inside the repetition period %g s"
            % (float(pulse_width_s), period)
        )
    return ratio


def validate_pulse_profile(pulse_width_s, prf_hz):
    """Normalize a pulse profile into width, period and duty cycle."""
    ratio = duty_cycle(pulse_width_s, prf_hz)
    return {
        "pulse_width_s": float(pulse_width_s),
        "prf_hz": float(prf_hz),
        "period_s": pulse_repetition_period_s(prf_hz),
        "duty_cycle": ratio,
    }


def electron_transit_time_s(frequency_hz, resonant_order=1):
    """Time for one electron transit of the gap at a resonant order."""
    if not _is_finite_number(frequency_hz) or float(frequency_hz) <= 0.0:
        raise ValueError("frequency_hz must be a finite positive frequency")
    if isinstance(resonant_order, bool) or not isinstance(resonant_order, int):
        raise ValueError("resonant_order must be an odd positive integer")
    if resonant_order < 1 or resonant_order > _MAX_RESONANT_ORDER:
        raise ValueError("resonant_order must lie between 1 and %d" % _MAX_RESONANT_ORDER)
    if resonant_order % 2 == 0:
        raise ValueError("resonant_order must be odd (even orders are not resonant)")
    return float(resonant_order) / (2.0 * float(frequency_hz))


def gap_crossings_per_pulse(pulse_width_s, frequency_hz, resonant_order=1):
    """Gap transits contained in one pulse."""
    if not _is_finite_number(pulse_width_s) or float(pulse_width_s) <= 0.0:
        raise ValueError("pulse_width_s must be a finite positive duration")
    return float(pulse_width_s) / electron_transit_time_s(frequency_hz, resonant_order)


def rf_cycles_per_pulse(pulse_width_s, frequency_hz):
    """RF periods contained in one pulse (reported, not gated).

    At resonant order n the crossing criterion already implies 10*n RF
    periods, so this quantity is carried for readability of the report
    rather than as an independent condition.
    """
    if not _is_finite_number(pulse_width_s) or float(pulse_width_s) <= 0.0:
        raise ValueError("pulse_width_s must be a finite positive duration")
    if not _is_finite_number(frequency_hz) or float(frequency_hz) <= 0.0:
        raise ValueError("frequency_hz must be a finite positive frequency")
    return float(pulse_width_s) * float(frequency_hz)


def minimum_pulse_width_s(frequency_hz, resonant_order=1, min_crossings=MIN_GAP_CROSSINGS):
    """Shortest pulse that still contains the avalanche-growth transits."""
    if not _is_finite_number(min_crossings) or float(min_crossings) <= 0.0:
        raise ValueError("min_crossings must be a finite positive count")
    return float(min_crossings) * electron_transit_time_s(frequency_hz, resonant_order)


def pulses_in_window(prf_hz, observation_s):
    """Whole pulses delivered inside an observation window.

    A window that is an exact whole number of repetition periods can
    evaluate a few units in the last place below that integer, so the
    count is nudged up when the product is indistinguishable from the
    next integer. The window itself is never lengthened.
    """
    if not _is_finite_number(prf_hz) or float(prf_hz) <= 0.0:
        raise ValueError("prf_hz must be a finite positive repetition frequency")
    if not _is_finite_number(observation_s) or float(observation_s) <= 0.0:
        raise ValueError("observation_s must be a finite positive duration")
    product = float(observation_s) * float(prf_hz)
    count = math.floor(product)
    if math.isclose(count + 1.0, product, rel_tol=REL_TOL, abs_tol=0.0):
        count += 1
    return int(count)


def accumulated_on_time_s(pulse_width_s, prf_hz, observation_s):
    """Total time the drive is on inside an observation window."""
    profile = validate_pulse_profile(pulse_width_s, prf_hz)
    return pulses_in_window(prf_hz, observation_s) * profile["pulse_width_s"]


def pulsed_average_power_w(peak_power_w, duty):
    """Average power a pulsed drive deposits in the article."""
    if not _is_finite_number(peak_power_w) or float(peak_power_w) <= 0.0:
        raise ValueError("peak_power_w must be a finite positive power in watts")
    if not _is_finite_number(duty) or not 0.0 < float(duty) < 1.0:
        raise ValueError("duty must lie strictly between 0 and 1")
    return float(peak_power_w) * float(duty)


def required_peak_drive_w(continuous_wave_power_w, margin_db):
    """Pulse peak that reproduces the operational level plus its margin."""
    if (
        not _is_finite_number(continuous_wave_power_w)
        or float(continuous_wave_power_w) <= 0.0
    ):
        raise ValueError("continuous_wave_power_w must be a finite positive power")
    if not _is_finite_number(margin_db) or float(margin_db) < 0.0:
        raise ValueError("margin_db must be a finite non-negative decibel value")
    return float(continuous_wave_power_w) * (10.0 ** (float(margin_db) / 10.0))


def assess_pulsed_substitution(
    frequency_hz,
    pulse_width_s,
    prf_hz,
    continuous_wave_power_w,
    peak_power_w,
    observation_s,
    margin_db=6.0,
    resonant_order=1,
    operational_mode="continuous-wave",
    thermal_compensation="none",
    min_accumulated_on_time_s=None,
    min_thermal_duty=DEFAULT_MIN_THERMAL_DUTY,
):
    """Full clause 6.4.4 assessment of a pulsed-drive substitution.

    Returns a report mapping with the pulse profile, the avalanche
    growth margin the pulse provides, the detection integration it
    accumulates, the thermal gap it leaves open, and every finding that
    blocks the substitution.
    """
    mode = validate_operational_mode(operational_mode)
    compensation = validate_thermal_compensation(thermal_compensation)
    profile = validate_pulse_profile(pulse_width_s, prf_hz)
    if not _is_finite_number(min_thermal_duty) or not 0.0 < float(min_thermal_duty) <= 1.0:
        raise ValueError("min_thermal_duty must lie in the interval (0, 1]")
    if min_accumulated_on_time_s is not None:
        if (
            not _is_finite_number(min_accumulated_on_time_s)
            or float(min_accumulated_on_time_s) <= 0.0
        ):
            raise ValueError("min_accumulated_on_time_s must be a finite positive duration")

    transit_s = electron_transit_time_s(frequency_hz, resonant_order)
    crossings = profile["pulse_width_s"] / transit_s
    shortest_pulse_s = minimum_pulse_width_s(frequency_hz, resonant_order)
    cycles = rf_cycles_per_pulse(profile["pulse_width_s"], frequency_hz)
    pulse_count = pulses_in_window(prf_hz, observation_s)
    on_time_s = pulse_count * profile["pulse_width_s"]
    required_peak_w = required_peak_drive_w(continuous_wave_power_w, margin_db)
    average_w = pulsed_average_power_w(peak_power_w, profile["duty_cycle"])

    findings = []
    if mode == "pulsed":
        findings.append(
            {
                "code": "equipment-does-not-operate-continuously",
                "detail": "clause 6.4.4 governs a stand-in for continuous-wave operation",
            }
        )
    if not _not_below(crossings, float(MIN_GAP_CROSSINGS)):
        findings.append(
            {
                "code": "pulse-too-short-for-avalanche-growth",
                "detail": "the pulse ends before the electron population can grow",
                "value": crossings,
                "limit": float(MIN_GAP_CROSSINGS),
            }
        )
    if not _not_below(float(peak_power_w), required_peak_w):
        findings.append(
            {
                "code": "pulse-peak-below-required-drive-level",
                "detail": "the pulse peak does not reach the operational level plus margin",
                "value": float(peak_power_w),
                "limit": required_peak_w,
            }
        )
    if min_accumulated_on_time_s is not None and not _not_below(
        on_time_s, float(min_accumulated_on_time_s)
    ):
        findings.append(
            {
                "code": "accumulated-on-time-below-detection-threshold",
                "detail": "the detection chain does not integrate enough on-time",
                "value": on_time_s,
                "limit": float(min_accumulated_on_time_s),
            }
        )
    thermally_representative = _not_below(profile["duty_cycle"], float(min_thermal_duty))
    if not thermally_representative and compensation == "none":
        findings.append(
            {
                "code": "continuous-wave-thermal-state-not-reproduced",
                "detail": "low duty cycle with no compensating measure on record",
                "value": profile["duty_cycle"],
                "limit": float(min_thermal_duty),
            }
        )

    report = {
        "operational_mode": mode,
        "frequency_hz": float(frequency_hz),
        "resonant_order": resonant_order,
        "pulse_width_s": profile["pulse_width_s"],
        "prf_hz": profile["prf_hz"],
        "period_s": profile["period_s"],
        "duty_cycle": profile["duty_cycle"],
        "electron_transit_time_s": transit_s,
        "gap_crossings_per_pulse": crossings,
        "shortest_admissible_pulse_s": shortest_pulse_s,
        "rf_cycles_per_pulse": cycles,
        "pulses_in_window": pulse_count,
        "accumulated_on_time_s": on_time_s,
        "required_peak_drive_w": required_peak_w,
        "peak_power_w": float(peak_power_w),
        "pulsed_average_power_w": average_w,
        "continuous_wave_power_w": float(continuous_wave_power_w),
        "thermal_compensation": compensation,
        "thermally_representative": thermally_representative,
        "findings": findings,
        "compliant": len(findings) == 0,
    }
    report["verdict"] = categorize_pulsed_substitution(report)
    return report


def categorize_pulsed_substitution(report):
    """Categorize a report into an acceptance outcome token."""
    if not isinstance(report, dict) or "findings" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    codes = {finding["code"] for finding in report["findings"]}
    if "equipment-does-not-operate-continuously" in codes:
        return "pulsed-drive-substitution-out-of-scope"
    if not codes:
        if report.get("thermal_compensation", "none") == "none":
            return "pulsed-drive-substitution-acceptable"
        return "pulsed-drive-substitution-acceptable-with-compensation"
    return "pulsed-drive-substitution-not-acceptable"


def summarize_report(report):
    """Render a report as deterministic plain text lines."""
    if not isinstance(report, dict) or "verdict" not in report:
        raise ValueError("report must be a mapping produced by the assessment function")
    lines = [
        "pulse width: %.6g s" % report["pulse_width_s"],
        "duty cycle: %.6g" % report["duty_cycle"],
        "crossings per pulse: %.6g" % report["gap_crossings_per_pulse"],
        "accumulated on-time: %.6g s" % report["accumulated_on_time_s"],
        "thermal compensation: %s" % report["thermal_compensation"],
        "verdict: %s" % report["verdict"],
    ]
    for finding in report["findings"]:
        lines.append("finding: %s" % finding["code"])
    return "\n".join(lines)
