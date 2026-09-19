"""Particle and UV radiation testing: in-situ versus ex-situ read-out.

Anchor: ECSS-Q-ST-70-06C, the measurement clause of particle and UV
radiation testing for space materials (paraphrased into an implementable
procedure; no standard text is reproduced).

Procedure implemented here:

1. A property can be read out without breaking vacuum (in-situ) or after
   the specimen has been taken out of the chamber (ex-situ). The choice
   is not a convenience: it decides whether the number that reaches the
   thermal or optical designer is the irradiated value or a value that
   has already started to come back.
2. Radiation-induced darkening in glasses, coatings and polymers bleaches
   once the specimen is warm, lit and in air. The recovery is described
   by a half-time, and the fraction that has come back by the time the
   instrument sees the specimen follows straight from the transfer time
   and that half-time.
3. When that fraction is large enough to matter, the read-out has to be
   in-situ. When it is small, an ex-situ read-out is acceptable, but
   only under handling controls that keep it small: a transfer-time
   ceiling derived from the half-time, an inert or evacuated transfer
   container for an air-sensitive surface, a humidity ceiling for a
   moisture-sensitive one, a light-tight container for a photo-bleaching
   one, and a ceiling on how often the specimen is brought back to air.
4. A property whose in-situ instrument does not exist in the facility is
   still a property that needed one. The decision records that as a
   finding rather than silently downgrading the requirement.
5. The allocation over a set of properties is sound only when every
   property has a mode, every mandated control is planned, and no
   property is read out in a way that hides the degradation it was
   exposed to show.

Stdlib only, offline, deterministic.
"""

import math

TRANSFER_ATMOSPHERES = ("air", "dry-nitrogen", "argon", "vacuum")
INERT_ATMOSPHERES = ("dry-nitrogen", "argon", "vacuum")

# The read-out has to be in-situ once this fraction of the induced change
# has recovered before the instrument sees the specimen.
MAX_RECOVERED_FRACTION = 0.05

# Handling ceilings for an ex-situ read-out.
MAX_TRANSFER_HUMIDITY_PCT = 10.0
MAX_BREAKS_TO_AIR = 1

MODE_IN_SITU = "in-situ"
MODE_EX_SITU = "ex-situ"

# Ratios and ceilings are built from decimal literals, so a value sitting
# exactly on a bound can land a few units in the last place past it. This
# tolerance absorbs that representation error only; no bound is relaxed.
DECISION_TOLERANCE = 1.0e-12


def _numeric(label, value, minimum=None, maximum=None):
    """Return value as a float, raising on anything that is not a number."""
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ValueError("%s must be numeric, got %r" % (label, value))
    val = float(value)
    if minimum is not None and val < minimum - DECISION_TOLERANCE:
        raise ValueError("%s must be >= %r, got %r" % (label, minimum, value))
    if maximum is not None and val > maximum + DECISION_TOLERANCE:
        raise ValueError("%s must be <= %r, got %r" % (label, maximum, value))
    return val


