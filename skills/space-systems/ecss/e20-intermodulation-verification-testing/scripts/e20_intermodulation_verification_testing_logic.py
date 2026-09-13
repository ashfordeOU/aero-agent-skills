#!/usr/bin/env python3
"""Intermodulation verification testing -- ECSS-E-ST-20C clause 7.4.4.

Deterministic, offline, stdlib-only logic for grading a passive-
intermodulation verification campaign: selecting the order to measure,
checking the two-carrier configuration against the flight carrier-plan,
proving the bench has headroom over the acceptance-level, and turning each
reading plus its uncertainty into a verdict.

Verdicts
--------
pass                -- reading + uncertainty at or below the acceptance-level
uncertainty-limited -- bare reading clears, worst case does not
instrument-limited  -- the bench residual is too close to the limit, or the
                       reading is a residual reading that does not clear it
fail                -- bare reading above the acceptance-level
"""

import math

# Levels are dB sums and power-sums of floats, so an exactly compliant case
# can land a few ULPs above the limit. This tolerance absorbs representation
# error only; it never widens the acceptance-level.
DB_TOL = 1e-9

MIN_ORDER = 3
MIN_CARRIERS = 2
VERDICT_PASS = "pass"
VERDICT_FAIL = "fail"
VERDICT_UNCERTAINTY_LIMITED = "uncertainty-limited"
VERDICT_INSTRUMENT_LIMITED = "instrument-limited"
CAMPAIGN_PASS = "pass"
CAMPAIGN_FAIL = "fail"
CAMPAIGN_INCONCLUSIVE = "inconclusive"


def _is_finite_number(value):
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(value)
    )


def _require_number(value, label):
    if not _is_finite_number(value):
        raise ValueError("%s must be a finite number, got %r" % (label, value))
    return float(value)


def _require_positive(value, label):
    number = _require_number(value, label)
    if number <= 0.0:
        raise ValueError("%s must be > 0, got %r" % (label, value))
    return number


def _require_non_negative(value, label):
    number = _require_number(value, label)
    if number < 0.0:
        raise ValueError("%s must be >= 0, got %r" % (label, value))
    return number


def _le(left, right, tol=DB_TOL):
    """`left <= right`, tolerant of float representation error only."""
    return left <= right or math.isclose(left, right, rel_tol=0.0, abs_tol=tol)


def dbm_to_mw(level_dbm):
    """Convert a dBm level to milliwatts."""
    return 10.0 ** (_require_number(level_dbm, "level_dbm") / 10.0)


def power_sum_dbm(levels_dbm):
    """Power-sum a non-empty sequence of dBm levels (they add as powers)."""
    levels = list(levels_dbm)
    if not levels:
        raise ValueError("levels_dbm must contain at least one level")
    total_mw = sum(
        dbm_to_mw(_require_number(level, "levels_dbm[%d]" % index))
        for index, level in enumerate(levels)
    )
    if total_mw <= 0.0:
        raise ValueError("power-sum collapsed to zero power")
    return 10.0 * math.log10(total_mw)


def select_measured_order(critical_orders):
    """Lowest critical intermodulation-order -- the one to measure."""
    orders = list(critical_orders)
    if not orders:
        raise ValueError(
            "critical_orders is empty: nothing was identified as critical, so "
            "there is no order to verify"
        )
    for index, order in enumerate(orders):
        if isinstance(order, bool) or not isinstance(order, int):
            raise ValueError(
                "critical_orders[%d] must be an int, got %r" % (index, order)
            )
        if order < MIN_ORDER:
            raise ValueError(
                "critical_orders[%d] must be >= %d, got %d" % (index, MIN_ORDER, order)
            )
    return min(orders)


