#!/usr/bin/env python3
"""Protection diode test -- general provisions.

Anchor: ECSS-E-ST-20-08C clause 9.6.1. The procedure below is a
paraphrase into implementable steps; no standard text is reproduced.

The clause does not hand anybody a spike level. It says the electrical
spike levels a protection diode is required to withstand are settled
between the customer and the supplier and are then written into the
control drawing. That makes this a provenance job before it is ever a
measurement job, and it is the provenance half that gets skipped.

Two parties have to have accepted the level. A figure the supplier
proposed and the customer never came back on is not an agreed level,
and neither is a customer instruction the supplier never confirmed it
can build to. Either way there is nothing to test against and nothing
to sentence.

The capture is the second half and it is the one that actually fails.
A level can be agreed in a meeting, in a minute, in an e-mail, and
never reach the drawing the part is bought and inspected against. A
drawing that carries no spike level at all leaves the allowance
unestablished however firm the agreement was. A drawing carrying a
different figure is worse: it is a live document contradicting the
agreement, and whichever one is wrong, parts are being accepted against
it. And a drawing issued before the agreement was reached cannot
contain what was agreed afterwards, so a matching figure on an earlier
issue is a coincidence to be checked rather than a capture.

Only once a level is agreed and captured does the bench matter. A spike
is an amplitude held for a duration, so the stress it imposes is the
product, and comparing amplitudes alone lets a short pulse at the right
volts stand in for the agreed stress. A bench that applied less than
the captured level has not shown the diode withstands it; a bench that
applied substantially more has stressed a flight part past what was
bought and the overstress needs dispositioning, not quiet acceptance.
A spike of the wrong polarity says nothing about the allowance at all.

The criteria set below is a declared project criteria set, not a
physical constant; a project substitutes its own.

Standard library only, offline, deterministic.
"""

from __future__ import annotations

import math

FORWARD = "forward"
REVERSE = "reverse"
SPIKE_POLARITIES = (FORWARD, REVERSE)

AGREED = "agreed"
CUSTOMER_ONLY = "customer-only"
SUPPLIER_ONLY = "supplier-only"
UNAGREED = "unagreed"
AGREEMENT_STATES = (AGREED, CUSTOMER_ONLY, SUPPLIER_ONLY, UNAGREED)

CAPTURED = "captured"
CAPTURE_MISSING = "capture-missing"
CAPTURE_CONTRADICTED = "capture-contradicted"
CAPTURE_STALE = "capture-stale"
CAPTURE_STATES = (
    CAPTURED,
    CAPTURE_MISSING,
    CAPTURE_CONTRADICTED,
    CAPTURE_STALE,
)

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

