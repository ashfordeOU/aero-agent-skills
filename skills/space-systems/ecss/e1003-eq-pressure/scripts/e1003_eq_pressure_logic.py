#!/usr/bin/env python3
"""ECSS-E-ST-10-03C clause 5.5.3 equipment structural-integrity-under-
pressure test logic (paraphrase, not copy).

Common-knowledge summary (standards-map.yaml, ecss: gated false): a
pressurized piece of space segment equipment demonstrates structural
integrity under pressure through up to five checks -- a leak test (no
detrimental leakage), a proof pressure test (structural margin shown
nondestructively, holding a pressure above MEOP -- maximum expected
operating pressure -- without damage), a pressure cycling test
(fatigue life over repeated pressurization for equipment in cyclic
service), and a burst-margin demonstration that is either a physical
burst test (destructive, only on an article that may be sacrificed) or
a design burst analysis (nondestructive, for an article that must stay
usable). This module implements test applicability by campaign and
service profile, the mutually-exclusive burst-verification method
selection by article disposition, test sequencing (a destructive burst
test must come last), and per-test pass/fail evaluation; it does not
set the numeric levels/durations themselves (those are project-
specific and come from the item's qualification/acceptance/protoflight
baseline, e1003-eq-qual / e1003-eq-acceptance / e1003-eq-protoflight).
"""

CAMPAIGNS = ("qualification", "acceptance", "protoflight")
DISPOSITIONS = ("dedicated_qualification", "flight")
TEST_TYPES = ("leak", "proof_pressure", "pressure_cycling", "design_burst", "burst")
STATUSES = ("open", "closed", "failed")


def required_tests(campaign, is_pressurized, cyclic_service, disposition):
    """Ordered tuple of applicable pressure-family test types for one
    equipment item. Non-pressurized equipment has no applicable tests.
    Every pressurized item gets leak and proof_pressure; cyclic_service
    adds pressure_cycling. The burst-margin check is disposition-
    driven: a dedicated_qualification article (may be sacrificed) gets
    the physical burst test; a flight article (must remain usable)
    gets the design_burst analysis instead. Raises ValueError for an
    unknown campaign or disposition."""
    if campaign not in CAMPAIGNS:
        raise ValueError("unknown campaign: %r" % (campaign,))
    if disposition not in DISPOSITIONS:
        raise ValueError("unknown article disposition: %r" % (disposition,))
    if not is_pressurized:
        return ()
    tests = ["leak", "proof_pressure"]
    if cyclic_service:
        tests.append("pressure_cycling")
    tests.append("burst" if disposition == "dedicated_qualification" else "design_burst")
    return tuple(tests)


def validate_sequence(tests_performed):
    """Validate an ordered sequence of test-type strings already
    performed on one article. Raises ValueError if: an entry is not a
    known test type; "burst" and "design_burst" both appear (the two
    burst-verification methods are mutually exclusive on one article);
    or "burst" appears anywhere but last (it is destructive, so
    nothing can follow it). Returns True when the sequence is valid."""
    for test in tests_performed:
        if test not in TEST_TYPES:
            raise ValueError("unknown test type: %r" % (test,))
    if "burst" in tests_performed and "design_burst" in tests_performed:
        raise ValueError("burst and design_burst are mutually exclusive on one article")
    if "burst" in tests_performed and tests_performed[-1] != "burst":
        raise ValueError("burst is destructive and must be the last test performed")
    return True


def evaluate_leak(measured_leak_rate, max_allowable_leak_rate):
    """Pass when the measured leak rate does not exceed the maximum
    allowable leak rate."""
    return measured_leak_rate <= max_allowable_leak_rate


def evaluate_proof_pressure(held_pressure, required_proof_pressure, anomaly_detected):
    """Pass when the held pressure reaches the required proof pressure
    and no anomaly (permanent deformation, leak, damage) was detected
    while holding it."""
    return held_pressure >= required_proof_pressure and not anomaly_detected


def evaluate_pressure_cycling(cycles_completed, required_cycles, failure_detected):
    """Pass when the required number of pressure cycles completed with
    no failure detected during cycling."""
    return cycles_completed >= required_cycles and not failure_detected


def evaluate_design_burst(predicted_burst_pressure, meop, required_burst_factor):
    """Pass when the analytically predicted burst pressure meets the
    required burst factor times MEOP (maximum expected operating
    pressure), demonstrated without a physical burst test."""
    return predicted_burst_pressure >= required_burst_factor * meop


def evaluate_burst(achieved_burst_pressure, meop, required_burst_factor):
    """Pass when the article's actual burst pressure, measured in a
    destructive physical burst test, meets the required burst factor
    times MEOP."""
    return achieved_burst_pressure >= required_burst_factor * meop


_EVALUATORS = {
    "leak": lambda r: evaluate_leak(r["measured_leak_rate"], r["max_allowable_leak_rate"]),
    "proof_pressure": lambda r: evaluate_proof_pressure(
        r["held_pressure"], r["required_proof_pressure"], r["anomaly_detected"]
    ),
    "pressure_cycling": lambda r: evaluate_pressure_cycling(
        r["cycles_completed"], r["required_cycles"], r["failure_detected"]
    ),
    "design_burst": lambda r: evaluate_design_burst(
        r["predicted_burst_pressure"], r["meop"], r["required_burst_factor"]
    ),
    "burst": lambda r: evaluate_burst(
        r["achieved_burst_pressure"], r["meop"], r["required_burst_factor"]
    ),
}


def evaluate_test(test_type, result):
    """Pass/fail bool for one test result dict, dispatched by test
    type. Raises ValueError for an unknown test type."""
    if test_type not in _EVALUATORS:
        raise ValueError("unknown test type: %r" % (test_type,))
    return _EVALUATORS[test_type](result)


def build_pressure_test_record(item_id, campaign, is_pressurized, cyclic_service, disposition, results):
    """Full pressure-test assessment for one equipment item. results is
    a dict test_type -> result dict, holding only the tests already
    performed/reported in performance order (a required test with no
    entry is left open). Returns a new dict; does not mutate results.
    Raises ValueError if the performed tests fail the sequencing
    rules, or if item_id is falsy."""
    if not item_id:
        raise ValueError("item is missing an id")
    required = required_tests(campaign, is_pressurized, cyclic_service, disposition)
    performed_order = [test for test in results.keys() if test in required]
    validate_sequence(performed_order)
    statuses = {}
    for test in required:
        if test not in results:
            statuses[test] = "open"
        else:
            statuses[test] = "closed" if evaluate_test(test, results[test]) else "failed"
    return {
        "id": item_id,
        "required_tests": required,
        "statuses": statuses,
    }


def open_or_failed_tests(record):
    """Required test-type names from a record that are not closed
    (still open, or failed), in required-test order."""
    return [test for test in record["required_tests"] if record["statuses"][test] != "closed"]


def item_complete(record):
    """True when every required test in the record is closed."""
    return len(open_or_failed_tests(record)) == 0
