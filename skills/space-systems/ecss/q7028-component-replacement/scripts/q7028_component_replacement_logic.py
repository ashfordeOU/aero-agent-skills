"""Component removal and replacement planning with thermal damage control.

Anchor: ECSS-Q-ST-70-28 Methods (removal and replacement of a component on a
printed board assembly, and the control of thermal damage to the board, the
replaced part and its neighbours). Paraphrased into an implementable
procedure; no standard text is reproduced.

Procedure implemented here
--------------------------
1. Validate the planned thermal profile, the site history and the neighbour
   list.
2. Read the profile for its peak temperature and for the time it spends above
   the damage threshold of the laminate, interpolating the crossings rather
   than counting whole sample intervals.
3. Project the peak onto every neighbouring component through a distance
   decay and compare with each neighbour's own limit, so a part that never
   sees the iron can still demand shielding.
4. Decide whether a moisture-sensitive replacement part owes a bake, from its
   sensitivity level and the floor time it has already accumulated.
5. Draw the work against the number of replacements the site may take, and
   return proceed, proceed-with-controls, or refuse.
"""

import math

__all__ = [
    "TEMPERATURE_TOLERANCE_C",
    "TIME_TOLERANCE_S",
    "MSL_FLOOR_LIFE_HOURS",
    "require_real",
    "require_count",
    "validate_thermal_profile",
    "peak_temperature_c",
    "time_above_c",
    "adjacent_exposure_c",
    "neighbours_over_limit",
    "floor_life_hours",
    "bake_required",
    "replacement_allowance",
    "assess_component_replacement",
]

TEMPERATURE_TOLERANCE_C = 1e-9
TIME_TOLERANCE_S = 1e-9

# Floor life a moisture-sensitive part may spend out of dry storage before it
# owes a bake. Level 1 parts are not floor-life limited.
MSL_FLOOR_LIFE_HOURS = {
    1: None,
    2: 8760.0,
    3: 168.0,
    4: 72.0,
    5: 48.0,
    6: 6.0,
}