def _text(label, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string" % label)
    return value.strip()


def _flag(label, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (label, value))
    return value


def recovery_risk_ratio(transfer_time_h, recovery_half_time_h):
    """Transfer time expressed in recovery half-times."""
    transfer = _numeric("transfer_time_h", transfer_time_h, 0.0)
    half_time = _numeric("recovery_half_time_h", recovery_half_time_h, 0.0)
    if half_time <= 0.0:
        raise ValueError("recovery_half_time_h must be greater than zero")
    return transfer / half_time


def recovered_fraction_during_transfer(transfer_time_h, recovery_half_time_h):
    """Fraction of the induced change that has come back before read-out."""
    ratio = recovery_risk_ratio(transfer_time_h, recovery_half_time_h)
    return 1.0 - 0.5 ** ratio


def max_transfer_time(recovery_half_time_h):
    """Longest transfer that keeps the recovered fraction under the ceiling."""
    half_time = _numeric("recovery_half_time_h", recovery_half_time_h, 0.0)
    if half_time <= 0.0:
        raise ValueError("recovery_half_time_h must be greater than zero")
    remaining = 1.0 - MAX_RECOVERED_FRACTION
    return half_time * math.log(remaining) / math.log(0.5)


def validate_property(record):
    """Normalize one property read-out record, raising on a bad field."""
    if not isinstance(record, dict):
        raise ValueError("each property record must be a mapping")
    name = _text("property", record.get("property"))
    atmosphere = _text("transfer_atmosphere", record.get("transfer_atmosphere"))
    if atmosphere not in TRANSFER_ATMOSPHERES:
        raise ValueError("unknown transfer atmosphere %r" % (atmosphere,))
    breaks = record.get("breaks_to_air")
    if not isinstance(breaks, int) or isinstance(breaks, bool) or breaks < 0:
        raise ValueError("breaks_to_air must be a whole number of openings")
    half_time = record.get("recovery_half_time_h")
    if half_time is not None:
        half_time = _numeric("recovery_half_time_h", half_time, 0.0)
        if half_time <= 0.0:
            raise ValueError("recovery_half_time_h must be greater than zero")
    return {
        "property": name,
        "recovery_half_time_h": half_time,
        "air_sensitive": _flag("air_sensitive", record.get("air_sensitive", False)),
        "moisture_sensitive": _flag(
            "moisture_sensitive", record.get("moisture_sensitive", False)
        ),
        "light_sensitive": _flag(
            "light_sensitive", record.get("light_sensitive", False)
        ),
        "in_situ_instrument_available": _flag(
            "in_situ_instrument_available",
            record.get("in_situ_instrument_available", False),
        ),
        "transfer_time_h": _numeric(
            "transfer_time_h", record.get("transfer_time_h"), 0.0
        ),
        "transfer_atmosphere": atmosphere,
        "transfer_humidity_pct": _numeric(
            "transfer_humidity_pct", record.get("transfer_humidity_pct", 0.0), 0.0, 100.0
        ),
        "breaks_to_air": breaks,
    }


def in_situ_reasons(record):
    """Reasons an ex-situ read-out cannot be trusted for this property."""
    item = validate_property(record)
    reasons = []
    half_time = item["recovery_half_time_h"]
    if half_time is not None:
        recovered = recovered_fraction_during_transfer(
            item["transfer_time_h"], half_time
        )
        if recovered > MAX_RECOVERED_FRACTION + DECISION_TOLERANCE:
            reasons.append("recovery-during-transfer-exceeds-the-ceiling")
    if item["air_sensitive"] and item["transfer_atmosphere"] not in INERT_ATMOSPHERES:
        reasons.append("air-sensitive-surface-transferred-through-air")
    if (
        item["moisture_sensitive"]
        and item["transfer_humidity_pct"]
        > MAX_TRANSFER_HUMIDITY_PCT + DECISION_TOLERANCE
    ):
        reasons.append("moisture-sensitive-surface-above-the-humidity-ceiling")
    if item["breaks_to_air"] > MAX_BREAKS_TO_AIR:
        reasons.append("more-chamber-openings-than-the-handling-ceiling")
    return reasons


def in_situ_required(record):
    """True when this property cannot be read out after a transfer."""
    return bool(in_situ_reasons(record))


def handling_controls(record):
    """Handling controls an ex-situ read-out of this property has to carry."""
    item = validate_property(record)
    controls = []
    if item["recovery_half_time_h"] is not None:
        controls.append("transfer-time-ceiling")
    if item["air_sensitive"]:
        controls.append("inert-or-evacuated-transfer-container")
    if item["moisture_sensitive"]:
        controls.append("transfer-humidity-ceiling")
    if item["light_sensitive"]:
        controls.append("light-tight-transfer-container")
    controls.append("chamber-opening-count-ceiling")
    return sorted(set(controls))


def decide_measurement_mode(record):
    """Decide in-situ or ex-situ for one property, with its controls."""
    item = validate_property(record)
    reasons = in_situ_reasons(record)
    controls = handling_controls(record)
    findings = []

    half_time = item["recovery_half_time_h"]
    recovered = None
    ceiling = None
    if half_time is not None:
        recovered = recovered_fraction_during_transfer(
            item["transfer_time_h"], half_time
        )
        ceiling = max_transfer_time(half_time)

    if reasons:
        if item["in_situ_instrument_available"]:
            mode = MODE_IN_SITU
        else:
            mode = MODE_EX_SITU
            findings.append("in-situ-read-out-required-but-no-instrument-in-the-facility")
    else:
        mode = MODE_EX_SITU

    return {
        "property": item["property"],
        "mode": mode,
        "reasons": reasons,
        "handling_controls": controls if mode == MODE_EX_SITU else [],
        "recovered_fraction_during_transfer": recovered,
        "max_transfer_time_h": ceiling,
        "findings": findings,
    }


def assess_measurement_allocation(plan):
    """Assess the in-situ and ex-situ allocation across a property set."""
    if not isinstance(plan, dict):
        raise ValueError("plan must be a mapping")
    properties = plan.get("properties")
    if not isinstance(properties, (list, tuple)) or not properties:
        raise ValueError("plan must carry at least one property record")

    planned = plan.get("planned_controls", [])
    if not isinstance(planned, (list, tuple)):
        raise ValueError("planned_controls must be a sequence")
    planned_set = set(_text("planned control", c) for c in planned)

    decisions = []
    seen = set()
    findings = []
    for record in properties:
        decision = decide_measurement_mode(record)
        if decision["property"] in seen:
            raise ValueError("property %r appears twice" % (decision["property"],))
        seen.add(decision["property"])
        decisions.append(decision)
        findings.extend(decision["findings"])

    required_controls = set()
    for decision in decisions:
        required_controls.update(decision["handling_controls"])
    unplanned = sorted(required_controls - planned_set)
    if unplanned:
        findings.append("mandated-handling-control-not-planned")

    in_situ = [d["property"] for d in decisions if d["mode"] == MODE_IN_SITU]
    ex_situ = [d["property"] for d in decisions if d["mode"] == MODE_EX_SITU]

    return {
        "plan_id": plan.get("plan_id"),
        "decisions": decisions,
        "in_situ_properties": sorted(in_situ),
        "ex_situ_properties": sorted(ex_situ),
        "required_controls": sorted(required_controls),
        "unplanned_controls": unplanned,
        "findings": sorted(set(findings)),
        "allocation_sound": not findings,
    }
