"""Offgassing exposure conditions: set point, dwell and environment.

Anchor: ECSS-Q-ST-70-29 procedure step -- setting the exposure of a test
specimen, namely the temperature it is held at, the time it is held there and
the environment (evacuated or dry-nitrogen purged) surrounding it, and then
grading a recorded profile against that specification. Paraphrased into an
implementable procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the set point: temperature, tolerance band and required dwell.
2. Validate the environment: an evacuated vessel against a pressure ceiling,
   or a nitrogen purge against a flow and a purity floor.
3. Validate the recorded temperature profile.
4. Locate thermal stabilisation as the first sample inside the band.
5. Accumulate effective dwell only over intervals whose both endpoints are
   inside the band, so a dip is charged in full.
6. Group out-of-band intervals into excursions with direction, duration and
   peak deviation.
7. Decide acceptance of the run and report every finding.
"""

import math

__all__ = [
    "ABSOLUTE_ZERO_C",
    "TIME_TOLERANCE_H",
    "TEMP_TOLERANCE_C",
    "ENV_VACUUM",
    "ENV_NITROGEN",
    "ENVIRONMENTS",
    "DIRECTION_COLD",
    "DIRECTION_HOT",
    "VERDICT_ACCEPTED",
    "VERDICT_REJECTED",
    "validate_setpoint",
    "validate_environment",
    "validate_profile",
    "stabilisation_index",
    "in_band",
    "accumulate_dwell",
    "group_excursions",
    "evaluate_exposure",
]

ABSOLUTE_ZERO_C = -273.15

# The dwell is a sum of interval widths and can land a few ULP either side of
# the required value. Absorb the representation error here rather than by
# shortening the requirement.
TIME_TOLERANCE_H = 1e-9
TEMP_TOLERANCE_C = 1e-9

ENV_VACUUM = "vacuum"
ENV_NITROGEN = "nitrogen"
ENVIRONMENTS = (ENV_VACUUM, ENV_NITROGEN)

DIRECTION_COLD = "below-band"
DIRECTION_HOT = "above-band"

VERDICT_ACCEPTED = "accepted"
VERDICT_REJECTED = "rejected"


