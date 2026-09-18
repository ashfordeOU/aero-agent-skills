#!/usr/bin/env python3
"""Discharge-pulse injection arrangement, ECSS-E-ST-20-07C clause 5.4.13.4.

Paraphrased procedure, no verbatim standard text. The clause covers the
arrangement used to apply injected discharge pulses to a unit that is powered
and operating while the pulses arrive. This module turns that arrangement into
a deterministic assessment:

  injection points    -> is each clamp placeable, and is it the right distance
                         from the unit connector to inject rather than couple
  amplitude ladder    -> does the unit get walked up to the required level in
                         steps, without overtesting past it
  pulse budget        -> how many pulses the arrangement calls for and how long
                         applying them takes at a lawful repetition interval
  repetition interval -> is it long enough for the generator to recharge and
                         the unit to settle between pulses
  monitoring          -> can the operator see an upset while it is happening

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

__all__ = [
    "COUPLINGS",
    "DEFAULT_CLAMP_MAX_DISTANCE_M",
    "DEFAULT_CLAMP_MIN_DISTANCE_M",
    "DEFAULT_MARGINAL_BAND",
    "DEFAULT_OVERTEST_ALLOWANCE",
    "DEFAULT_RECHARGE_GUARD",
    "DEFAULT_SAMPLES_PER_UPSET",
    "GROUP_ADEQUATE",
    "GROUP_INADEQUATE",
    "GROUP_MARGINAL",
    "MIN_LADDER_STEPS",
    "OPERATING_MODES",
    "POLARITIES",
    "assess_discharge_injection",
    "assess_injection_point",
    "assess_monitoring",
    "clamp_window",
    "governing_shortfall",
    "injection_duration_s",
    "max_monitor_interval_s",
    "min_repetition_interval_s",
    "normalize_injection_points",
    "total_pulse_count",
    "validate_injection_point",
    "validate_level_ladder",
]

# Distances, durations and levels are floats, so a placement or an interval
# that exactly meets its bound can land a few units in the last place short.
# These tolerances absorb that representation error and nothing else.
REL_TOL = 1e-12
ABS_TOL_M = 1e-9
ABS_TOL_S = 1e-12
ABS_TOL_KV = 1e-9

# Placement window for an injection clamp measured from the unit connector.
# Closer than the lower edge and the pulse couples into the connector shell
# instead of the conductors; further than the upper edge and the bundle's own
# attenuation and the return path take the injected current away.
DEFAULT_CLAMP_MIN_DISTANCE_M = 0.05
DEFAULT_CLAMP_MAX_DISTANCE_M = 0.30

# A placement inside the window but within this fraction of the window width
# of either edge is usable and carried as a limitation, because a harness
# moves between runs and the next setup lands on the other side.
DEFAULT_MARGINAL_BAND = 0.10

# The pulse interval has to clear the slower of the generator recharge and the
# unit settling, with this guard on top so neither is only just cleared.
DEFAULT_RECHARGE_GUARD = 1.2

# Samples the monitor must take across the shortest upset worth catching
# before the upset can be said to be observed rather than inferred.
DEFAULT_SAMPLES_PER_UPSET = 3.0

# Fraction by which the top of the ladder may exceed the required level.
DEFAULT_OVERTEST_ALLOWANCE = 0.10

# Fewer steps than this is a single hit at level, not a walk-up.
MIN_LADDER_STEPS = 3

POLARITIES = ("positive", "negative")

COUPLINGS = (
    "harness-injection-clamp",
    "capacitive-coupling-clamp",
    "structure-injection-stud",
)

OPERATING_MODES = ("nominal", "worst-case", "transfer", "safe")

GROUP_ADEQUATE = "adequate"
GROUP_MARGINAL = "marginal"
GROUP_INADEQUATE = "inadequate"


def _number(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s: field %r must be numeric, got %r" % (where, key, value))
    value = float(value)
    if math.isnan(value) or math.isinf(value):
        raise ValueError("%s: field %r must be finite, got %r" % (where, key, value))
    return value


def _positive(record, key, where):
    value = _number(record, key, where)
    if value <= 0.0:
        raise ValueError("%s: field %r must be positive, got %r" % (where, key, value))
    return value


def _non_negative(record, key, where):
    value = _number(record, key, where)
    if value < 0.0:
        raise ValueError("%s: field %r must not be negative, got %r" % (where, key, value))
    return value


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def _token(record, key, where, recognized):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, str):
        raise ValueError("%s: field %r must be a string, got %r" % (where, key, value))
    token = value.strip().lower()
    if token not in recognized:
        raise ValueError(
            "%s: unrecognized %s %r; recognized: %s"
            % (where, key, value, ", ".join(recognized))
        )
    return token


def _scalar(value, name):
    return _number({name: value}, name, "argument")


def _positive_scalar(value, name):
    return _positive({name: value}, name, "argument")


def _non_negative_scalar(value, name):
    return _non_negative({name: value}, name, "argument")


def at_least(value, bound, abs_tol=ABS_TOL_M):
    """True when value reaches bound, absorbing float representation error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=abs_tol)


