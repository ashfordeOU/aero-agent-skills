#!/usr/bin/env python3
"""Bonded attachments examined for full cure and for any remaining tackiness.

Anchor: ECSS-E-ST-20-08C clause 5.5.3.2.16. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

An attachment bonded to a solar-array panel -- a cable clip, a bracket,
a tie-down, a thermistor pad -- is held by an adhesive that has to have
finished curing. Two independent things say whether it has:

    the schedule    what the thermal profile the part actually saw adds
                    up to, expressed as equivalent minutes at the
                    adhesive's reference temperature
    the surface     whether the adhesive is still tacky when it is
                    touched at inspection

The first is a prediction from recorded temperatures and the second is
an observation of the part in front of the inspector, and where they
disagree the observation governs. Remaining tackiness means unreacted
adhesive: it outgasses, it picks up contamination and it has not
developed its strength, so it takes the attachment out regardless of
what the cure profile accumulated. A profile that falls short while the
surface is tack-free is the opposite case and is not a pass either,
because the surface skins over before the bond line finishes.

The cure accumulation weights each segment of the recorded profile by
its temperature, in the Arrhenius sense, and credits nothing to time
spent below the temperature at which the adhesive advances at all.

Dispositions are accept, rework -- meaning return the part to cure --
and reject. The allowance set below is a declared project allowance
set, not a physical constant; a project may substitute its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ACCEPT = "accept"
REWORK = "rework"
REJECT = "reject"
ATTACHMENT_DISPOSITIONS = (ACCEPT, REWORK, REJECT)

INSPECTION_INCOMPLETE = "inspection-incomplete"

TACK_FREE = "tack-free"
TACK_MARGINAL = "marginal"
TACKY = "tacky"
TACK_NOT_TESTED = "not-tested"
TACK_STATES = (TACK_FREE, TACK_MARGINAL, TACKY, TACK_NOT_TESTED)

_SEVERITY_ORDER = {ACCEPT: 0, REWORK: 1, REJECT: 2}

ABSOLUTE_ZERO_C = -273.15

DEFAULT_CURE_ALLOWANCES = {
    "min_cure_ratio": 1.0,
    "review_cure_ratio": 0.95,
    "min_fillet_coverage": 0.90,
    "max_void_fraction": 0.05,
    "max_affected_attachment_fraction": 0.05,
    "rework_margin_factor": 2.0,
}

_REL_TOL = 1e-9
_ABS_TOL = 1e-12


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


def _require_fraction(name, value):
    number = _require_number(name, value)
    if number < 0.0 or number > 1.0:
        raise ValueError("%s must lie between zero and one, got %r" % (name, value))
    return number


def _require_temperature(name, value):
    number = _require_number(name, value)
    if number <= ABSOLUTE_ZERO_C:
        raise ValueError(
            "%s must be above absolute zero, got %r degrees Celsius" % (name, value)
        )
    return number


def _require_text(name, value):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("%s must be a non-empty string, got %r" % (name, value))
    return value


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error.

    A cure ratio is a sum of exponentially weighted segment times
    divided by a reference dwell, and an allowance is a product of a
    declared fraction and a counted population, so a value that should
    land exactly on its limit can evaluate a few units in the last place
    past it -- and the exponential is not correctly rounded, so it lands
    differently on different machines. The limit is never moved; only
    the comparison tolerates the representation error.
    """
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_least(value, limit):
    """value >= limit under the same representation tolerance."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _worst(dispositions):
    worst = ACCEPT
    for disposition in dispositions:
        if _SEVERITY_ORDER[disposition] > _SEVERITY_ORDER[worst]:
            worst = disposition
    return worst


def validate_cure_allowances(allowances):
    """Check a cure allowance set is complete and self-consistent."""
    if not isinstance(allowances, dict):
        raise ValueError("allowances must be a mapping, got %r" % (allowances,))
    for key in (
        "min_fillet_coverage",
        "max_void_fraction",
        "max_affected_attachment_fraction",
    ):
        _require_fraction("allowances %s" % key, allowances.get(key))
    minimum = _require_positive(
        "allowances min_cure_ratio", allowances.get("min_cure_ratio")
    )
    review = _require_positive(
        "allowances review_cure_ratio", allowances.get("review_cure_ratio")
    )
    factor = allowances.get("rework_margin_factor")
    if not _is_finite_number(factor) or factor < 1.0:
        raise ValueError(
            "allowances rework_margin_factor must be at least one, got %r" % (factor,)
        )
    if review > minimum:
        raise ValueError(
            "allowances put the review cure ratio above the ratio that counts as "
            "cured, which leaves no band in which a short cure can be returned "
            "to the oven rather than scrapped"
        )
    return allowances


def validate_cure_schedule(schedule):
    """Check the adhesive cure schedule the accumulation is taken against."""
    if not isinstance(schedule, dict):
        raise ValueError("schedule must be a mapping, got %r" % (schedule,))
    _require_text("adhesive_id", schedule.get("adhesive_id"))
    reference = _require_temperature(
        "reference_temperature_c", schedule.get("reference_temperature_c")
    )
    _require_positive(
        "reference_dwell_minutes", schedule.get("reference_dwell_minutes")
    )
    _require_positive(
        "activation_temperature_k", schedule.get("activation_temperature_k")
    )
    floor = _require_temperature(
        "minimum_cure_temperature_c", schedule.get("minimum_cure_temperature_c")
    )
    ceiling = _require_temperature(
        "max_temperature_c", schedule.get("max_temperature_c")
    )
    if floor >= reference:
        raise ValueError(
            "the temperature below which the adhesive does not advance (%r C) is "
            "at or above its reference cure temperature (%r C)" % (floor, reference)
        )
    if ceiling <= reference:
        raise ValueError(
            "the adhesive damage temperature (%r C) is at or below its reference "
            "cure temperature (%r C)" % (ceiling, reference)
        )
    return schedule


def cure_acceleration(temperature_c, schedule):
    """How fast the adhesive advances at one temperature, against reference.

    One at the reference temperature, above one when hotter, below one
    when cooler, and zero below the temperature at which the adhesive
    does not advance at all.
    """
    validate_cure_schedule(schedule)
    temperature = _require_temperature("temperature_c", temperature_c)
    if temperature < schedule["minimum_cure_temperature_c"]:
        return 0.0
    reference_k = schedule["reference_temperature_c"] - ABSOLUTE_ZERO_C
    temperature_k = temperature - ABSOLUTE_ZERO_C
    return math.exp(
        schedule["activation_temperature_k"]
        * (1.0 / reference_k - 1.0 / temperature_k)
    )


def equivalent_cure_minutes(profile, schedule):
    """Recorded profile reduced to equivalent minutes at the reference.

    Each segment contributes its own duration weighted by how fast the
    adhesive advances at that segment's temperature. Time below the
    adhesive's floor contributes nothing rather than a little, because
    an unheated part does not creep towards cured by sitting there.
    """
    validate_cure_schedule(schedule)
    if not isinstance(profile, (list, tuple)) or not profile:
        raise ValueError(
            "the cure profile must carry at least one segment, got %r" % (profile,)
        )
    equivalent = 0.0
    elapsed = 0.0
    peak = None
    below_floor = 0.0
    for index, segment in enumerate(profile):
        if not isinstance(segment, dict):
            raise ValueError("profile segment %d must be a mapping, got %r" % (index, segment))
        temperature = _require_temperature(
            "temperature_c on profile segment %d" % index, segment.get("temperature_c")
        )
        minutes = _require_positive(
            "minutes on profile segment %d" % index, segment.get("minutes")
        )
        elapsed += minutes
        peak = temperature if peak is None else max(peak, temperature)
        acceleration = cure_acceleration(temperature, schedule)
        if acceleration == 0.0:
            below_floor += minutes
        equivalent += minutes * acceleration
    return {
        "equivalent_minutes": equivalent,
        "elapsed_minutes": elapsed,
        "minutes_below_cure_floor": below_floor,
        "peak_temperature_c": peak,
        "reference_dwell_minutes": schedule["reference_dwell_minutes"],
        "cure_ratio": equivalent / schedule["reference_dwell_minutes"],
        "over_temperature": peak > schedule["max_temperature_c"]
        and not math.isclose(
            peak, schedule["max_temperature_c"], rel_tol=_REL_TOL, abs_tol=_ABS_TOL
        ),
    }


def attachment_cure_state(record, schedule, allowances=DEFAULT_CURE_ALLOWANCES):
    """Cure accumulation and surface condition of one bonded attachment."""
    validate_cure_allowances(allowances)
    validate_cure_schedule(schedule)
    if not isinstance(record, dict):
        raise ValueError("record must be a mapping, got %r" % (record,))
    attachment_id = _require_text("attachment_id", record.get("attachment_id"))
    adhesive = _require_text("adhesive_id on %s" % attachment_id, record.get("adhesive_id"))
    if adhesive != schedule["adhesive_id"]:
        raise ValueError(
            "%s was bonded with adhesive %r while the cure schedule in hand is "
            "for %r; the accumulation would be taken against the wrong kinetics"
            % (attachment_id, adhesive, schedule["adhesive_id"])
        )
    tack = record.get("tack_state", TACK_NOT_TESTED)
    if tack not in TACK_STATES:
        raise ValueError(
            "tack_state on %s must be one of %s, got %r"
            % (attachment_id, ", ".join(TACK_STATES), tack)
        )
    accumulation = equivalent_cure_minutes(record.get("cure_profile"), schedule)
    coverage = _require_fraction(
        "fillet_coverage on %s" % attachment_id, record.get("fillet_coverage", 1.0)
    )
    voids = _require_fraction(
        "void_fraction on %s" % attachment_id, record.get("void_fraction", 0.0)
    )
    state = dict(accumulation)
    state.update(
        {
            "attachment_id": attachment_id,
            "adhesive_id": adhesive,
            "tack_state": tack,
            "tack_tested": tack != TACK_NOT_TESTED,
            "fillet_coverage": coverage,
            "void_fraction": voids,
            "schedule_says_cured": _at_least(
                accumulation["cure_ratio"], allowances["min_cure_ratio"]
            ),
        }
    )
    return state


def assess_attachment(record, schedule, allowances=DEFAULT_CURE_ALLOWANCES):
    """Grade one bonded attachment for full cure and remaining tackiness."""
    validate_cure_allowances(allowances)
    state = attachment_cure_state(record, schedule, allowances)
    attachment_id = state["attachment_id"]
    findings = []
    dispositions = [ACCEPT]
    factor = allowances["rework_margin_factor"]
    ratio = state["cure_ratio"]

    if state["tack_state"] == TACKY:
        dispositions.append(REJECT)
        if state["schedule_says_cured"]:
            findings.append(
                "the adhesive is still tacky although the recorded profile adds "
                "up to %.3f of the reference dwell; the profile is a prediction "
                "and the surface is the observation, so the surface governs"
                % ratio
            )
        else:
            findings.append(
                "the adhesive is still tacky and the recorded profile reached "
                "only %.3f of the reference dwell" % ratio
            )
    elif state["tack_state"] == TACK_MARGINAL:
        dispositions.append(REWORK)
        findings.append(
            "the adhesive is marginally tacky; unreacted adhesive outgasses and "
            "picks up contamination, so the part returns to cure"
        )

    if not state["schedule_says_cured"]:
        if _at_least(ratio, allowances["review_cure_ratio"]):
            dispositions.append(REWORK)
            findings.append(
                "the recorded profile adds up to %.3f of the reference dwell, "
                "short of the %.3f that counts as cured"
                % (ratio, allowances["min_cure_ratio"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "the recorded profile adds up to %.3f of the reference dwell, "
                "under the %.3f review floor"
                % (ratio, allowances["review_cure_ratio"])
            )
        if state["tack_state"] == TACK_FREE:
            findings.append(
                "a tack-free surface over a short profile is not proof of cure; "
                "the surface skins before the bond line finishes"
            )

    if state["over_temperature"]:
        dispositions.append(REJECT)
        findings.append(
            "the profile peaked at %.1f C, over the %.1f C the adhesive tolerates"
            % (state["peak_temperature_c"], schedule["max_temperature_c"])
        )

    if not _at_least(state["fillet_coverage"], allowances["min_fillet_coverage"]):
        if _at_least(
            state["fillet_coverage"], allowances["min_fillet_coverage"] / factor
        ):
            dispositions.append(REWORK)
            findings.append(
                "the fillet covers %.3f of the joint, short of the %.3f the "
                "allowance asks for"
                % (state["fillet_coverage"], allowances["min_fillet_coverage"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "the fillet covers %.3f of the joint, under the %.3f rework floor"
                % (
                    state["fillet_coverage"],
                    allowances["min_fillet_coverage"] / factor,
                )
            )

    if not _at_most(state["void_fraction"], allowances["max_void_fraction"]):
        if _at_most(state["void_fraction"], allowances["max_void_fraction"] * factor):
            dispositions.append(REWORK)
            findings.append(
                "voids take %.3f of the bond area, past the %.3f the allowance "
                "permits" % (state["void_fraction"], allowances["max_void_fraction"])
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "voids take %.3f of the bond area, past the rework margin of %.3f"
                % (
                    state["void_fraction"],
                    allowances["max_void_fraction"] * factor,
                )
            )

    verdict = _worst(dispositions)
    if not state["tack_tested"]:
        findings.append(
            "no tack test is recorded; the clause turns on whether any tackiness "
            "is left, so the attachment is not graded until one is"
        )
    return {
        "attachment_id": attachment_id,
        "verdict": verdict,
        "tack_tested": state["tack_tested"],
        "tack_state": state["tack_state"],
        "cure_ratio": ratio,
        "equivalent_cure_minutes": state["equivalent_minutes"],
        "state": state,
        "findings": findings,
    }


def inspect_attachment_material(
    assembly, schedule, allowances=DEFAULT_CURE_ALLOWANCES
):
    """Clause 5.5.3.2.16 cure and tackiness screen over one assembly."""
    validate_cure_allowances(allowances)
    validate_cure_schedule(schedule)
    if not isinstance(assembly, dict):
        raise ValueError("assembly must be a mapping, got %r" % (assembly,))
    assembly_id = _require_text("assembly_id", assembly.get("assembly_id"))
    declared = assembly.get("declared_attachment_count")
    if not isinstance(declared, int) or isinstance(declared, bool) or declared <= 0:
        raise ValueError(
            "declared_attachment_count must be a positive integer, got %r" % (declared,)
        )
    records = assembly.get("attachments")
    if not isinstance(records, (list, tuple)):
        raise ValueError("attachments must be a list, got %r" % (records,))
    if len(records) > declared:
        raise ValueError(
            "%d attachment records against a declared count of %d on %s"
            % (len(records), declared, assembly_id)
        )

    seen = set()
    screened = []
    for record in records:
        result = assess_attachment(record, schedule, allowances)
        if result["attachment_id"] in seen:
            raise ValueError(
                "duplicate attachment id %r on assembly %s"
                % (result["attachment_id"], assembly_id)
            )
        seen.add(result["attachment_id"])
        screened.append(result)

    inspected = len(screened)
    counts = dict((state, 0) for state in ATTACHMENT_DISPOSITIONS)
    findings = []
    dispositions = [ACCEPT]
    affected = 0
    tacky = 0
    untested = []
    for result in screened:
        counts[result["verdict"]] += 1
        dispositions.append(result["verdict"])
        if result["findings"]:
            affected += 1
        if result["tack_state"] == TACKY:
            tacky += 1
        if not result["tack_tested"]:
            untested.append(result["attachment_id"])
        for finding in result["findings"]:
            findings.append("%s %s" % (result["attachment_id"], finding))

    affected_allowed = allowances["max_affected_attachment_fraction"] * inspected
    factor = allowances["rework_margin_factor"]
    if inspected and not _at_most(affected, affected_allowed):
        if _at_most(affected, affected_allowed * factor):
            dispositions.append(REWORK)
            findings.append(
                "%d of %d bonded attachments carry a finding, past the %.2f the "
                "assembly allowance permits" % (affected, inspected, affected_allowed)
            )
        else:
            dispositions.append(REJECT)
            findings.append(
                "%d of %d bonded attachments carry a finding, past the rework "
                "margin of %.2f" % (affected, inspected, affected_allowed * factor)
            )

    verdict = _worst(dispositions)
    missing = declared - inspected
    complete = missing == 0 and not untested
    if missing:
        findings.append(
            "%d of %d bonded attachments carry no inspection record; an "
            "allowance applied to a short set is applied to the wrong population"
            % (missing, declared)
        )
    if untested:
        findings.append(
            "%d bonded attachments have no tack test; the clause turns on "
            "remaining tackiness, so the assembly stays open" % len(untested)
        )
    if not complete:
        verdict = INSPECTION_INCOMPLETE
    return {
        "assembly_id": assembly_id,
        "adhesive_id": schedule["adhesive_id"],
        "verdict": verdict,
        "inspection_complete": complete,
        "declared_attachment_count": declared,
        "inspected_count": inspected,
        "missing_record_count": missing,
        "untested_attachment_ids": untested,
        "disposition_counts": counts,
        "tacky_count": tacky,
        "affected_count": affected,
        "affected_fraction": affected / float(inspected) if inspected else 0.0,
        "affected_allowance": affected_allowed,
        "remaining_affected_allowance": affected_allowed - affected,
        "not_accepted_ids": [
            result["attachment_id"] for result in screened if result["verdict"] != ACCEPT
        ],
        "attachments": screened,
        "findings": findings,
    }