def _real(label, value):
    """Return value as a finite float or raise ValueError."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    v = float(value)
    if not math.isfinite(v):
        raise ValueError("%s must be finite, got %r" % (label, value))
    return v


def _positive(label, value):
    v = _real(label, value)
    if v <= 0.0:
        raise ValueError("%s must be positive, got %r" % (label, value))
    return v


def _temperature_c(label, value):
    v = _real(label, value)
    if v <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must be above absolute zero (%g C), got %r"
            % (label, ABSOLUTE_ZERO_C, value)
        )
    return v


def validate_setpoint(temperature_c, tolerance_c, dwell_h):
    """Return the validated exposure set point of the conditioning run."""
    return {
        "temperature_c": _temperature_c("temperature_c", temperature_c),
        "tolerance_c": _positive("tolerance_c", tolerance_c),
        "dwell_h": _positive("dwell_h", dwell_h),
    }


def validate_environment(environment, pressure_pa=None, pressure_ceiling_pa=None,
                         purge_flow_l_per_min=None, min_flow_l_per_min=None,
                         purity_fraction=None, min_purity_fraction=None):
    """Return the validated surrounding environment and its conformance.

    An evacuated run is graded against a pressure ceiling; a purged run is
    graded against a flow floor and a purity floor. A missing or unreal field
    is an input error; a value outside its limit is a finding, not an error.
    """
    if environment not in ENVIRONMENTS:
        raise ValueError(
            "environment must be one of %s, got %r" % (", ".join(ENVIRONMENTS), environment)
        )
    findings = []
    record = {"environment": environment, "conforming": True, "findings": findings}
    if environment == ENV_VACUUM:
        if pressure_pa is None or pressure_ceiling_pa is None:
            raise ValueError(
                "an evacuated run needs pressure_pa and pressure_ceiling_pa"
            )
        pressure = _positive("pressure_pa", pressure_pa)
        ceiling = _positive("pressure_ceiling_pa", pressure_ceiling_pa)
        record["pressure_pa"] = pressure
        record["pressure_ceiling_pa"] = ceiling
        if pressure > ceiling * (1.0 + 1e-12):
            findings.append(
                "vessel pressure %g Pa is above the ceiling %g Pa" % (pressure, ceiling)
            )
            record["conforming"] = False
    else:
        if purge_flow_l_per_min is None or min_flow_l_per_min is None:
            raise ValueError(
                "a purged run needs purge_flow_l_per_min and min_flow_l_per_min"
            )
        if purity_fraction is None or min_purity_fraction is None:
            raise ValueError(
                "a purged run needs purity_fraction and min_purity_fraction"
            )
        flow = _positive("purge_flow_l_per_min", purge_flow_l_per_min)
        min_flow = _positive("min_flow_l_per_min", min_flow_l_per_min)
        purity = _real("purity_fraction", purity_fraction)
        min_purity = _real("min_purity_fraction", min_purity_fraction)
        if purity <= 0.0 or purity > 1.0:
            raise ValueError(
                "purity_fraction must lie in (0, 1], got %r" % (purity_fraction,)
            )
        if min_purity <= 0.0 or min_purity > 1.0:
            raise ValueError(
                "min_purity_fraction must lie in (0, 1], got %r" % (min_purity_fraction,)
            )
        record["purge_flow_l_per_min"] = flow
        record["min_flow_l_per_min"] = min_flow
        record["purity_fraction"] = purity
        record["min_purity_fraction"] = min_purity
        if flow < min_flow * (1.0 - 1e-12):
            findings.append(
                "purge flow %g l/min is below the required %g l/min" % (flow, min_flow)
            )
            record["conforming"] = False
        if purity < min_purity * (1.0 - 1e-12):
            findings.append(
                "purge purity %g is below the required %g" % (purity, min_purity)
            )
            record["conforming"] = False
    return record


def validate_profile(samples):
    """Return the recorded profile as (time_h, temperature_c) pairs."""
    if not isinstance(samples, (list, tuple)) or len(samples) < 2:
        raise ValueError("profile needs at least two (time_h, temperature_c) samples")
    out = []
    for i, item in enumerate(samples):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("profile[%d] must be a (time_h, temperature_c) pair" % i)
        t = _real("profile[%d] time_h" % i, item[0])
        if t < 0.0:
            raise ValueError("profile[%d] time_h must not be negative" % i)
        temp = _temperature_c("profile[%d] temperature_c" % i, item[1])
        out.append((t, temp))
    for i in range(1, len(out)):
        if out[i][0] <= out[i - 1][0]:
            raise ValueError("profile times must strictly increase (index %d)" % i)
    return out


def in_band(temperature_c, setpoint):
    """Return True when a sample sits inside the tolerance band."""
    temp = _temperature_c("temperature_c", temperature_c)
    deviation = abs(temp - setpoint["temperature_c"])
    return deviation <= setpoint["tolerance_c"] + TEMP_TOLERANCE_C


def stabilisation_index(profile, setpoint):
    """Return the index of the first in-band sample, or None if never reached."""
    for i, (_, temp) in enumerate(profile):
        if in_band(temp, setpoint):
            return i
    return None


def accumulate_dwell(profile, setpoint, start_index):
    """Return effective in-band hours and the out-of-band intervals after start.

    An interval is credited only when both endpoints are inside the band, so a
    dip between two samples is charged in full rather than interpolated away.
    """
    if not isinstance(start_index, int) or isinstance(start_index, bool):
        raise ValueError("start_index must be an int, got %r" % (start_index,))
    if start_index < 0 or start_index >= len(profile) - 1:
        raise ValueError(
            "start_index %r is outside the usable profile range" % (start_index,)
        )
    effective = 0.0
    out_of_band = []
    for i in range(start_index, len(profile) - 1):
        t0, temp0 = profile[i]
        t1, temp1 = profile[i + 1]
        width = t1 - t0
        if in_band(temp0, setpoint) and in_band(temp1, setpoint):
            effective += width
        else:
            out_of_band.append((i, t0, t1, temp0, temp1))
    return effective, out_of_band


def group_excursions(out_of_band, setpoint):
    """Group contiguous out-of-band intervals into excursion records."""
    excursions = []
    current = None
    previous_index = None
    for index, t0, t1, temp0, temp1 in out_of_band:
        worst = temp0 if abs(temp0 - setpoint["temperature_c"]) >= abs(
            temp1 - setpoint["temperature_c"]
        ) else temp1
        deviation = worst - setpoint["temperature_c"]
        if current is None or previous_index is None or index != previous_index + 1:
            current = {
                "start_h": t0,
                "end_h": t1,
                "duration_h": t1 - t0,
                "peak_temperature_c": worst,
                "peak_deviation_c": deviation,
            }
            excursions.append(current)
        else:
            current["end_h"] = t1
            current["duration_h"] = current["end_h"] - current["start_h"]
            if abs(deviation) > abs(current["peak_deviation_c"]):
                current["peak_temperature_c"] = worst
                current["peak_deviation_c"] = deviation
        previous_index = index
    for record in excursions:
        record["direction"] = (
            DIRECTION_HOT if record["peak_deviation_c"] > 0.0 else DIRECTION_COLD
        )
    return excursions


def evaluate_exposure(spec):
    """Specify and grade one offgassing exposure run.

    spec keys: temperature_c, tolerance_c, dwell_h, profile, environment, and
    the environment-specific limit fields consumed by validate_environment.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    for key in ("temperature_c", "tolerance_c", "dwell_h", "profile", "environment"):
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    setpoint = validate_setpoint(
        spec["temperature_c"], spec["tolerance_c"], spec["dwell_h"]
    )
    environment = validate_environment(
        spec["environment"],
        pressure_pa=spec.get("pressure_pa"),
        pressure_ceiling_pa=spec.get("pressure_ceiling_pa"),
        purge_flow_l_per_min=spec.get("purge_flow_l_per_min"),
        min_flow_l_per_min=spec.get("min_flow_l_per_min"),
        purity_fraction=spec.get("purity_fraction"),
        min_purity_fraction=spec.get("min_purity_fraction"),
    )
    profile = validate_profile(spec["profile"])
    findings = list(environment["findings"])
    start = stabilisation_index(profile, setpoint)
    result = {
        "setpoint": setpoint,
        "environment": environment,
        "stabilisation_h": None,
        "effective_dwell_h": 0.0,
        "dwell_shortfall_h": setpoint["dwell_h"],
        "excursions": [],
        "excursion_count": 0,
        "longest_excursion_h": 0.0,
        "hot_excursion_count": 0,
        "verdict": VERDICT_REJECTED,
        "findings": findings,
    }
    if start is None:
        findings.append("the profile never entered the tolerance band; no dwell credited")
        return result
    if start >= len(profile) - 1:
        findings.append(
            "the band was first reached at the last sample; no dwell interval follows"
        )
        result["stabilisation_h"] = profile[start][0]
        return result
    result["stabilisation_h"] = profile[start][0]
    effective, out_of_band = accumulate_dwell(profile, setpoint, start)
    excursions = group_excursions(out_of_band, setpoint)
    result["effective_dwell_h"] = effective
    result["excursions"] = excursions
    result["excursion_count"] = len(excursions)
    result["longest_excursion_h"] = max(
        (e["duration_h"] for e in excursions), default=0.0
    )
    result["hot_excursion_count"] = sum(
        1 for e in excursions if e["direction"] == DIRECTION_HOT
    )
    shortfall = setpoint["dwell_h"] - effective
    result["dwell_shortfall_h"] = shortfall if shortfall > TIME_TOLERANCE_H else 0.0
    if shortfall > TIME_TOLERANCE_H:
        findings.append(
            "effective in-band dwell %g h is short of the required %g h"
            % (effective, setpoint["dwell_h"])
        )
    if result["hot_excursion_count"]:
        findings.append(
            "%d excursion(s) above the band; over temperature can change what the "
            "specimen releases" % result["hot_excursion_count"]
        )
    total_span = profile[-1][0] - profile[0][0]
    if total_span > 0.0 and result["stabilisation_h"] - profile[0][0] > 0.5 * total_span:
        findings.append(
            "thermal stabilisation consumed more than half of the recorded run"
        )
    if (
        environment["conforming"]
        and result["dwell_shortfall_h"] == 0.0
        and result["hot_excursion_count"] == 0
    ):
        result["verdict"] = VERDICT_ACCEPTED
    return result
