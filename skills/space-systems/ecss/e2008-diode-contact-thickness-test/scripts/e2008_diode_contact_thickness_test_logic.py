#!/usr/bin/env python3
"""Acceptance record of protection diode contact metallisation thickness.

Anchor: ECSS-E-ST-20-08C clause 9.6.8. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

This is the acceptance clause, and acceptance clauses are about the
record as much as the number. The thickness present on each protection
diode contact has to be measured and written down, and a figure written
down without the three things that make it a measurement is a number
rather than evidence.

The first is that the gauge has to be able to split the band it is
sentencing against. A specification band six micrometres wide read by
an instrument whose step is two micrometres cannot tell a part near the
floor from a part under it; every reading it returns is honest and none
of them discriminates. So the resolution is compared against the band
before the reading is compared against anything, and a gauge too coarse
for the band closes the record as not established rather than passing
or failing the part.

The second is that a calibration has a date on it. A reading taken
after the gauge's calibration lapsed is not a bad reading -- it is a
reading of unknown bias, which is worse, because it looks exactly like
a good one in the record. That is a not-established outcome too: the
part is unsentenced and goes back to a calibrated gauge, and calling it
a reject scraps parts that were probably fine.

The third is repeatability. A single reading cannot show that the
surface, the fixture and the operator agree, so the clause is worked
with replicates, and the spread of the replicates is checked before
their mean is used. Replicates that disagree past the repeatability
limit mean the mean describes nothing, and averaging them anyway
produces a confident figure out of an unrepeatable one.

Sentencing is then asymmetric on purpose. Under the floor the
metallisation is not there to be welded and the contact is rejected.
Over the ceiling the metal is present in excess, which is a different
problem -- stress, weld parameter drift, a plating bath running long --
and it goes to review rather than to scrap.

The figure that goes into the record is quantised to the gauge step.
Quoting a mean of replicates to more digits than the instrument can
resolve writes a precision into the record that the gauge never had,
and the record is what somebody reads years later.

Finally the lot. Acceptance runs on a declared sample, and a polarity
or a device carrying no record is unsentenced rather than passed: a
diode accepted on its anode figure while nobody measured the cathode
has been shown half of what the clause asks for.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

ANODE = "anode"
CATHODE = "cathode"
CONTACT_POLARITIES = (ANODE, CATHODE)

ACCEPT = "accept"
REFER_FOR_REVIEW = "refer-for-review"
NOT_ESTABLISHED = "not-established"
REJECT = "reject"
DISPOSITIONS = (ACCEPT, REFER_FOR_REVIEW, NOT_ESTABLISHED, REJECT)

_SEVERITY_ORDER = {
    ACCEPT: 0,
    REFER_FOR_REVIEW: 1,
    NOT_ESTABLISHED: 2,
    REJECT: 3,
}

DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA = {
    "min_thickness_um": 4.0,
    "max_thickness_um": 10.0,
    "max_gauge_resolution_fraction": 0.10,
    "min_replicates": 3,
    "max_replicate_spread_um": 0.6,
    "min_acceptance_sample": 5,
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
    if number <= 0.0 or number > 1.0:
        raise ValueError("%s must fall in the interval (0, 1], got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_label(name, value):
    if not isinstance(value, str):
        raise ValueError("%s must be a string, got %r" % (name, value))
    return value.strip()


def _at_least(value, limit):
    """value >= limit, absorbing floating-point representation error."""
    return value >= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def _at_most(value, limit):
    """value <= limit, absorbing floating-point representation error."""
    return value <= limit or math.isclose(
        value, limit, rel_tol=_REL_TOL, abs_tol=_ABS_TOL
    )


def validate_thickness_acceptance_criteria(criteria):
    """Check an acceptance criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    floor = _require_positive("min_thickness_um", criteria.get("min_thickness_um"))
    ceiling = _require_positive("max_thickness_um", criteria.get("max_thickness_um"))
    if _at_most(ceiling, floor):
        raise ValueError(
            "max_thickness_um must sit above min_thickness_um; a band with no "
            "width admits no deposit and cannot be measured against"
        )
    _require_fraction(
        "max_gauge_resolution_fraction",
        criteria.get("max_gauge_resolution_fraction"),
    )
    replicates = _require_count("min_replicates", criteria.get("min_replicates"))
    if replicates < 2:
        raise ValueError(
            "min_replicates must be at least 2; a single reading cannot show "
            "the measurement repeats"
        )
    _require_positive(
        "max_replicate_spread_um", criteria.get("max_replicate_spread_um")
    )
    _require_count("min_acceptance_sample", criteria.get("min_acceptance_sample"))
    return criteria