def validate_test_configuration(config):
    """Normalise a two-carrier bench configuration, raising on bad input."""
    if not isinstance(config, dict):
        raise ValueError(
            "test configuration must be a mapping, got %s" % (type(config).__name__,)
        )
    count = config.get("carrier_count")
    if isinstance(count, bool) or not isinstance(count, int):
        raise ValueError("carrier_count must be an int, got %r" % (count,))
    if count < MIN_CARRIERS:
        raise ValueError(
            "a passive-intermodulation run needs at least %d carriers, got %d"
            % (MIN_CARRIERS, count)
        )
    frequencies = config.get("carrier_frequencies_hz")
    if not isinstance(frequencies, (list, tuple)) or len(frequencies) != count:
        raise ValueError(
            "carrier_frequencies_hz must list exactly %d frequencies" % (count,)
        )
    clean_freqs = [
        _require_positive(f, "carrier_frequencies_hz[%d]" % i)
        for i, f in enumerate(frequencies)
    ]
    if len(set(clean_freqs)) != len(clean_freqs):
        raise ValueError("carrier frequencies must be distinct")
    order = config.get("measured_order")
    if isinstance(order, bool) or not isinstance(order, int) or order < MIN_ORDER:
        raise ValueError(
            "measured_order must be an int >= %d, got %r" % (MIN_ORDER, order)
        )
    return {
        "carrier_count": count,
        "carrier_frequencies_hz": clean_freqs,
        "carrier_power_dbm": _require_number(
            config.get("carrier_power_dbm"), "carrier_power_dbm"
        ),
        "measurement_bandwidth_hz": _require_positive(
            config.get("measurement_bandwidth_hz"), "measurement_bandwidth_hz"
        ),
        "dwell_s": _require_non_negative(config.get("dwell_s", 0.0), "dwell_s"),
        "residual_dbm": _require_number(config.get("residual_dbm"), "residual_dbm"),
        "uncertainty_db": _require_non_negative(
            config.get("uncertainty_db", 0.0), "uncertainty_db"
        ),
        "measured_order": order,
    }


def check_configuration_against_flight(
    config, flight_plan, lowest_critical_order, victim_bandwidth_hz=None
):
    """Findings when the bench configuration does not bracket flight."""
    record = validate_test_configuration(config)
    if not isinstance(flight_plan, dict):
        raise ValueError("flight_plan must be a mapping")
    flight_power = _require_number(
        flight_plan.get("carrier_power_dbm"), "flight_plan.carrier_power_dbm"
    )
    flight_count = flight_plan.get("carrier_count")
    if isinstance(flight_count, bool) or not isinstance(flight_count, int):
        raise ValueError("flight_plan.carrier_count must be an int, got %r" % (flight_count,))
    findings = []
    if not _le(flight_power, record["carrier_power_dbm"]):
        findings.append(
            "test per-carrier-power %.3f dBm is below the flight %.3f dBm"
            % (record["carrier_power_dbm"], flight_power)
        )
    if record["carrier_count"] < flight_count:
        findings.append(
            "test carrier count %d is below the flight %d"
            % (record["carrier_count"], flight_count)
        )
    if record["measured_order"] != lowest_critical_order:
        findings.append(
            "measured order %d is not the lowest critical order %d"
            % (record["measured_order"], lowest_critical_order)
        )
    if victim_bandwidth_hz is not None:
        width = _require_positive(victim_bandwidth_hz, "victim_bandwidth_hz")
        if not _le(record["measurement_bandwidth_hz"], width):
            findings.append(
                "measurement-bandwidth %.6g Hz is wider than the victim band %.6g Hz"
                % (record["measurement_bandwidth_hz"], width)
            )
    return findings


def residual_headroom_db(acceptance_dbm, residual_dbm):
    """How far the bench residual sits below the acceptance-level."""
    acceptance = _require_number(acceptance_dbm, "acceptance_dbm")
    residual = _require_number(residual_dbm, "residual_dbm")
    return acceptance - residual


def measurement_is_capable(acceptance_dbm, residual_dbm, required_headroom_db):
    """True when the bench residual clears the limit by the required headroom."""
    required = _require_non_negative(required_headroom_db, "required_headroom_db")
    return _le(required, residual_headroom_db(acceptance_dbm, residual_dbm))


def worst_case_level_dbm(reading_dbm, uncertainty_db):
    """Reading raised by its measurement-uncertainty."""
    reading = _require_number(reading_dbm, "reading_dbm")
    uncertainty = _require_non_negative(uncertainty_db, "uncertainty_db")
    return reading + uncertainty


