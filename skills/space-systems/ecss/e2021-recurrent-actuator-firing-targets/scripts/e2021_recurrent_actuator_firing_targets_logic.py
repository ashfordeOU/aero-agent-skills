#!/usr/bin/env python3
"""Recurrent actuator firing targets (ECSS-E-ST-20-21C 5.6.3).

Offline, deterministic, standard library only. The ECSS clause is cited as
the anchor; the procedure below is a paraphrase into implementable logic.

Model
-----
A recurrent actuator product is sold off a catalogue and reused across
programmes, so its published all-fire current and minimum actuation
duration are not one unit's measurements -- they are figures that have to
bound the whole production population and still sit inside what an
ordinary bus can deliver:

* the published all-fire current is the WORST unit's all-fire, because a
  figure that only the best unit meets is not a product specification;
* the published no-fire current is the LOWEST unit's no-fire, for the
  same reason read from the safety side;
* the two have to stay separated. The firing circuit is designed above
  all-fire with a design factor and the inhibit circuit below no-fire,
  and a population whose bands nearly touch leaves no room for either;
* the minimum actuation duration is the mechanism function time carried
  with a margin factor and never below a product floor, because a
  command shorter than the mechanism takes to complete leaves the
  actuator part-actuated.

The recommended figures are then graded against the catalogue targets and
against the drive the bus can actually supply.
"""

import math

# The firing circuit is designed this far above the published all-fire.
DEFAULT_DRIVE_DESIGN_FACTOR = 1.5
# Below this all-fire/no-fire ratio there is no room for both circuits.
MIN_SEPARATION_RATIO = 1.5
# At or above this ratio the population is comfortably separated.
WELL_SEPARATED_RATIO = 2.0
# The commanded duration carries this much over the function time.
DEFAULT_DURATION_MARGIN_FACTOR = 2.0
# A recurrent product never publishes a duration under this floor.
DEFAULT_DURATION_FLOOR_S = 0.010
# Comparisons absorb representation error only; targets are never widened.
REL_TOL = 1e-12
ABS_TOL = 1e-18

_REQUIRED_KEYS = ("units", "function_time_s")
_OPTIONAL_KEYS = (
    "target_all_fire_a",
    "target_minimum_duration_s",
    "drive_capability_a",
    "drive_design_factor",
    "duration_margin_factor",
    "duration_floor_s",
    "commanded_duration_s",
    "rated_maximum_current_a",
)
_UNIT_KEYS = ("unit_id", "no_fire_a", "all_fire_a")