DEFAULT_SPIKE_TEST_CRITERIA = {
    "min_applied_stress_fraction": 1.0,
    "max_applied_stress_fraction": 1.2,
    "capture_tolerance_fraction": 0.02,
    "max_drawing_lead_days": 0,
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
    if number <= 0.0:
        raise ValueError("%s must be greater than zero, got %r" % (name, value))
    return number


def _require_count(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError("%s must be an integer, got %r" % (name, value))
    if value < 0:
        raise ValueError("%s must not be negative, got %r" % (name, value))
    return value


def _require_day(name, value):
    if not isinstance(value, int) or isinstance(value, bool):
        raise ValueError(
            "%s must be an integer day index on the project calendar, got %r"
            % (name, value)
        )
    return value


def _require_flag(name, value):
    if not isinstance(value, bool):
        raise ValueError("%s must be true or false, got %r" % (name, value))
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


def validate_spike_test_criteria(criteria):
    """Check a criteria set is complete and internally sensible."""
    if not isinstance(criteria, dict):
        raise ValueError("criteria must be a mapping, got %r" % (criteria,))
    low = _require_fraction(
        "min_applied_stress_fraction", criteria.get("min_applied_stress_fraction")
    )
    high = _require_fraction(
        "max_applied_stress_fraction", criteria.get("max_applied_stress_fraction")
    )
    if high < low:
        raise ValueError(
            "max_applied_stress_fraction must not sit below "
            "min_applied_stress_fraction"
        )
    _require_fraction(
        "capture_tolerance_fraction", criteria.get("capture_tolerance_fraction")
    )
    _require_count("max_drawing_lead_days", criteria.get("max_drawing_lead_days"))
    return criteria


def validate_spike_level(level):
    """Normalise one spike level record."""
    if not isinstance(level, dict):
        raise ValueError("spike level must be a mapping, got %r" % (level,))
    polarity = level.get("polarity")
    if polarity not in SPIKE_POLARITIES:
        raise ValueError(
            "spike polarity must be one of %s, got %r"
            % (", ".join(SPIKE_POLARITIES), polarity)
        )
    return {
        "polarity": polarity,
        "amplitude_v": _require_positive(
            "spike amplitude_v", level.get("amplitude_v")
        ),
        "duration_us": _require_positive(
            "spike duration_us", level.get("duration_us")
        ),
        "repetitions": _require_count("spike repetitions", level.get("repetitions")),
        "survived": _require_flag("survived", level.get("survived", True)),
    }


def spike_stress_v_us(level):
    """Amplitude-duration product of one spike, in volt-microseconds.

    Comparing amplitudes alone lets a short pulse at the right volts
    stand in for the agreed stress, which is why the product is the
    quantity carried forward.
    """
    normalised = validate_spike_level(level)
    return normalised["amplitude_v"] * normalised["duration_us"]


def validate_spike_agreement(agreement):
    """Normalise the negotiated allowance and who accepted it."""
    if not isinstance(agreement, dict):
        raise ValueError("agreement must be a mapping, got %r" % (agreement,))
    return {
        "level": validate_spike_level(agreement.get("level")),
        "customer_accepted": _require_flag(
            "customer_accepted", agreement.get("customer_accepted")
        ),
        "supplier_accepted": _require_flag(
            "supplier_accepted", agreement.get("supplier_accepted")
        ),
        "agreed_on_day": _require_day("agreed_on_day", agreement.get("agreed_on_day")),
    }


def agreement_state(agreement):
    """Whether both parties, one party or neither accepted the level."""
    record = validate_spike_agreement(agreement)
    if record["customer_accepted"] and record["supplier_accepted"]:
        return AGREED
    if record["customer_accepted"]:
        return CUSTOMER_ONLY
    if record["supplier_accepted"]:
        return SUPPLIER_ONLY
    return UNAGREED


def validate_control_drawing(drawing):
    """Normalise the control drawing the allowance is supposed to reach."""
    if not isinstance(drawing, dict):
        raise ValueError("control drawing must be a mapping, got %r" % (drawing,))
    identifier = _require_label("control drawing id", drawing.get("id"))
    if not identifier:
        raise ValueError("control drawing id must not be blank")
    level = drawing.get("spike_level")
    return {
        "id": identifier,
        "issue": _require_label("control drawing issue", drawing.get("issue", "-")),
        "issue_day": _require_day("issue_day", drawing.get("issue_day")),
        "spike_level": None if level is None else validate_spike_level(level),
    }


def levels_match(left, right, tolerance_fraction):
    """Whether a drawing level carries the agreed one within tolerance."""
    first = validate_spike_level(left)
    second = validate_spike_level(right)
    tolerance = _require_fraction("capture_tolerance_fraction", tolerance_fraction)
    if first["polarity"] != second["polarity"]:
        return False
    if first["repetitions"] != second["repetitions"]:
        return False
    for field in ("amplitude_v", "duration_us"):
        reference = second[field]
        drift = abs(first[field] - reference) / reference
        if not _at_most(drift, tolerance):
            return False
    return True


def capture_state(agreement, drawing, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """Whether the agreed level actually reached the control drawing."""
    validate_spike_test_criteria(criteria)
    record = validate_spike_agreement(agreement)
    sheet = validate_control_drawing(drawing)
    if sheet["spike_level"] is None:
        return CAPTURE_MISSING
    if not levels_match(
        sheet["spike_level"], record["level"], criteria["capture_tolerance_fraction"]
    ):
        return CAPTURE_CONTRADICTED
    lead = record["agreed_on_day"] - sheet["issue_day"]
    if lead > criteria["max_drawing_lead_days"]:
        return CAPTURE_STALE
    return CAPTURED


def assess_spike_allowance(agreement, drawing, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """Disposition the allowance itself, before any bench result."""
    validate_spike_test_criteria(criteria)
    sheet = validate_control_drawing(drawing)
    state = agreement_state(agreement)
    if state != AGREED:
        return (
            NOT_ESTABLISHED,
            "the spike level stands at %s; a level one party has not accepted is "
            "not a level, so there is nothing to test the diode against" % state,
        )
    capture = capture_state(agreement, drawing, criteria)
    if capture == CAPTURE_MISSING:
        return (
            NOT_ESTABLISHED,
            "drawing %s issue %s records no spike level; the allowance was "
            "negotiated and never captured, so parts are bought against a sheet "
            "that does not carry it" % (sheet["id"], sheet["issue"]),
        )
    if capture == CAPTURE_CONTRADICTED:
        return (
            REJECT,
            "drawing %s issue %s carries a spike level the agreement does not; "
            "a live sheet contradicting the agreement is accepting parts against "
            "one of the two figures and nobody has said which"
            % (sheet["id"], sheet["issue"]),
        )
    if capture == CAPTURE_STALE:
        return (
            REFER_FOR_REVIEW,
            "drawing %s issue %s was issued before the level was agreed, so it "
            "cannot contain what was agreed afterwards; the matching figure has "
            "to be traced to a later issue" % (sheet["id"], sheet["issue"]),
        )
    return (
        ACCEPT,
        "the spike level is accepted by both parties and captured on drawing %s "
        "issue %s" % (sheet["id"], sheet["issue"]),
    )


def captured_spike_level(agreement, drawing, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """The level a bench may be sentenced against, or None if there is none."""
    disposition, _reason = assess_spike_allowance(agreement, drawing, criteria)
    if disposition in (NOT_ESTABLISHED, REJECT):
        return None
    return validate_control_drawing(drawing)["spike_level"]


def applied_stress_fraction(applied, level):
    """Bench stress as a fraction of the level it has to demonstrate."""
    return spike_stress_v_us(applied) / spike_stress_v_us(level)


def assess_applied_spike(applied, level, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """Disposition one bench spike against the captured allowance."""
    validate_spike_test_criteria(criteria)
    bench = validate_spike_level(applied)
    target = validate_spike_level(level)
    if bench["polarity"] != target["polarity"]:
        return (
            NOT_ESTABLISHED,
            "a %s spike says nothing about a %s allowance"
            % (bench["polarity"], target["polarity"]),
        )
    if not bench["survived"]:
        return (
            REJECT,
            "the diode did not survive a %s spike of %.4g V held %.4g us; the "
            "allowance is exactly what it was required to withstand"
            % (bench["polarity"], bench["amplitude_v"], bench["duration_us"]),
        )
    if bench["repetitions"] < target["repetitions"]:
        return (
            NOT_ESTABLISHED,
            "%d spikes applied against the %d the allowance names; the diode has "
            "not seen the duty it is required to withstand"
            % (bench["repetitions"], target["repetitions"]),
        )
    fraction = applied_stress_fraction(applied, level)
    if not _at_least(fraction, criteria["min_applied_stress_fraction"]):
        return (
            NOT_ESTABLISHED,
            "the bench applied %.1f per cent of the captured stress; an "
            "under-stressed diode has demonstrated nothing" % (fraction * 100.0),
        )
    if not _at_most(fraction, criteria["max_applied_stress_fraction"]):
        return (
            REFER_FOR_REVIEW,
            "the bench applied %.1f per cent of the captured stress, past the "
            "%.1f per cent the criteria allow; a flight part has been stressed "
            "beyond what was bought"
            % (fraction * 100.0, criteria["max_applied_stress_fraction"] * 100.0),
        )
    return (
        ACCEPT,
        "the bench applied %.1f per cent of the captured stress at the right "
        "polarity" % (fraction * 100.0),
    )


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


def assess_protection_diode_test_general(case, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """Clause 9.6.1 screen for one protection diode type."""
    validate_spike_test_criteria(criteria)
    if not isinstance(case, dict):
        raise ValueError("case must be a mapping, got %r" % (case,))
    agreement = case.get("agreement")
    drawing = case.get("control_drawing")
    if agreement is None or drawing is None:
        raise ValueError(
            "a case must carry both an agreement and a control_drawing; the "
            "clause is about the two of them together"
        )
    spikes = case.get("applied_spikes", [])
    if not isinstance(spikes, (list, tuple)):
        raise ValueError("case must record applied_spikes as a sequence")

    allowance, allowance_reason = assess_spike_allowance(agreement, drawing, criteria)
    findings = []
    advisories = []
    dispositions = [allowance]
    if allowance != ACCEPT:
        findings.append(allowance_reason)

    level = captured_spike_level(agreement, drawing, criteria)
    sentenced = 0
    not_accepted = []
    for index, applied in enumerate(spikes):
        if level is None:
            validate_spike_level(applied)
            advisories.append(
                "bench spike %d cannot be sentenced while the allowance is not "
                "established; there is no captured level to compare it with"
                % index
            )
            continue
        disposition, reason = assess_applied_spike(applied, level, criteria)
        sentenced += 1
        dispositions.append(disposition)
        if disposition != ACCEPT:
            not_accepted.append(index)
            findings.append("bench spike %d: %s" % (index, reason))

    return {
        "diode_id": _require_label("diode id", case.get("id", "unnamed-diode")),
        "verdict": worst_disposition(dispositions),
        "agreement_state": agreement_state(agreement),
        "capture_state": capture_state(agreement, drawing, criteria),
        "allowance_disposition": allowance,
        "captured_stress_v_us": None if level is None else spike_stress_v_us(level),
        "spikes_sentenced": sentenced,
        "spikes_not_accepted": tuple(not_accepted),
        "findings": findings,
        "advisories": advisories,
    }


def assess_diode_spike_programme(cases, criteria=DEFAULT_SPIKE_TEST_CRITERIA):
    """Roll the clause 9.6.1 screen up over every protection diode type."""
    validate_spike_test_criteria(criteria)
    if not isinstance(cases, (list, tuple)):
        raise ValueError("cases must be a sequence of diode records")
    if not cases:
        raise ValueError(
            "a programme with no protection diode declared cannot be screened "
            "against a clause about protection diodes"
        )
    results = []
    seen = set()
    for case in cases:
        result = assess_protection_diode_test_general(case, criteria)
        if result["diode_id"] in seen:
            raise ValueError("duplicate diode id %r" % result["diode_id"])
        seen.add(result["diode_id"])
        results.append(result)
    return {
        "verdict": worst_disposition([r["verdict"] for r in results]),
        "diodes_assessed": len(results),
        "diodes_without_a_captured_level": tuple(
            r["diode_id"] for r in results if r["captured_stress_v_us"] is None
        ),
        "diodes_not_accepted": tuple(
            r["diode_id"] for r in results if r["verdict"] != ACCEPT
        ),
        "diode_results": tuple(results),
    }