def specification_band_um(criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA):
    """Width of the band the gauge has to be able to split."""
    validate_thickness_acceptance_criteria(criteria)
    return criteria["max_thickness_um"] - criteria["min_thickness_um"]


def validate_gauge(gauge):
    """Normalise the instrument a thickness reading was taken with."""
    if not isinstance(gauge, dict):
        raise ValueError("gauge must be a mapping, got %r" % (gauge,))
    identifier = _require_label("gauge id", gauge.get("id"))
    if not identifier:
        raise ValueError("gauge id must not be blank")
    return {
        "id": identifier,
        "resolution_um": _require_positive(
            "gauge resolution_um", gauge.get("resolution_um")
        ),
        "calibration_valid_to_day": _require_count(
            "calibration_valid_to_day", gauge.get("calibration_valid_to_day")
        ),
    }


def gauge_resolves_the_band(gauge, criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA):
    """Whether the instrument step is fine enough to split the band."""
    instrument = validate_gauge(gauge)
    allowance = (
        specification_band_um(criteria) * criteria["max_gauge_resolution_fraction"]
    )
    return _at_most(instrument["resolution_um"], allowance)


def calibration_is_current(measurement):
    """Whether the gauge calibration still stood on the measurement day."""
    record = validate_thickness_measurement(measurement)
    return record["measured_on_day"] <= record["gauge"]["calibration_valid_to_day"]


def validate_thickness_measurement(measurement):
    """Normalise one thickness measurement: gauge, day and replicates."""
    if not isinstance(measurement, dict):
        raise ValueError("measurement must be a mapping, got %r" % (measurement,))
    replicates = measurement.get("replicates")
    if not isinstance(replicates, (list, tuple)):
        raise ValueError("measurement must record replicates as a sequence")
    if not replicates:
        raise ValueError(
            "a measurement with no replicate recorded is not a measurement"
        )
    return {
        "gauge": validate_gauge(measurement.get("gauge")),
        "measured_on_day": _require_count(
            "measured_on_day", measurement.get("measured_on_day")
        ),
        "replicates": tuple(
            _require_positive("replicate thickness_um", value) for value in replicates
        ),
    }


def mean_replicate_um(replicates):
    """Arithmetic mean of the replicate readings."""
    if not isinstance(replicates, (list, tuple)):
        raise ValueError("replicates must be a sequence")
    values = [_require_positive("replicate thickness_um", v) for v in replicates]
    if not values:
        raise ValueError("no replicate to take a mean of")
    return sum(values) / len(values)


def replicate_spread_um(replicates):
    """Widest disagreement between the replicate readings."""
    if not isinstance(replicates, (list, tuple)):
        raise ValueError("replicates must be a sequence")
    values = [_require_positive("replicate thickness_um", v) for v in replicates]
    if not values:
        raise ValueError("no replicate to take a spread of")
    return max(values) - min(values)


def quantize_to_resolution(value_um, resolution_um):
    """The figure the record carries: no finer than the gauge can resolve."""
    value = _require_positive("value_um", value_um)
    step = _require_positive("resolution_um", resolution_um)
    return round(value / step) * step


def worst_disposition(dispositions):
    """The governing disposition of a set; severity, not record order."""
    if not isinstance(dispositions, (list, tuple)):
        raise ValueError("dispositions must be a sequence")
    if not dispositions:
        return ACCEPT
    unknown = [d for d in dispositions if d not in _SEVERITY_ORDER]
    if unknown:
        raise ValueError("unknown disposition %r" % (unknown[0],))
    return max(dispositions, key=lambda d: _SEVERITY_ORDER[d])