def _as_float(name, value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a real number, got %r" % (name, value))
    out = float(value)
    if math.isnan(out) or math.isinf(out):
        raise ValueError("%s must be finite, got %r" % (name, value))
    return out


def _positive(name, value):
    out = _as_float(name, value)
    if out <= 0.0:
        raise ValueError("%s must be > 0, got %g" % (name, out))
    return out


def within_limit(value, limit):
    """True when ``value`` is at or under ``limit``.

    The tolerance absorbs representation error carried by a product of
    floats; the published target itself is untouched.
    """
    value = _as_float("value", value)
    limit = _as_float("limit", limit)
    return value < limit or math.isclose(
        value, limit, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def at_least(value, floor):
    """True when ``value`` reaches ``floor``, representation error absorbed."""
    value = _as_float("value", value)
    floor = _as_float("floor", floor)
    return value > floor or math.isclose(
        value, floor, rel_tol=REL_TOL, abs_tol=ABS_TOL
    )


def validate_unit(unit, index=0):
    """Check one measured unit and return its two currents."""
    if not isinstance(unit, dict):
        raise ValueError("units[%d] must be a mapping" % index)
    unknown = sorted(set(unit) - set(_UNIT_KEYS))
    if unknown:
        raise ValueError("units[%d] has unknown keys: %s" % (index, ", ".join(unknown)))
    missing = [key for key in _UNIT_KEYS if key not in unit]
    if missing:
        raise ValueError(
            "units[%d] missing keys: %s" % (index, ", ".join(missing))
        )
    unit_id = unit["unit_id"]
    if not isinstance(unit_id, str) or not unit_id.strip():
        raise ValueError("units[%d].unit_id must be a non-empty string" % index)
    no_fire = _positive("units[%d].no_fire_a" % index, unit["no_fire_a"])
    all_fire = _positive("units[%d].all_fire_a" % index, unit["all_fire_a"])
    if not no_fire < all_fire:
        raise ValueError(
            "units[%d] (%s): no_fire_a %g A must be below all_fire_a %g A"
            % (index, unit_id.strip(), no_fire, all_fire)
        )
    return unit_id.strip(), no_fire, all_fire


def population_currents(units):
    """Published pair for a population: worst all-fire, lowest no-fire."""
    if not isinstance(units, (list, tuple)):
        raise ValueError("units must be a list or tuple of measured units")
    if len(units) == 0:
        raise ValueError("units must hold at least one measured unit")
    seen = set()
    highest_all_fire = None
    lowest_no_fire = None
    for index, unit in enumerate(units):
        unit_id, no_fire, all_fire = validate_unit(unit, index)
        if unit_id in seen:
            raise ValueError("duplicate unit_id %r in units" % unit_id)
        seen.add(unit_id)
        if highest_all_fire is None or all_fire > highest_all_fire:
            highest_all_fire = all_fire
        if lowest_no_fire is None or no_fire < lowest_no_fire:
            lowest_no_fire = no_fire
    return {
        "published_all_fire_a": highest_all_fire,
        "published_no_fire_a": lowest_no_fire,
        "unit_count": len(units),
    }


def separation_ratio(all_fire_a, no_fire_a):
    """How far the all-fire current sits above the no-fire current."""
    all_fire = _positive("all_fire_a", all_fire_a)
    no_fire = _positive("no_fire_a", no_fire_a)
    if not no_fire < all_fire:
        raise ValueError(
            "no_fire_a %g A must be below all_fire_a %g A" % (no_fire, all_fire)
        )
    return all_fire / no_fire


def categorize_separation(ratio):
    """Name the separation regime of a population's firing band."""
    value = _positive("ratio", ratio)
    if at_least(value, WELL_SEPARATED_RATIO):
        return "well-separated"
    if at_least(value, MIN_SEPARATION_RATIO):
        return "adequate"
    return "insufficient"


def required_drive_current_a(all_fire_a, design_factor=DEFAULT_DRIVE_DESIGN_FACTOR):
    """Current the firing circuit has to deliver above the published all-fire."""
    all_fire = _positive("all_fire_a", all_fire_a)
    factor = _positive("design_factor", design_factor)
    if factor < 1.0:
        raise ValueError(
            "design_factor must be >= 1.0, a firing circuit is never designed "
            "below the all-fire current, got %g" % factor
        )
    return all_fire * factor


def recommended_actuation_duration_s(
    function_time_s,
    margin_factor=DEFAULT_DURATION_MARGIN_FACTOR,
    floor_s=DEFAULT_DURATION_FLOOR_S,
):
    """Minimum duration the catalogue should publish for this mechanism."""
    function_time = _positive("function_time_s", function_time_s)
    factor = _positive("margin_factor", margin_factor)
    if factor < 1.0:
        raise ValueError(
            "margin_factor must be >= 1.0, the command cannot be shorter than "
            "the mechanism function time, got %g" % factor
        )
    floor = _positive("floor_s", floor_s)
    carried = function_time * factor
    return carried if carried > floor else floor


def duration_is_floor_driven(
    function_time_s,
    margin_factor=DEFAULT_DURATION_MARGIN_FACTOR,
    floor_s=DEFAULT_DURATION_FLOOR_S,
):
    """True when the product floor, not the mechanism, sets the duration."""
    function_time = _positive("function_time_s", function_time_s)
    factor = _positive("margin_factor", margin_factor)
    floor = _positive("floor_s", floor_s)
    return within_limit(function_time * factor, floor)


def evaluate_recurrent_firing_targets(spec):
    """Full clause 5.6.3 target assessment for one recurrent actuator product.

    Returns the published population figures, the recommended drive current
    and minimum actuation duration, the findings and the verdict.
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping of population and target data")
    known = set(_REQUIRED_KEYS) | set(_OPTIONAL_KEYS)
    unknown = sorted(set(spec) - known)
    if unknown:
        raise ValueError("unknown spec keys: %s" % ", ".join(unknown))
    missing = [key for key in _REQUIRED_KEYS if key not in spec]
    if missing:
        raise ValueError("spec missing required keys: %s" % ", ".join(missing))

    population = population_currents(spec["units"])
    all_fire = population["published_all_fire_a"]
    no_fire = population["published_no_fire_a"]
    ratio = separation_ratio(all_fire, no_fire)
    separation = categorize_separation(ratio)

    design_factor = _positive(
        "drive_design_factor", spec.get("drive_design_factor", DEFAULT_DRIVE_DESIGN_FACTOR)
    )
    drive_current = required_drive_current_a(all_fire, design_factor)
    margin_factor = _positive(
        "duration_margin_factor",
        spec.get("duration_margin_factor", DEFAULT_DURATION_MARGIN_FACTOR),
    )
    floor_s = _positive("duration_floor_s", spec.get("duration_floor_s", DEFAULT_DURATION_FLOOR_S))
    duration = recommended_actuation_duration_s(
        spec["function_time_s"], margin_factor, floor_s
    )

    findings = []
    if separation == "insufficient":
        findings.append(
            {
                "code": "firing-band-too-narrow",
                "separation_ratio": ratio,
                "detail": "all-fire sits only %.2fx above no-fire across %d unit(s), "
                "leaving no room for both the firing and the inhibit circuit"
                % (ratio, population["unit_count"]),
            }
        )
    if "target_all_fire_a" in spec:
        target = _positive("target_all_fire_a", spec["target_all_fire_a"])
        if not within_limit(all_fire, target):
            findings.append(
                {
                    "code": "all-fire-above-catalogue-target",
                    "published_all_fire_a": all_fire,
                    "target_all_fire_a": target,
                    "detail": "worst unit needs %.3f A against a %.3f A catalogue "
                    "target" % (all_fire, target),
                }
            )
    if "target_minimum_duration_s" in spec:
        target_duration = _positive(
            "target_minimum_duration_s", spec["target_minimum_duration_s"]
        )
        if not at_least(target_duration, duration):
            findings.append(
                {
                    "code": "published-duration-below-recommendation",
                    "recommended_duration_s": duration,
                    "target_minimum_duration_s": target_duration,
                    "detail": "catalogue publishes %.4f s where the mechanism and "
                    "margin ask for %.4f s" % (target_duration, duration),
                }
            )
    if "drive_capability_a" in spec:
        capability = _positive("drive_capability_a", spec["drive_capability_a"])
        if not at_least(capability, drive_current):
            findings.append(
                {
                    "code": "drive-cannot-reach-all-fire",
                    "drive_capability_a": capability,
                    "required_drive_current_a": drive_current,
                    "detail": "bus supplies %.3f A where the design factor asks for "
                    "%.3f A" % (capability, drive_current),
                }
            )
    if "rated_maximum_current_a" in spec:
        rated_max = _positive("rated_maximum_current_a", spec["rated_maximum_current_a"])
        if not within_limit(drive_current, rated_max):
            findings.append(
                {
                    "code": "design-current-over-actuator-rating",
                    "required_drive_current_a": drive_current,
                    "rated_maximum_current_a": rated_max,
                    "detail": "the firing circuit would push %.3f A into a %.3f A "
                    "part" % (drive_current, rated_max),
                }
            )
    if "commanded_duration_s" in spec:
        commanded = _positive("commanded_duration_s", spec["commanded_duration_s"])
        if not at_least(commanded, duration):
            findings.append(
                {
                    "code": "command-shorter-than-minimum-actuation",
                    "commanded_duration_s": commanded,
                    "recommended_duration_s": duration,
                    "detail": "a %.4f s command cannot complete a mechanism asking "
                    "for %.4f s" % (commanded, duration),
                }
            )

    return {
        "published_all_fire_a": all_fire,
        "published_no_fire_a": no_fire,
        "unit_count": population["unit_count"],
        "separation_ratio": ratio,
        "separation_category": separation,
        "required_drive_current_a": drive_current,
        "recommended_duration_s": duration,
        "duration_is_floor_driven": duration_is_floor_driven(
            spec["function_time_s"], margin_factor, floor_s
        ),
        "findings": findings,
        "recurrent_ready": not findings,
    }
