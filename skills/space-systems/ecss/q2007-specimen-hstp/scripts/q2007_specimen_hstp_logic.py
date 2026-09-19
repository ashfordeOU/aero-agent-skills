#!/usr/bin/env python3
"""Specimen handling, storage, transportation and preservation inside a
test centre, ECSS-Q-ST-20-07C clause 5.7.4.4.

Paraphrased clause intent, no verbatim standard text. The clause carries
the handling, storage, transportation and preservation provisions of
ECSS-Q-ST-20-08 into the centre's own perimeter: the time a customer
item spends off the rig is controlled as tightly as the time on it.
This module turns a stay into a deterministic assessment:

  storage log vs limits   -> which readings, and for how long, sat out
  preservation clock      -> is the item still preserved on its use day
  transport monitors      -> what the internal moves actually applied
  handling constraints    -> mass, lift points and sensitivity

stdlib only, offline, deterministic.
"""

from __future__ import annotations

import math

# Comparison tolerance. Environmental readings, limits and day counts
# are floats, so a reading exactly on a bound can land a few units in
# the last place outside it. The tolerance absorbs that representation
# error only; it never moves the limit the item was accepted under.
REL_TOL = 1e-12
ABS_TOL = 1e-12

# Above this mass an item is not lifted by hand.
TWO_PERSON_LIFT_LIMIT_KG = 25.0

HSTP_COMPLIANT = "hstp-compliant"
HSTP_DEFICIENT = "hstp-deficient"

TEMPERATURE = "temperature_c"
HUMIDITY = "humidity_pct"
CLEANLINESS = "cleanliness_class"


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


def _scalar(value, name):
    return _number({"v": value}, "v", name)


def _flag(record, key, where):
    if key not in record:
        raise ValueError("%s: missing required field %r" % (where, key))
    value = record[key]
    if not isinstance(value, bool):
        raise ValueError("%s: field %r must be a boolean, got %r" % (where, key, value))
    return value


def at_least(value, bound):
    """True when a value reaches a lower bound, absorbing float error."""
    if value >= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def at_most(value, bound):
    """True when a value stays under an upper bound, absorbing float error."""
    if value <= bound:
        return True
    return math.isclose(value, bound, rel_tol=REL_TOL, abs_tol=ABS_TOL)


def validate_limits(limits):
    """Validate the storage and transport limits the item was accepted under."""
    where = "limits"
    if not isinstance(limits, dict):
        raise ValueError("%s: record must be a mapping" % where)
    out = {}
    lower = _number(limits, "temperature_min_c", where)
    upper = _number(limits, "temperature_max_c", where)
    if not upper > lower:
        raise ValueError(
            "%s: temperature_max_c (%g) must exceed temperature_min_c (%g)"
            % (where, upper, lower)
        )
    out["temperature_min_c"] = lower
    out["temperature_max_c"] = upper

    humidity = _number(limits, "humidity_max_pct", where)
    if not 0.0 < humidity <= 100.0:
        raise ValueError(
            "%s: humidity_max_pct must be within (0, 100], got %g" % (where, humidity)
        )
    out["humidity_max_pct"] = humidity

    cleanliness = _number(limits, "cleanliness_class_max", where)
    if cleanliness <= 0.0:
        raise ValueError(
            "%s: cleanliness_class_max must be > 0, got %g" % (where, cleanliness)
        )
    out["cleanliness_class_max"] = cleanliness

    shock = _number(limits, "max_shock_g", where)
    if shock <= 0.0:
        raise ValueError("%s: max_shock_g must be > 0, got %g" % (where, shock))
    out["max_shock_g"] = shock

    tilt = _number(limits, "max_tilt_deg", where)
    if tilt < 0.0:
        raise ValueError("%s: max_tilt_deg must be >= 0, got %g" % (where, tilt))
    out["max_tilt_deg"] = tilt

    shelf = _number(limits, "shelf_life_days", where)
    if shelf <= 0.0:
        raise ValueError("%s: shelf_life_days must be > 0, got %g" % (where, shelf))
    out["shelf_life_days"] = shelf
    return out