def categorize_contact_thickness(
    measurement, criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA
):
    """Disposition one contact measurement: record first, then the figure."""
    validate_thickness_acceptance_criteria(criteria)
    record = validate_thickness_measurement(measurement)
    gauge = record["gauge"]

    if not gauge_resolves_the_band(gauge, criteria):
        allowance = (
            specification_band_um(criteria) * criteria["max_gauge_resolution_fraction"]
        )
        return (
            NOT_ESTABLISHED,
            "gauge %s steps in %.3g um against a %.3g um band, coarser than the "
            "%.3g um the criteria allow; every reading it returns is honest and "
            "none of them splits the band"
            % (
                gauge["id"],
                gauge["resolution_um"],
                specification_band_um(criteria),
                allowance,
            ),
        )
    if record["measured_on_day"] > gauge["calibration_valid_to_day"]:
        return (
            NOT_ESTABLISHED,
            "gauge %s was read on day %d, %d day(s) past its calibration; a "
            "reading of unknown bias looks exactly like a good one in the record"
            % (
                gauge["id"],
                record["measured_on_day"],
                record["measured_on_day"] - gauge["calibration_valid_to_day"],
            ),
        )
    if len(record["replicates"]) < criteria["min_replicates"]:
        return (
            NOT_ESTABLISHED,
            "%d replicate(s) recorded, under the %d the criteria want; one "
            "reading cannot show the surface, the fixture and the operator agree"
            % (len(record["replicates"]), criteria["min_replicates"]),
        )
    spread = replicate_spread_um(record["replicates"])
    if not _at_most(spread, criteria["max_replicate_spread_um"]):
        return (
            NOT_ESTABLISHED,
            "the replicates disagree by %.3g um, past the %.3g um repeatability "
            "limit; their mean is a confident figure taken from an "
            "unrepeatable one"
            % (spread, criteria["max_replicate_spread_um"]),
        )

    thickness = mean_replicate_um(record["replicates"])
    if not _at_least(thickness, criteria["min_thickness_um"]):
        return (
            REJECT,
            "the contact carries %.3g um of metallisation, under the %.3g um "
            "floor; the metal is not there to weld an interconnect onto"
            % (thickness, criteria["min_thickness_um"]),
        )
    if not _at_most(thickness, criteria["max_thickness_um"]):
        return (
            REFER_FOR_REVIEW,
            "the contact carries %.3g um of metallisation, over the %.3g um "
            "ceiling; excess metal is a plating and weld-parameter question "
            "rather than a missing conductor"
            % (thickness, criteria["max_thickness_um"]),
        )
    return (
        ACCEPT,
        "the contact carries %.3g um of metallisation, inside the %.3g to "
        "%.3g um band"
        % (thickness, criteria["min_thickness_um"], criteria["max_thickness_um"]),
    )


def validate_thickness_contact(contact):
    """Normalise one polarity contact and the measurement recorded on it."""
    if not isinstance(contact, dict):
        raise ValueError("contact must be a mapping, got %r" % (contact,))
    identifier = _require_label("contact id", contact.get("id"))
    if not identifier:
        raise ValueError("contact id must not be blank")
    polarity = contact.get("polarity")
    if polarity not in CONTACT_POLARITIES:
        raise ValueError(
            "contact polarity must be one of %s, got %r"
            % (", ".join(CONTACT_POLARITIES), polarity)
        )
    return {
        "id": identifier,
        "polarity": polarity,
        "measurement": validate_thickness_measurement(contact.get("measurement")),
    }


