"""Reattaching an element with bonding compound during corrective work.

Anchor: ECSS-Q-ST-60-05C clause 10.5.4 (the conditions under which an element
may be reattached with a bonding compound while a hybrid is open for permitted
corrective work). Paraphrased into an implementable procedure; no standard
text is reproduced.

Procedure implemented here
--------------------------
1. Validate the compound: that it is an approved one, that it is inside its
   storage life on the day it is used, and that the mixed material is still
   inside its working life when it goes down.
2. Validate the joint: the element footprint, the dispensed volume and the
   bond line those two imply, against the thickness window the compound is
   qualified for.
3. Size the cure. Each compound carries a schedule of temperatures and the
   dwell each one needs; a cure run cooler than a tabulated point needs the
   longer dwell interpolated between the points, and a cure shorter than that
   is an under-cure whatever the paperwork says.
4. Check the cure against the neighbourhood: the peak cure temperature is
   applied to the whole assembly, so any already-mounted element with a lower
   limit is exposed by it.
5. Return permitted, permitted-with-conditions or not-permitted with every
   failing condition named.

Cure completion and bond line are ratios and quotients that land exactly on
their bounds for a nominal joint, so those comparisons carry a tolerance
rather than being strict inequalities.
"""

import datetime
import math

__all__ = [
    "RATIO_TOLERANCE",
    "DEFAULT_CURE_SCHEDULE",
    "DEFAULT_BOND_LINE_UM",
    "SHELF_LIFE_CAUTION_DAYS",
    "parse_date",
    "validate_compound",
    "shelf_life_days_remaining",
    "working_life_remaining_minutes",
    "bond_line_thickness_um",
    "required_cure_minutes",
    "cure_completion_ratio",
    "elements_exceeded_by_cure",
    "assess_adhesive_repair",
]

# A nominal joint lands on its bond-line bound and a nominal cure lands on a
# completion of one. Absorb representation error here, not in the limits.
RATIO_TOLERANCE = 1e-9

# Temperature (degrees Celsius) against the dwell in minutes that temperature
# needs. Between two tabulated points the dwell is interpolated linearly.
DEFAULT_CURE_SCHEDULE = ((80.0, 240.0), (100.0, 120.0), (125.0, 60.0), (150.0, 30.0))

# Qualified bond-line window in micrometres.
DEFAULT_BOND_LINE_UM = (25.0, 125.0)

# Inside this many days of the storage-life date the compound is usable but
# the use is a recorded condition rather than an unremarkable one.
SHELF_LIFE_CAUTION_DAYS = 30


def _require_positive_number(value, label):
    """Return value as a strictly positive finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number <= 0.0:
        raise ValueError("%s must be positive, got %g" % (label, number))
    return number


def _require_non_negative_number(value, label):
    """Return value as a non-negative finite float."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("%s must be a number, got %r" % (label, value))
    number = float(value)
    if math.isnan(number) or math.isinf(number):
        raise ValueError("%s must be finite, got %r" % (label, value))
    if number < 0.0:
        raise ValueError("%s must not be negative, got %g" % (label, number))
    return number