def validate_storage_log(samples):
    """Validate the storage log and return it in strict time order."""
    if not isinstance(samples, (list, tuple)) or not samples:
        raise ValueError("samples: must be a non-empty sequence of storage readings")
    out = []
    previous = None
    for index, sample in enumerate(samples):
        where = "samples[%d]" % index
        if not isinstance(sample, dict):
            raise ValueError("%s: record must be a mapping" % where)
        time_s = _number(sample, "time_s", where)
        if previous is not None and not time_s > previous:
            raise ValueError(
                "%s: reading at %g does not follow the previous one at %g"
                % (where, time_s, previous)
            )
        previous = time_s
        entry = {"time_s": time_s}
        for key in (TEMPERATURE, HUMIDITY, CLEANLINESS):
            entry[key] = _number(sample, key, where)
        out.append(entry)
    return out


def sample_excursions(sample, limits):
    """Name every limit one storage reading sits outside."""
    bounds = validate_limits(limits)
    if not isinstance(sample, dict):
        raise ValueError("sample: record must be a mapping")
    temperature = _number(sample, TEMPERATURE, "sample")
    humidity = _number(sample, HUMIDITY, "sample")
    cleanliness = _number(sample, CLEANLINESS, "sample")

    out = []
    if not at_least(temperature, bounds["temperature_min_c"]):
        out.append(TEMPERATURE)
    elif not at_most(temperature, bounds["temperature_max_c"]):
        out.append(TEMPERATURE)
    if not at_most(humidity, bounds["humidity_max_pct"]):
        out.append(HUMIDITY)
    if not at_most(cleanliness, bounds["cleanliness_class_max"]):
        out.append(CLEANLINESS)
    return out


def environment_excursions(samples, limits):
    """Every storage reading that sat outside a limit, with what it broke."""
    log = validate_storage_log(samples)
    bounds = validate_limits(limits)
    out = []
    for sample in log:
        broken = sample_excursions(sample, bounds)
        if broken:
            out.append({"time_s": sample["time_s"], "limits": broken})
    return out


def time_outside_limits_s(samples, limits):
    """Seconds the item spent outside its limits, from the sample spacing."""
    log = validate_storage_log(samples)
    bounds = validate_limits(limits)
    if len(log) < 2:
        return 0.0
    total = 0.0
    for index in range(len(log) - 1):
        if sample_excursions(log[index], bounds):
            total += log[index + 1]["time_s"] - log[index]["time_s"]
    return total


def preservation_expiry_day(applied_day, shelf_life_days):
    """Day index on which the preservation stops being valid."""
    applied = _scalar(applied_day, "applied_day")
    shelf = _scalar(shelf_life_days, "shelf_life_days")
    if shelf <= 0.0:
        raise ValueError("shelf_life_days must be > 0, got %g" % shelf)
    return applied + shelf


def preservation_is_valid(use_day, applied_day, shelf_life_days):
    """True when the item is still preserved on the day it is to be used."""
    use = _scalar(use_day, "use_day")
    applied = _scalar(applied_day, "applied_day")
    if use < applied:
        raise ValueError(
            "use_day (%g) cannot precede applied_day (%g)" % (use, applied)
        )
    return at_most(use, preservation_expiry_day(applied, shelf_life_days))


def transport_findings(move, limits):
    """Read the monitors and the seal state of one internal move."""
    bounds = validate_limits(limits)
    where = "move"
    if not isinstance(move, dict):
        raise ValueError("%s: record must be a mapping" % where)
    shock = _number(move, "peak_shock_g", where)
    tilt = _number(move, "peak_tilt_deg", where)
    if shock < 0.0:
        raise ValueError("%s: peak_shock_g must be >= 0, got %g" % (where, shock))
    if tilt < 0.0:
        raise ValueError("%s: peak_tilt_deg must be >= 0, got %g" % (where, tilt))
    monitors_fitted = _flag(move, "monitors_fitted", where)
    seal_intact = _flag(move, "seal_intact", where)

    out = []
    if not monitors_fitted:
        out.append(
            "the move ran with no shock or tilt monitor fitted, so nothing records "
            "what the item was subjected to between stores and bay"
        )
    if not at_most(shock, bounds["max_shock_g"]):
        out.append(
            "the move applied %g g against the %g g the item may take"
            % (shock, bounds["max_shock_g"])
        )
    if not at_most(tilt, bounds["max_tilt_deg"]):
        out.append(
            "the item was tilted to %g degrees against the %g degrees allowed"
            % (tilt, bounds["max_tilt_deg"])
        )
    if not seal_intact:
        out.append(
            "the protective seal did not survive the move, so the preservation "
            "inside it is no longer evidenced"
        )
    return out