def at_most(value, bound, abs_tol=ABS_TOL_M):
    """True when value stays at or under bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=abs_tol)


def clamp_window(plan=None):
    """Return the validated (min, max) clamp placement window in metres."""
    if plan is None:
        plan = {}
    if not isinstance(plan, dict):
        raise ValueError("clamp window: plan must be a mapping")
    low = plan.get("clamp_min_distance_m", DEFAULT_CLAMP_MIN_DISTANCE_M)
    high = plan.get("clamp_max_distance_m", DEFAULT_CLAMP_MAX_DISTANCE_M)
    low = _positive_scalar(low, "clamp_min_distance_m")
    high = _positive_scalar(high, "clamp_max_distance_m")
    if not high > low:
        raise ValueError(
            "clamp window: upper edge %g m must exceed the lower edge %g m" % (high, low)
        )
    return (low, high)


def validate_injection_point(point, index=0, window=None):
    """Validate one injection point and return it normalized.

    Required fields: name (str), coupling (recognized token), bundle_length_m
    (> 0), clamp_length_m (> 0), distance_to_connector_m (> 0).
    """
    where = "injection point %d" % index
    if not isinstance(point, dict):
        raise ValueError("%s: record must be a mapping" % where)
    name = point.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ValueError("%s: field 'name' must be a non-empty string" % where)
    name = name.strip()
    coupling = _token(point, "coupling", where, COUPLINGS)
    bundle = _positive(point, "bundle_length_m", where)
    clamp = _positive(point, "clamp_length_m", where)
    distance = _positive(point, "distance_to_connector_m", where)
    if window is None:
        window = clamp_window()
    needed = distance + clamp
    return {
        "name": name,
        "coupling": coupling,
        "bundle_length_m": bundle,
        "clamp_length_m": clamp,
        "distance_to_connector_m": distance,
        "bundle_needed_m": needed,
        "bundle_sufficient": at_least(bundle, needed),
    }


def normalize_injection_points(points, window=None):
    """Validate a list of injection points; reject an empty list or a repeat."""
    if not isinstance(points, (list, tuple)) or not points:
        raise ValueError("injection points: expected a non-empty sequence of records")
    if window is None:
        window = clamp_window()
    seen = set()
    normalized = []
    for index, point in enumerate(points):
        record = validate_injection_point(point, index, window)
        key = record["name"].lower()
        if key in seen:
            raise ValueError(
                "injection points: point %r declared twice" % record["name"]
            )
        seen.add(key)
        normalized.append(record)
    return normalized


def assess_injection_point(point, window=None, marginal_band=DEFAULT_MARGINAL_BAND):
    """Group one normalized point and return its placement record.

    The group is inadequate when the clamp cannot be placed on the bundle at
    all, or when its distance from the connector falls outside the window;
    marginal when it sits within the marginal band of either edge; adequate
    otherwise. The shortfall factor is how far outside the violated bound the
    placement is, expressed as a ratio at or above one.
    """
    if not isinstance(point, dict):
        raise ValueError("placement: point must be a normalized mapping")
    for key in ("name", "distance_to_connector_m", "bundle_length_m", "bundle_needed_m"):
        if key not in point:
            raise ValueError("placement: normalized point missing %r" % key)
    if window is None:
        window = clamp_window()
    band = _non_negative_scalar(marginal_band, "marginal_band")
    if band >= 0.5:
        raise ValueError("marginal_band must be below 0.5 of the window width")
    low, high = window
    distance = float(point["distance_to_connector_m"])
    width = high - low
    reasons = []
    shortfall = 1.0
    if not point["bundle_sufficient"]:
        reasons.append(
            "bundle of %.3f m cannot carry a clamp of %.3f m at %.3f m from the connector"
            % (point["bundle_length_m"], point["clamp_length_m"], distance)
        )
        shortfall = max(shortfall, float(point["bundle_needed_m"]) / point["bundle_length_m"])
        group = GROUP_INADEQUATE
    elif not at_least(distance, low):
        reasons.append(
            "clamp at %.3f m is nearer the connector than the %.3f m lower edge"
            % (distance, low)
        )
        shortfall = low / distance
        group = GROUP_INADEQUATE
    elif not at_most(distance, high):
        reasons.append(
            "clamp at %.3f m is further from the connector than the %.3f m upper edge"
            % (distance, high)
        )
        shortfall = distance / high
        group = GROUP_INADEQUATE
    elif at_most(distance, low + band * width) or at_least(distance, high - band * width):
        reasons.append(
            "clamp at %.3f m sits within the marginal band of the %.3f-%.3f m window"
            % (distance, low, high)
        )
        group = GROUP_MARGINAL
    else:
        group = GROUP_ADEQUATE
    record = dict(point)
    record.update(
        {
            "window_m": (low, high),
            "group": group,
            "shortfall_factor": shortfall,
            "reasons": reasons,
        }
    )
    return record


def validate_level_ladder(ladder, required_level_kv,
                          overtest_allowance=DEFAULT_OVERTEST_ALLOWANCE):
    """Validate the amplitude ladder against the required injection level.

    The ladder must be a strictly rising sequence of positive levels in kV. It
    reaches compliance when its top level attains the required level, and it
    overtests when the top exceeds the required level by more than the
    allowance.
    """
    if not isinstance(ladder, (list, tuple)) or len(ladder) < 2:
        raise ValueError("level ladder: expected at least two levels in kV")
    levels = []
    for index, value in enumerate(ladder):
        level = _positive({"level": value}, "level", "level ladder step %d" % index)
        levels.append(level)
    for index in range(1, len(levels)):
        if levels[index] <= levels[index - 1]:
            raise ValueError(
                "level ladder: levels must strictly rise (step %d is %g after %g)"
                % (index, levels[index], levels[index - 1])
            )
    required = _positive_scalar(required_level_kv, "required_level_kv")
    allowance = _non_negative_scalar(overtest_allowance, "overtest_allowance")
    top = levels[-1]
    reaches = at_least(top, required, abs_tol=ABS_TOL_KV)
    overtest_ratio = top / required
    overtests = not at_most(top, required * (1.0 + allowance), abs_tol=ABS_TOL_KV)
    return {
        "levels": levels,
        "steps": len(levels),
        "top_level_kv": top,
        "required_level_kv": required,
        "reaches_required": reaches,
        "overtest_ratio": overtest_ratio,
        "overtests": overtests,
        "stepped": len(levels) >= MIN_LADDER_STEPS,
    }


def min_repetition_interval_s(generator_recharge_s, eut_recovery_s,
                              guard=DEFAULT_RECHARGE_GUARD):
    """Return the shortest lawful interval between two injected pulses."""
    recharge = _positive_scalar(generator_recharge_s, "generator_recharge_s")
    recovery = _non_negative_scalar(eut_recovery_s, "eut_recovery_s")
    factor = _scalar(guard, "guard")
    if factor < 1.0:
        raise ValueError("guard must be at least 1.0, got %r" % (guard,))
    return factor * max(recharge, recovery)


def total_pulse_count(n_points, n_levels, pulses_per_polarity, n_polarities=2):
    """Return the number of pulses the arrangement calls for."""
    counts = {
        "n_points": n_points,
        "n_levels": n_levels,
        "pulses_per_polarity": pulses_per_polarity,
        "n_polarities": n_polarities,
    }
    for name, value in counts.items():
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("%s must be an integer, got %r" % (name, value))
        if value < 1:
            raise ValueError("%s must be at least 1, got %d" % (name, value))
    return n_points * n_levels * pulses_per_polarity * n_polarities


def injection_duration_s(total_pulses, repetition_interval_s, n_points,
                         per_point_setup_s=0.0):
    """Return the wall-clock duration of the injection sequence in seconds."""
    if isinstance(total_pulses, bool) or not isinstance(total_pulses, int):
        raise ValueError("total_pulses must be an integer, got %r" % (total_pulses,))
    if total_pulses < 1:
        raise ValueError("total_pulses must be at least 1, got %d" % total_pulses)
    if isinstance(n_points, bool) or not isinstance(n_points, int):
        raise ValueError("n_points must be an integer, got %r" % (n_points,))
    if n_points < 1:
        raise ValueError("n_points must be at least 1, got %d" % n_points)
    interval = _positive_scalar(repetition_interval_s, "repetition_interval_s")
    setup = _non_negative_scalar(per_point_setup_s, "per_point_setup_s")
    return total_pulses * interval + n_points * setup


def max_monitor_interval_s(shortest_upset_s, samples_per_upset=DEFAULT_SAMPLES_PER_UPSET):
    """Return the slowest monitor sampling interval that still sees an upset."""
    upset = _positive_scalar(shortest_upset_s, "shortest_upset_s")
    samples = _positive_scalar(samples_per_upset, "samples_per_upset")
    if samples < 2.0:
        raise ValueError("samples_per_upset must be at least 2, got %r" % (samples_per_upset,))
    return upset / samples


def assess_monitoring(monitoring, shortest_upset_s,
                      samples_per_upset=DEFAULT_SAMPLES_PER_UPSET):
    """Assess the unit monitoring that runs while the pulses are applied."""
    where = "monitoring"
    if not isinstance(monitoring, dict):
        raise ValueError("%s: record must be a mapping" % where)
    continuous = _flag(monitoring, "continuous", where)
    interval = _positive(monitoring, "sample_interval_s", where)
    records_index = _flag(monitoring, "records_pulse_index", where)
    allowed = max_monitor_interval_s(shortest_upset_s, samples_per_upset)
    fast_enough = at_most(interval, allowed, abs_tol=ABS_TOL_S)
    findings = []
    limitations = []
    if not continuous:
        findings.append(
            "unit monitoring is sampled between pulses, so an upset that clears "
            "before the next look is never seen"
        )
    if not fast_enough:
        findings.append(
            "monitor interval %.6g s is slower than the %.6g s needed to take "
            "%.3g looks at the shortest upset" % (interval, allowed, samples_per_upset)
        )
    if not records_index:
        limitations.append(
            "monitor does not record the pulse index, so an observed upset "
            "cannot be tied to the pulse that caused it"
        )
    return {
        "continuous": continuous,
        "sample_interval_s": interval,
        "max_interval_s": allowed,
        "fast_enough": fast_enough,
        "records_pulse_index": records_index,
        "findings": findings,
        "limitations": limitations,
    }


def governing_shortfall(records):
    """Return the inadequate placement short by the largest factor, or None."""
    if not isinstance(records, (list, tuple)):
        raise ValueError("governing shortfall: expected a sequence of records")
    worst = None
    for record in records:
        if not isinstance(record, dict) or "group" not in record:
            raise ValueError("governing shortfall: each record needs a 'group'")
        if record["group"] != GROUP_INADEQUATE:
            continue
        if worst is None or record["shortfall_factor"] > worst["shortfall_factor"]:
            worst = record
    return worst


def assess_discharge_injection(plan):
    """Assess a complete clause 5.4.13.4 discharge-injection arrangement.

    Required plan keys: injection_points, level_ladder, required_level_kv,
    pulses_per_polarity, repetition_interval_s, generator_recharge_s,
    eut_recovery_s, shortest_upset_s, monitoring, eut_powered,
    eut_operating_mode. Optional: polarities, per_point_setup_s,
    overtest_allowance, marginal_band, clamp_min_distance_m,
    clamp_max_distance_m, samples_per_upset.
    """
    where = "injection plan"
    if not isinstance(plan, dict):
        raise ValueError("%s: plan must be a mapping" % where)
    required_keys = (
        "injection_points",
        "level_ladder",
        "required_level_kv",
        "pulses_per_polarity",
        "repetition_interval_s",
        "generator_recharge_s",
        "eut_recovery_s",
        "shortest_upset_s",
        "monitoring",
        "eut_powered",
        "eut_operating_mode",
    )
    for key in required_keys:
        if key not in plan:
            raise ValueError("%s: missing required field %r" % (where, key))

    window = clamp_window(plan)
    band = plan.get("marginal_band", DEFAULT_MARGINAL_BAND)
    points = normalize_injection_points(plan["injection_points"], window)
    placements = [assess_injection_point(p, window, band) for p in points]

    ladder = validate_level_ladder(
        plan["level_ladder"],
        plan["required_level_kv"],
        plan.get("overtest_allowance", DEFAULT_OVERTEST_ALLOWANCE),
    )

    polarities = plan.get("polarities", POLARITIES)
    if not isinstance(polarities, (list, tuple)) or not polarities:
        raise ValueError("%s: polarities must be a non-empty sequence" % where)
    seen_polarity = []
    for index, value in enumerate(polarities):
        token = _token({"polarity": value}, "polarity", "%s polarity %d" % (where, index),
                       POLARITIES)
        if token in seen_polarity:
            raise ValueError("%s: polarity %r declared twice" % (where, token))
        seen_polarity.append(token)

    pulses_per_polarity = plan["pulses_per_polarity"]
    total = total_pulse_count(
        len(points), ladder["steps"], pulses_per_polarity, len(seen_polarity)
    )
    interval = _positive(plan, "repetition_interval_s", where)
    min_interval = min_repetition_interval_s(
        plan["generator_recharge_s"], plan["eut_recovery_s"]
    )
    interval_ok = at_least(interval, min_interval, abs_tol=ABS_TOL_S)
    duration = injection_duration_s(
        total, interval, len(points), plan.get("per_point_setup_s", 0.0)
    )

    monitoring = assess_monitoring(
        plan["monitoring"],
        plan["shortest_upset_s"],
        plan.get("samples_per_upset", DEFAULT_SAMPLES_PER_UPSET),
    )

    powered = _flag(plan, "eut_powered", where)
    mode = _token(plan, "eut_operating_mode", where, OPERATING_MODES)

    findings = []
    limitations = []
    if not powered:
        findings.append(
            "pulses are applied to an unpowered unit, which demonstrates nothing "
            "about how the unit behaves under injection"
        )
    if mode == "safe":
        limitations.append(
            "unit is held in its safe mode, so the functions most at risk are "
            "not exercised while the pulses arrive"
        )
    if not ladder["reaches_required"]:
        findings.append(
            "ladder tops out at %.3f kV, short of the required %.3f kV"
            % (ladder["top_level_kv"], ladder["required_level_kv"])
        )
    if ladder["overtests"]:
        findings.append(
            "ladder tops out at %.3f kV, %.1f%% above the required level"
            % (ladder["top_level_kv"], (ladder["overtest_ratio"] - 1.0) * 100.0)
        )
    if not ladder["stepped"]:
        findings.append(
            "ladder has %d levels, fewer than the %d needed to walk the unit up "
            "rather than hit it at level" % (ladder["steps"], MIN_LADDER_STEPS)
        )
    if not interval_ok:
        findings.append(
            "repetition interval %.6g s is shorter than the %.6g s the generator "
            "and the unit need between pulses" % (interval, min_interval)
        )
    for placement in placements:
        if placement["group"] == GROUP_INADEQUATE:
            findings.append("injection point %s: %s"
                            % (placement["name"], "; ".join(placement["reasons"])))
        elif placement["group"] == GROUP_MARGINAL:
            limitations.append("injection point %s: %s"
                               % (placement["name"], "; ".join(placement["reasons"])))
    findings.extend(monitoring["findings"])
    limitations.extend(monitoring["limitations"])

    return {
        "placements": placements,
        "ladder": ladder,
        "polarities": seen_polarity,
        "total_pulses": total,
        "repetition_interval_s": interval,
        "min_repetition_interval_s": min_interval,
        "repetition_interval_adequate": interval_ok,
        "injection_duration_s": duration,
        "monitoring": monitoring,
        "eut_powered": powered,
        "eut_operating_mode": mode,
        "governing_shortfall": governing_shortfall(placements),
        "findings": findings,
        "limitations": limitations,
        "arrangement_acceptable": not findings,
    }