def parse_date(value, label):
    """Return an ISO date string or date as a date, raising on anything else."""
    if isinstance(value, datetime.date) and not isinstance(value, datetime.datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.date.fromisoformat(value.strip())
        except ValueError as exc:
            raise ValueError("%s is not an ISO date: %r" % (label, value)) from exc
    raise ValueError("%s must be an ISO date string or a date, got %r" % (label, value))


def validate_compound(compound):
    """Return the normalised bonding-compound record."""
    if not isinstance(compound, dict):
        raise ValueError("compound must be a mapping")
    for key in ("compound_id", "storage_life_expiry", "working_life_minutes"):
        if key not in compound:
            raise ValueError("compound missing required key '%s'" % key)
    compound_id = compound["compound_id"]
    if not isinstance(compound_id, str) or not compound_id.strip():
        raise ValueError("compound['compound_id'] must be a non-empty string")
    conductive = compound.get("electrically_conductive", False)
    if not isinstance(conductive, bool):
        raise ValueError("compound['electrically_conductive'] must be a boolean")
    approved = compound.get("approved_for_programme", False)
    if not isinstance(approved, bool):
        raise ValueError("compound['approved_for_programme'] must be a boolean")
    return {
        "compound_id": compound_id.strip(),
        "storage_life_expiry": parse_date(
            compound["storage_life_expiry"], "compound['storage_life_expiry']"
        ),
        "working_life_minutes": _require_positive_number(
            compound["working_life_minutes"], "compound['working_life_minutes']"
        ),
        "electrically_conductive": conductive,
        "approved_for_programme": approved,
    }


def shelf_life_days_remaining(compound, use_date):
    """Return days between the day of use and the storage-life date.

    Negative means the compound was already past its storage life when it was
    used; zero means it was used on the last day it was good for.
    """
    record = validate_compound(compound)
    day = parse_date(use_date, "use_date")
    return (record["storage_life_expiry"] - day).days


def working_life_remaining_minutes(compound, minutes_since_mix):
    """Return the working life the mixed compound had left when it went down."""
    record = validate_compound(compound)
    elapsed = _require_non_negative_number(minutes_since_mix, "minutes_since_mix")
    return record["working_life_minutes"] - elapsed


def bond_line_thickness_um(dispensed_volume_mm3, footprint_mm2):
    """Return the bond line the dispensed volume gives under the footprint."""
    volume = _require_positive_number(dispensed_volume_mm3, "dispensed_volume_mm3")
    area = _require_positive_number(footprint_mm2, "footprint_mm2")
    # Scale before dividing: millimetres cubed over millimetres squared is a
    # length in millimetres, and multiplying first keeps the conversion exact
    # for the round volumes a dispense programme actually uses.
    return volume * 1000.0 / area


def required_cure_minutes(temperature_c, schedule=DEFAULT_CURE_SCHEDULE):
    """Return the dwell the compound needs at this cure temperature.

    Between two tabulated temperatures the dwell is interpolated linearly.
    Above the hottest tabulated point the hottest dwell is held rather than
    extrapolated -- a schedule says nothing about temperatures it does not
    cover, and a cure below the coolest point is not covered at all.
    """
    temperature = _require_positive_number(temperature_c, "temperature_c")
    points = tuple(schedule)
    if len(points) < 2:
        raise ValueError("cure schedule needs at least two temperature points")
    ordered = sorted((float(t), float(m)) for t, m in points)
    if temperature < ordered[0][0] - RATIO_TOLERANCE:
        raise ValueError(
            "cure temperature %g C is below the coolest point the schedule covers (%g C)"
            % (temperature, ordered[0][0])
        )
    if temperature >= ordered[-1][0]:
        return ordered[-1][1]
    for (t_low, m_low), (t_high, m_high) in zip(ordered, ordered[1:]):
        if t_low <= temperature <= t_high:
            span = t_high - t_low
            if span == 0.0:
                return m_low
            fraction = (temperature - t_low) / span
            return m_low + fraction * (m_high - m_low)
    return ordered[0][1]


def cure_completion_ratio(temperature_c, applied_minutes, schedule=DEFAULT_CURE_SCHEDULE):
    """Return applied dwell over required dwell; one is a just-complete cure."""
    applied = _require_positive_number(applied_minutes, "applied_minutes")
    return applied / required_cure_minutes(temperature_c, schedule)


def elements_exceeded_by_cure(temperature_c, elements):
    """Return the already-mounted elements whose own limit the cure passes."""
    temperature = _require_positive_number(temperature_c, "temperature_c")
    if isinstance(elements, dict) or not isinstance(elements, (list, tuple)):
        raise ValueError("elements must be a sequence of element records")
    exceeded = []
    for index, element in enumerate(elements):
        if not isinstance(element, dict):
            raise ValueError("elements[%d] must be a mapping" % index)
        for key in ("element_id", "temperature_limit_c"):
            if key not in element:
                raise ValueError("elements[%d] missing required key '%s'" % (index, key))
        element_id = element["element_id"]
        if not isinstance(element_id, str) or not element_id.strip():
            raise ValueError("elements[%d]['element_id'] must be a non-empty string" % index)
        limit = _require_positive_number(
            element["temperature_limit_c"], "elements[%d]['temperature_limit_c']" % index
        )
        if limit < temperature - RATIO_TOLERANCE:
            exceeded.append(
                {
                    "element_id": element_id.strip(),
                    "temperature_limit_c": limit,
                    "cure_temperature_c": temperature,
                }
            )
    return exceeded


def assess_adhesive_repair(spec):
    """Run the full clause 10.5.4 adhesive reattachment assessment.

    spec keys: compound, use_date, minutes_since_mix, dispensed_volume_mm3,
    footprint_mm2, cure_temperature_c, cure_minutes; optional elements
    (default empty), bond_line_window_um, cure_schedule, site_cleaned
    (default False) and isolation_required (default False).
    """
    if not isinstance(spec, dict):
        raise ValueError("spec must be a mapping")
    required = (
        "compound",
        "use_date",
        "minutes_since_mix",
        "dispensed_volume_mm3",
        "footprint_mm2",
        "cure_temperature_c",
        "cure_minutes",
    )
    for key in required:
        if key not in spec:
            raise ValueError("spec missing required key '%s'" % key)
    site_cleaned = spec.get("site_cleaned", False)
    if not isinstance(site_cleaned, bool):
        raise ValueError("site_cleaned must be a boolean")
    isolation_required = spec.get("isolation_required", False)
    if not isinstance(isolation_required, bool):
        raise ValueError("isolation_required must be a boolean")

    compound = validate_compound(spec["compound"])
    window = tuple(spec.get("bond_line_window_um", DEFAULT_BOND_LINE_UM))
    if len(window) != 2:
        raise ValueError("bond_line_window_um must be a (minimum, maximum) pair")
    thin = _require_positive_number(window[0], "bond_line_window_um[0]")
    thick = _require_positive_number(window[1], "bond_line_window_um[1]")
    if thin >= thick:
        raise ValueError("bond_line_window_um minimum must be below its maximum")
    schedule = spec.get("cure_schedule", DEFAULT_CURE_SCHEDULE)

    days_left = shelf_life_days_remaining(spec["compound"], spec["use_date"])
    working_left = working_life_remaining_minutes(spec["compound"], spec["minutes_since_mix"])
    thickness = bond_line_thickness_um(spec["dispensed_volume_mm3"], spec["footprint_mm2"])
    required_dwell = required_cure_minutes(spec["cure_temperature_c"], schedule)
    completion = cure_completion_ratio(spec["cure_temperature_c"], spec["cure_minutes"], schedule)
    exposed = elements_exceeded_by_cure(spec["cure_temperature_c"], spec.get("elements", []))

    blockers = []
    conditions = []
    if not compound["approved_for_programme"]:
        blockers.append("compound %s is not approved for the programme" % compound["compound_id"])
    if days_left < 0:
        blockers.append(
            "compound %s was %d day(s) past its storage life on the day of use"
            % (compound["compound_id"], -days_left)
        )
    elif days_left <= SHELF_LIFE_CAUTION_DAYS:
        conditions.append(
            "compound %s had %d day(s) of storage life left" % (compound["compound_id"], days_left)
        )
    if working_left < -RATIO_TOLERANCE:
        blockers.append(
            "mixed compound was %.1f minute(s) past its working life when dispensed"
            % (-working_left)
        )
    if not site_cleaned:
        blockers.append("previous compound was not removed from the attachment site")
    if thickness < thin - RATIO_TOLERANCE or thickness > thick + RATIO_TOLERANCE:
        blockers.append(
            "bond line %.2f um is outside the qualified window %.2f-%.2f um"
            % (thickness, thin, thick)
        )
    if completion < 1.0 - RATIO_TOLERANCE:
        blockers.append(
            "cure is %.1f%% complete: %.1f minute(s) applied against %.1f required"
            % (100.0 * completion, float(spec["cure_minutes"]), required_dwell)
        )
    if exposed:
        blockers.append(
            "cure temperature passes the limit of %d already-mounted element(s): %s"
            % (len(exposed), ", ".join(e["element_id"] for e in exposed))
        )
    if isolation_required and compound["electrically_conductive"]:
        blockers.append(
            "attachment needs electrical isolation and compound %s is conductive"
            % compound["compound_id"]
        )

    if blockers:
        disposition = "not-permitted"
    elif conditions:
        disposition = "permitted-with-conditions"
    else:
        disposition = "permitted"
    return {
        "compound_id": compound["compound_id"],
        "shelf_life_days_remaining": days_left,
        "working_life_remaining_minutes": working_left,
        "bond_line_um": thickness,
        "bond_line_window_um": (thin, thick),
        "required_cure_minutes": required_dwell,
        "cure_completion_ratio": completion,
        "elements_exceeded_by_cure": exposed,
        "blockers": blockers,
        "conditions": conditions,
        "disposition": disposition,
        "permitted": disposition != "not-permitted",
    }