def assess_contact_thickness(
    contact, criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA
):
    """Clause 9.6.8 acceptance record for one polarity contact."""
    validate_thickness_acceptance_criteria(criteria)
    land = validate_thickness_contact(contact)
    record = land["measurement"]
    disposition, reason = categorize_contact_thickness(record, criteria)
    thickness = mean_replicate_um(record["replicates"])
    return {
        "contact_id": land["id"],
        "polarity": land["polarity"],
        "disposition": disposition,
        "reason": reason,
        "gauge_id": record["gauge"]["id"],
        "measured_on_day": record["measured_on_day"],
        "replicates_taken": len(record["replicates"]),
        "replicate_spread_um": replicate_spread_um(record["replicates"]),
        "mean_thickness_um": thickness,
        "recorded_thickness_um": quantize_to_resolution(
            thickness, record["gauge"]["resolution_um"]
        ),
        "gauge_resolves_the_band": gauge_resolves_the_band(record["gauge"], criteria),
        "calibration_current": record["measured_on_day"]
        <= record["gauge"]["calibration_valid_to_day"],
    }


def assess_diode_thickness(case, criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA):
    """Roll the clause 9.6.8 record up over both polarities of one diode."""
    validate_thickness_acceptance_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    contacts = case.get("contacts")
    if not isinstance(contacts, (list, tuple)):
        raise ValueError("case must record contacts as a sequence")
    if not contacts:
        raise ValueError(
            "a diode with no contact declared carries no thickness record at all"
        )

    results = []
    seen = set()
    for contact in contacts:
        result = assess_contact_thickness(contact, criteria)
        if result["contact_id"] in seen:
            raise ValueError(
                "duplicate contact id %r on the diode" % result["contact_id"]
            )
        seen.add(result["contact_id"])
        results.append(result)

    recorded = {result["polarity"] for result in results}
    unrecorded = tuple(p for p in CONTACT_POLARITIES if p not in recorded)

    findings = [
        result["reason"] for result in results if result["disposition"] != ACCEPT
    ]
    dispositions = [result["disposition"] for result in results]
    if unrecorded:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "no thickness record for the %s contact; a diode accepted on one "
            "polarity has been shown half of what the clause asks for"
            % " and ".join(unrecorded)
        )

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "disposition": worst_disposition(dispositions),
        "contacts_recorded": len(results),
        "polarities_without_a_record": unrecorded,
        "thinnest_contact_um": min(result["mean_thickness_um"] for result in results),
        "contacts_not_accepted": tuple(
            result["contact_id"]
            for result in results
            if result["disposition"] != ACCEPT
        ),
        "rollup_findings": findings,
        "contact_results": tuple(results),
    }


def assess_thickness_acceptance_lot(
    lot, criteria=DEFAULT_THICKNESS_ACCEPTANCE_CRITERIA
):
    """Sentence an acceptance run against its declared sample, not its records."""
    validate_thickness_acceptance_criteria(criteria)
    if not isinstance(lot, dict):
        raise ValueError("acceptance lot must be a mapping, got %r" % (lot,))
    declared = _require_count("declared_sample", lot.get("declared_sample"))
    devices = lot.get("devices")
    if not isinstance(devices, (list, tuple)):
        raise ValueError("acceptance lot must record devices as a sequence")

    results = []
    seen = set()
    for device in devices:
        result = assess_diode_thickness(device, criteria)
        if result["diode_id"] in seen:
            raise ValueError("duplicate diode id %r in the run" % result["diode_id"])
        seen.add(result["diode_id"])
        results.append(result)

    findings = []
    dispositions = [result["disposition"] for result in results]
    if declared < criteria["min_acceptance_sample"]:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "the run declares %d device(s), under the %d the acceptance sample "
            "needs; a smaller sample speaks for itself and not for the lot"
            % (declared, criteria["min_acceptance_sample"])
        )
    if len(results) < declared:
        dispositions.append(NOT_ESTABLISHED)
        findings.append(
            "%d of the %d declared devices carry a record; the devices without "
            "one are unsentenced rather than passed"
            % (len(results), declared)
        )

    return {
        "lot_id": _require_label("lot id", lot.get("id", "unnamed-lot")),
        "disposition": worst_disposition(dispositions),
        "declared_sample": declared,
        "devices_recorded": len(results),
        "devices_not_accepted": tuple(
            result["diode_id"]
            for result in results
            if result["disposition"] != ACCEPT
        ),
        "rollup_findings": findings,
        "device_results": tuple(results),
    }