def evaluate_reading(
    reading_dbm, uncertainty_db, acceptance_dbm, residual_dbm, required_headroom_db
):
    """Categorize one reading against the agreed acceptance-level."""
    acceptance = _require_number(acceptance_dbm, "acceptance_dbm")
    reading = _require_number(reading_dbm, "reading_dbm")
    residual = _require_number(residual_dbm, "residual_dbm")
    worst_case = worst_case_level_dbm(reading, uncertainty_db)
    headroom = residual_headroom_db(acceptance, residual)
    capable = measurement_is_capable(acceptance, residual, required_headroom_db)
    at_residual = _le(reading, residual)
    if not capable:
        verdict = VERDICT_INSTRUMENT_LIMITED
        note = "bench residual clears the limit by only %.3f dB" % headroom
    elif at_residual:
        verdict = VERDICT_PASS
        note = "reading is at the bench residual; the unit is bounded there"
    elif _le(worst_case, acceptance):
        verdict = VERDICT_PASS
        note = "worst case %.3f dBm is within the limit" % worst_case
    elif _le(reading, acceptance):
        verdict = VERDICT_UNCERTAINTY_LIMITED
        note = "reading clears but the worst case %.3f dBm does not" % worst_case
    else:
        verdict = VERDICT_FAIL
        note = "reading exceeds the limit by %.3f dB" % (reading - acceptance)
    return {
        "reading_dbm": reading,
        "worst_case_dbm": worst_case,
        "acceptance_dbm": acceptance,
        "headroom_db": headroom,
        "capable": capable,
        "at_residual": at_residual,
        "verdict": verdict,
        "note": note,
    }


def evaluate_campaign(
    runs, acceptance_dbm, required_headroom_db, critical_orders, flight_plan=None,
    victim_bandwidth_hz=None,
):
    """Grade a whole clause 7.4.4 campaign for one victim band.

    Each run is a mapping carrying its bench configuration keys plus the
    measured `reading_dbm`. Returns the per-run verdicts, the power-summed
    aggregate for the band, any configuration findings and the campaign
    verdict.
    """
    run_list = list(runs)
    if not run_list:
        raise ValueError("runs must contain at least one measurement run")
    lowest_order = select_measured_order(critical_orders)
    acceptance = _require_number(acceptance_dbm, "acceptance_dbm")
    results = []
    findings = []
    readings = []
    measured_orders = set()
    for index, run in enumerate(run_list):
        if not isinstance(run, dict):
            raise ValueError("runs[%d] must be a mapping" % index)
        config = validate_test_configuration(run)
        reading = _require_number(run.get("reading_dbm"), "runs[%d].reading_dbm" % index)
        outcome = evaluate_reading(
            reading,
            config["uncertainty_db"],
            acceptance,
            config["residual_dbm"],
            required_headroom_db,
        )
        outcome["measured_order"] = config["measured_order"]
        outcome["index"] = index
        measured_orders.add(config["measured_order"])
        readings.append(reading)
        results.append(outcome)
        if flight_plan is not None:
            for finding in check_configuration_against_flight(
                run, flight_plan, lowest_order, victim_bandwidth_hz
            ):
                findings.append("run %d: %s" % (index, finding))
    if lowest_order not in measured_orders:
        findings.append(
            "the lowest critical order %d was never measured" % lowest_order
        )
    aggregate_dbm = power_sum_dbm(readings)
    aggregate_worst_case = aggregate_dbm + max(
        validate_test_configuration(run)["uncertainty_db"] for run in run_list
    )
    # A bare aggregate above the limit is a demonstrated exceedance; one that
    # only the uncertainty pushes over is an uncertainty-limited aggregate,
    # which withholds the pass without condemning the unit.
    aggregate_exceeds = not _le(aggregate_dbm, acceptance)
    aggregate_uncertainty_limited = not aggregate_exceeds and not _le(
        aggregate_worst_case, acceptance
    )
    if any(r["verdict"] == VERDICT_FAIL for r in results) or aggregate_exceeds:
        verdict = CAMPAIGN_FAIL
    elif findings or aggregate_uncertainty_limited or any(
        r["verdict"] in (VERDICT_UNCERTAINTY_LIMITED, VERDICT_INSTRUMENT_LIMITED)
        for r in results
    ):
        verdict = CAMPAIGN_INCONCLUSIVE
    else:
        verdict = CAMPAIGN_PASS
    return {
        "lowest_critical_order": lowest_order,
        "runs": results,
        "aggregate_dbm": aggregate_dbm,
        "aggregate_worst_case_dbm": aggregate_worst_case,
        "aggregate_exceeds": aggregate_exceeds,
        "aggregate_uncertainty_limited": aggregate_uncertainty_limited,
        "findings": findings,
        "verdict": verdict,
        "verified": verdict == CAMPAIGN_PASS,
    }