def require_real(label, value, minimum=None, allow_equal=True):
    """Return value as a float, raising ValueError on anything unusable."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be a real number, got %r" % (label, value))
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if minimum is not None:
        if allow_equal and out < minimum:
            raise ValueError("%s must be at least %g, got %g" % (label, minimum, out))
        if not allow_equal and out <= minimum:
            raise ValueError("%s must exceed %g, got %g" % (label, minimum, out))
    return out


def require_count(label, value):
    """Return value as a non-negative integer count."""
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (label, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %d" % (label, value))
    return value


def validate_thermal_profile(profile):
    """Return a validated list of (time_s, temperature_c) samples."""
    if not isinstance(profile, (list, tuple)) or len(profile) < 2:
        raise ValueError("profile needs at least two (time_s, temperature_c) samples")
    points = []
    for i, item in enumerate(profile):
        if not isinstance(item, (list, tuple)) or len(item) != 2:
            raise ValueError("profile[%d] must be a (time_s, temperature_c) pair" % i)
        t = require_real("profile[%d] time_s" % i, item[0], minimum=0.0)
        temp = require_real("profile[%d] temperature_c" % i, item[1])
        points.append((t, temp))
    for i in range(1, len(points)):
        if points[i][0] <= points[i - 1][0]:
            raise ValueError("profile times must strictly increase (index %d)" % i)
    return points


def peak_temperature_c(profile):
    """Return the highest temperature the profile reaches."""
    points = validate_thermal_profile(profile)
    return max(temp for _, temp in points)


def time_above_c(profile, threshold_c):
    """Return the seconds the profile spends at or above a threshold."""
    points = validate_thermal_profile(profile)
    threshold = require_real("threshold_c", threshold_c)
    total = 0.0
    for i in range(1, len(points)):
        t0, temp0 = points[i - 1]
        t1, temp1 = points[i]
        span = t1 - t0
        above0 = temp0 >= threshold
        above1 = temp1 >= threshold
        if above0 and above1:
            total += span
        elif above0 or above1:
            fraction = (threshold - temp0) / (temp1 - temp0)
            total += span * (1.0 - fraction) if above1 else span * fraction
    return total


def adjacent_exposure_c(peak_c, ambient_c, distance_mm, decay_length_mm):
    """Project the peak temperature onto a neighbour at a given distance."""
    peak = require_real("peak_c", peak_c)
    ambient = require_real("ambient_c", ambient_c)
    distance = require_real("distance_mm", distance_mm, minimum=0.0)
    decay = require_real("decay_length_mm", decay_length_mm, minimum=0.0,
                         allow_equal=False)
    if peak < ambient:
        raise ValueError(
            "peak_c %g is below ambient_c %g; that is not a heating event"
            % (peak, ambient)
        )
    return ambient + (peak - ambient) * math.exp(-distance / decay)


def neighbours_over_limit(neighbours, peak_c, ambient_c, decay_length_mm):
    """Return the neighbour records whose projected exposure exceeds their limit."""
    if not isinstance(neighbours, (list, tuple)):
        raise ValueError("neighbours must be a sequence of mappings")
    exceeded = []
    for index, item in enumerate(neighbours):
        if not isinstance(item, dict):
            raise ValueError("neighbours[%d] must be a mapping" % index)
        for key in ("reference", "distance_mm", "max_temperature_c"):
            if key not in item:
                raise ValueError("neighbours[%d] missing key '%s'" % (index, key))
        exposure = adjacent_exposure_c(
            peak_c, ambient_c, item["distance_mm"], decay_length_mm
        )
        limit = require_real("neighbours[%d] max_temperature_c" % index,
                             item["max_temperature_c"])
        if exposure > limit + TEMPERATURE_TOLERANCE_C:
            exceeded.append({
                "reference": item["reference"],
                "distance_mm": float(item["distance_mm"]),
                "exposure_c": exposure,
                "max_temperature_c": limit,
            })
    return exceeded


def floor_life_hours(msl):
    """Return the floor life of a moisture sensitivity level, or None if unlimited."""
    if not isinstance(msl, int) or isinstance(msl, bool):
        raise ValueError("msl must be an integer level, got %r" % (msl,))
    if msl not in MSL_FLOOR_LIFE_HOURS:
        raise ValueError(
            "msl must be one of %s, got %d"
            % (", ".join(str(k) for k in sorted(MSL_FLOOR_LIFE_HOURS)), msl)
        )
    return MSL_FLOOR_LIFE_HOURS[msl]


def bake_required(msl, floor_hours, already_baked=False):
    """Decide whether the replacement part owes a bake before it is fitted."""
    limit = floor_life_hours(msl)
    used = require_real("floor_hours", floor_hours, minimum=0.0)
    if not isinstance(already_baked, bool):
        raise ValueError("already_baked must be a bool, got %r" % (already_baked,))
    if limit is None:
        return {
            "msl": msl,
            "floor_life_hours": None,
            "floor_hours": used,
            "bake_required": False,
            "reason": "level 1 parts are not floor-life limited",
        }
    over = used > limit + TIME_TOLERANCE_S
    return {
        "msl": msl,
        "floor_life_hours": limit,
        "floor_hours": used,
        "bake_required": over and not already_baked,
        "reason": ("floor time %g h exceeds the %g h life" % (used, limit)) if over
        else "floor time %g h is inside the %g h life" % (used, limit),
    }


def replacement_allowance(replacements_done, max_replacements):
    """Return the replacement budget state for one board site."""
    done = require_count("replacements_done", replacements_done)
    maximum = require_count("max_replacements", max_replacements)
    if maximum == 0:
        raise ValueError("max_replacements must be at least 1 for a workable site")
    remaining = maximum - done
    return {
        "replacements_done": done,
        "max_replacements": maximum,
        "remaining_after_this_one": remaining - 1,
        "exhausted": remaining <= 0,
        "last_allowed": remaining == 1,
    }


def assess_component_replacement(spec):
    """Plan one component replacement and report its thermal controls.

    spec keys: profile, ambient_c, laminate_max_temperature_c,
    damage_threshold_c, max_time_above_threshold_s, decay_length_mm,
    neighbours, replacements_done, max_replacements, msl, floor_hours,
    optional already_baked and min_preheat_c with preheat_c.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required_keys = (
        "profile", "ambient_c", "laminate_max_temperature_c", "damage_threshold_c",
        "max_time_above_threshold_s", "decay_length_mm", "neighbours",
        "replacements_done", "max_replacements", "msl", "floor_hours",
    )
    for key in required_keys:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)

    peak = peak_temperature_c(spec["profile"])
    dwell = time_above_c(spec["profile"], spec["damage_threshold_c"])
    laminate_limit = require_real("laminate_max_temperature_c",
                                  spec["laminate_max_temperature_c"])
    dwell_budget = require_real("max_time_above_threshold_s",
                                spec["max_time_above_threshold_s"], minimum=0.0)
    over_peak = peak > laminate_limit + TEMPERATURE_TOLERANCE_C
    over_dwell = dwell > dwell_budget + TIME_TOLERANCE_S

    exceeded = neighbours_over_limit(
        spec["neighbours"], peak, spec["ambient_c"], spec["decay_length_mm"]
    )
    bake = bake_required(spec["msl"], spec["floor_hours"],
                         spec.get("already_baked", False))
    allowance = replacement_allowance(spec["replacements_done"],
                                      spec["max_replacements"])

    preheat_short = False
    if "min_preheat_c" in spec:
        if "preheat_c" not in spec:
            raise ValueError("a min_preheat_c requires a preheat_c reading")
        preheat = require_real("preheat_c", spec["preheat_c"])
        min_preheat = require_real("min_preheat_c", spec["min_preheat_c"])
        preheat_short = preheat < min_preheat - TEMPERATURE_TOLERANCE_C

    findings = []
    if over_peak:
        findings.append(
            "profile peaks at %.1f C against the laminate limit of %.1f C"
            % (peak, laminate_limit)
        )
    if over_dwell:
        findings.append(
            "profile spends %.2f s above the damage threshold against a %.2f s budget"
            % (dwell, dwell_budget)
        )
    if allowance["exhausted"]:
        findings.append(
            "the site has already taken its %d permitted replacements"
            % allowance["max_replacements"]
        )
    for record in exceeded:
        findings.append(
            "neighbour %s at %.1f mm sees %.1f C against its %.1f C limit; shield it"
            % (record["reference"], record["distance_mm"], record["exposure_c"],
               record["max_temperature_c"])
        )
    if bake["bake_required"]:
        findings.append("replacement part owes a bake: %s" % bake["reason"])
    if preheat_short:
        findings.append("board preheat is below its minimum; raise it before removal")
    if allowance["last_allowed"]:
        findings.append("this replacement consumes the last of the site's allowance")

    refused = over_peak or over_dwell or allowance["exhausted"]
    if refused:
        verdict = "refuse"
    elif findings:
        verdict = "proceed-with-controls"
    else:
        verdict = "proceed"

    return {
        "peak_temperature_c": peak,
        "time_above_threshold_s": dwell,
        "laminate_max_temperature_c": laminate_limit,
        "max_time_above_threshold_s": dwell_budget,
        "neighbours_over_limit": exceeded,
        "bake": bake,
        "allowance": allowance,
        "preheat_below_minimum": preheat_short,
        "verdict": verdict,
        "findings": findings,
    }