def handling_findings(item, lift_limit_kg=TWO_PERSON_LIFT_LIMIT_KG):
    """Check the constraints the item's mass, lift points and sensitivity set."""
    where = "item"
    if not isinstance(item, dict):
        raise ValueError("%s: record must be a mapping" % where)
    mass = _number(item, "mass_kg", where)
    if mass <= 0.0:
        raise ValueError("%s: mass_kg must be > 0, got %g" % (where, mass))
    limit = _scalar(lift_limit_kg, "lift_limit_kg")
    if limit <= 0.0:
        raise ValueError("lift_limit_kg must be > 0, got %g" % limit)

    lifting_equipment = _flag(item, "lifting_equipment_used", where)
    certificate_valid = _flag(item, "lifting_certificate_valid", where)
    lift_points_used = _flag(item, "declared_lift_points_used", where)
    sensitive = _flag(item, "electrostatic_sensitive", where)
    protection = _flag(item, "electrostatic_protection_applied", where)

    out = []
    if not at_most(mass, limit) and not lifting_equipment:
        out.append(
            "a %g kg item was moved without lifting equipment, over the %g kg hand "
            "limit" % (mass, limit)
        )
    if lifting_equipment and not certificate_valid:
        out.append(
            "the lifting equipment used carries no current certificate, so the lift "
            "itself is unevidenced"
        )
    if not lift_points_used:
        out.append(
            "the item was not lifted by its declared lift points, so the load path "
            "through the structure is unknown"
        )
    if sensitive and not protection:
        out.append(
            "an electrostatic-sensitive item was handled with no protection applied"
        )
    return out


def assess_hstp(plan, lift_limit_kg=TWO_PERSON_LIFT_LIMIT_KG):
    """Full clause 5.7.4.4 assessment of one specimen's stay in the centre."""
    if not isinstance(plan, dict):
        raise ValueError("plan: record must be a mapping")
    bounds = validate_limits(plan.get("limits"))
    log = validate_storage_log(plan.get("storage_log"))
    excursions = environment_excursions(log, bounds)
    outside_s = time_outside_limits_s(log, bounds)

    applied_day = _number(plan, "preservation_applied_day", "plan")
    use_day = _number(plan, "planned_use_day", "plan")
    expiry_day = preservation_expiry_day(applied_day, bounds["shelf_life_days"])
    preserved = preservation_is_valid(use_day, applied_day, bounds["shelf_life_days"])

    moves = plan.get("internal_moves", [])
    if not isinstance(moves, (list, tuple)):
        raise ValueError("plan: internal_moves must be a sequence")
    move_findings = []
    for index, move in enumerate(moves):
        for finding in transport_findings(move, bounds):
            move_findings.append("internal move %d: %s" % (index + 1, finding))

    handling = handling_findings(plan.get("item", {}), lift_limit_kg)

    findings = []
    for entry in excursions:
        findings.append(
            "storage reading at %g s sat outside %s"
            % (entry["time_s"], ", ".join(entry["limits"]))
        )
    if not preserved:
        findings.append(
            "preservation applied on day %g expires on day %g, before the planned "
            "use day %g" % (applied_day, expiry_day, use_day)
        )
    findings.extend(move_findings)
    findings.extend(handling)

    limitations = []
    if not moves:
        limitations.append(
            "no internal move is recorded, so the assessment covers storage and "
            "preservation only"
        )

    return {
        "limits": bounds,
        "excursions": excursions,
        "time_outside_limits_s": outside_s,
        "preservation_expiry_day": expiry_day,
        "preservation_is_valid": preserved,
        "transport_findings": move_findings,
        "handling_findings": handling,
        "findings": findings,
        "limitations": limitations,
        "verdict": HSTP_COMPLIANT if not findings else HSTP_DEFICIENT,
    }
