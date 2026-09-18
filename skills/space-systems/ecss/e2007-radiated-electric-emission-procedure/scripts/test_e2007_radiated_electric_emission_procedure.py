#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-electric-emission-procedure.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_electric_emission_procedure.py
"""

import unittest

from e2007_radiated_electric_emission_procedure_logic import (
    DEFAULT_MAX_WARMUP_DRIFT_DB,
    REQUIRED_POLARIZATIONS,
    WARMUP_DRIFTING,
    WARMUP_SETTLED,
    WARMUP_UNDER_WARMED,
    assess_radiated_emission_procedure,
    at_least,
    at_most,
    bandwidth_to_step_ratio,
    categorize_warmup,
    missing_polarizations,
    polarizations_covered,
    scan_duration_s,
    step_duration_s,
    step_leaves_unmeasured_frequencies,
    step_point_count,
    steps_recorded_before_settling,
    unrecorded_sub_bands,
    validate_instrument,
    validate_scan_step,
    validate_scan_steps,
    warmup_shortfall_s,
)

BAND_START = 30.0e6
BAND_STOP = 1000.0e6
WARMUP_S = 1800.0


def instrument(elapsed=1800.0, drift=0.2, required=WARMUP_S):
    return {
        "instrument_id": "emi-receiver-1",
        "required_warmup_s": required,
        "elapsed_warmup_s": elapsed,
        "drift_db": drift,
    }


def scan_step(
    start,
    stop,
    polarization="horizontal",
    step_hz=50.0e3,
    bandwidth=120.0e3,
    dwell=0.02,
    offset=WARMUP_S,
):
    return {
        "start_hz": start,
        "stop_hz": stop,
        "step_hz": step_hz,
        "measurement_bandwidth_hz": bandwidth,
        "dwell_s": dwell,
        "start_offset_s": offset,
        "polarization": polarization,
    }


def full_scan():
    steps = []
    for polarization in REQUIRED_POLARIZATIONS:
        steps.append(scan_step(BAND_START, 300.0e6, polarization))
        steps.append(scan_step(300.0e6, BAND_STOP, polarization))
    return steps


class TestInstrumentValidation(unittest.TestCase):
    def test_instrument_normalizes_identifier(self):
        record = validate_instrument(instrument())
        self.assertEqual(record["instrument_id"], "emi-receiver-1")

    def test_instrument_rejects_non_positive_warmup_requirement(self):
        with self.assertRaises(ValueError):
            validate_instrument(instrument(required=0.0))

    def test_instrument_rejects_negative_elapsed_warmup(self):
        with self.assertRaises(ValueError):
            validate_instrument(instrument(elapsed=-1.0))

    def test_instrument_rejects_negative_drift(self):
        with self.assertRaises(ValueError):
            validate_instrument(instrument(drift=-0.1))

    def test_instrument_rejects_boolean_as_a_number(self):
        record = instrument()
        record["elapsed_warmup_s"] = True
        with self.assertRaises(ValueError):
            validate_instrument(record)

    def test_instrument_rejects_a_non_mapping(self):
        with self.assertRaises(ValueError):
            validate_instrument(["emi-receiver-1", 1800.0])


class TestWarmup(unittest.TestCase):
    def test_shortfall_is_zero_once_the_period_has_elapsed(self):
        self.assertAlmostEqual(warmup_shortfall_s(instrument()), 0.0, places=9)

    def test_shortfall_names_the_time_still_owed(self):
        self.assertAlmostEqual(
            warmup_shortfall_s(instrument(elapsed=1200.0)), 600.0, places=9
        )

    def test_warmup_exactly_at_the_requirement_is_settled(self):
        self.assertEqual(categorize_warmup(instrument(elapsed=WARMUP_S)), WARMUP_SETTLED)

    def test_short_warmup_is_under_warmed(self):
        self.assertEqual(
            categorize_warmup(instrument(elapsed=1799.0)), WARMUP_UNDER_WARMED
        )

    def test_drift_over_the_allowance_is_drifting(self):
        self.assertEqual(
            categorize_warmup(instrument(drift=0.9)), WARMUP_DRIFTING
        )

    def test_drift_exactly_on_the_allowance_is_settled(self):
        self.assertEqual(
            categorize_warmup(instrument(drift=DEFAULT_MAX_WARMUP_DRIFT_DB)),
            WARMUP_SETTLED,
        )

    def test_under_warmed_outranks_drift(self):
        self.assertEqual(
            categorize_warmup(instrument(elapsed=10.0, drift=5.0)),
            WARMUP_UNDER_WARMED,
        )

    def test_non_positive_drift_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            categorize_warmup(instrument(), max_drift_db=0.0)


class TestScanStepValidation(unittest.TestCase):
    def test_step_is_normalized(self):
        record = validate_scan_step(scan_step(BAND_START, 300.0e6))
        self.assertAlmostEqual(record["step_hz"], 50.0e3, places=6)

    def test_inverted_edges_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_step(scan_step(300.0e6, BAND_START))

    def test_zero_step_size_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_step(scan_step(BAND_START, 300.0e6, step_hz=0.0))

    def test_zero_dwell_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_step(scan_step(BAND_START, 300.0e6, dwell=0.0))

    def test_negative_offset_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_step(scan_step(BAND_START, 300.0e6, offset=-1.0))

    def test_unknown_polarization_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_step(scan_step(BAND_START, 300.0e6, polarization="circular"))

    def test_empty_step_list_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_scan_steps([])

    def test_steps_are_ordered_by_polarization_then_frequency(self):
        ordered = validate_scan_steps(list(reversed(full_scan())))
        self.assertEqual(ordered[0]["polarization"], "horizontal")
        self.assertAlmostEqual(ordered[0]["start_hz"], BAND_START, places=3)


class TestStepGeometry(unittest.TestCase):
    def test_point_count_includes_both_edges(self):
        self.assertEqual(step_point_count(scan_step(1.0e6, 1.1e6, step_hz=10.0e3)), 11)

    def test_point_count_of_a_step_narrower_than_one_increment(self):
        self.assertEqual(step_point_count(scan_step(1.0e6, 1.001e6, step_hz=10.0e3)), 1)

    def test_bandwidth_to_step_ratio(self):
        ratio = bandwidth_to_step_ratio(scan_step(1.0e6, 2.0e6, step_hz=60.0e3))
        self.assertAlmostEqual(ratio, 2.0, places=9)

    def test_step_equal_to_the_bandwidth_leaves_nothing_unmeasured(self):
        step = scan_step(1.0e6, 2.0e6, step_hz=120.0e3, bandwidth=120.0e3)
        self.assertFalse(step_leaves_unmeasured_frequencies(step))

    def test_step_wider_than_the_bandwidth_skips_frequencies(self):
        step = scan_step(1.0e6, 2.0e6, step_hz=200.0e3, bandwidth=120.0e3)
        self.assertTrue(step_leaves_unmeasured_frequencies(step))

    def test_step_duration_is_points_times_dwell(self):
        step = scan_step(1.0e6, 1.1e6, step_hz=10.0e3, dwell=0.02)
        self.assertAlmostEqual(step_duration_s(step), 0.22, places=9)

    def test_scan_duration_sums_every_step(self):
        steps = [
            scan_step(1.0e6, 1.1e6, "horizontal", step_hz=10.0e3, dwell=0.02),
            scan_step(1.0e6, 1.1e6, "vertical", step_hz=10.0e3, dwell=0.02),
        ]
        self.assertAlmostEqual(scan_duration_s(steps), 0.44, places=9)


class TestCoverage(unittest.TestCase):
    def test_both_polarizations_are_reported_as_covered(self):
        self.assertEqual(polarizations_covered(full_scan()), ["horizontal", "vertical"])

    def test_a_single_polarization_scan_names_the_missing_one(self):
        steps = [scan_step(BAND_START, BAND_STOP, "horizontal")]
        self.assertEqual(missing_polarizations(steps), ["vertical"])

    def test_touching_steps_leave_no_unrecorded_sub_band(self):
        self.assertEqual(unrecorded_sub_bands(full_scan(), BAND_START, BAND_STOP), [])

    def test_a_hole_in_one_polarization_is_exposed(self):
        steps = full_scan()
        steps[0] = scan_step(BAND_START, 250.0e6, "horizontal")
        gaps = unrecorded_sub_bands(steps, BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertEqual(gaps[0]["polarization"], "horizontal")
        self.assertAlmostEqual(gaps[0]["span_hz"], 50.0e6, places=3)

    def test_an_absent_polarization_leaves_the_whole_band_unrecorded(self):
        steps = [scan_step(BAND_START, BAND_STOP, "horizontal")]
        gaps = unrecorded_sub_bands(steps, BAND_START, BAND_STOP)
        self.assertEqual(len(gaps), 1)
        self.assertAlmostEqual(gaps[0]["span_hz"], BAND_STOP - BAND_START, places=3)

    def test_an_inverted_declared_band_is_rejected(self):
        with self.assertRaises(ValueError):
            unrecorded_sub_bands(full_scan(), BAND_STOP, BAND_START)


class TestSettlingOrder(unittest.TestCase):
    def test_a_step_started_exactly_at_the_warmup_end_is_accepted(self):
        early = steps_recorded_before_settling(instrument(), full_scan())
        self.assertEqual(early, [])

    def test_a_step_started_during_warmup_is_flagged(self):
        steps = full_scan()
        steps[0] = scan_step(BAND_START, 300.0e6, "horizontal", offset=600.0)
        early = steps_recorded_before_settling(instrument(), steps)
        self.assertEqual(len(early), 1)
        self.assertAlmostEqual(early[0]["start_offset_s"], 600.0, places=9)


class TestBoundHelpers(unittest.TestCase):
    def test_at_least_absorbs_representation_error(self):
        self.assertTrue(at_least(0.1 + 0.2, 0.3))

    def test_at_most_absorbs_representation_error(self):
        self.assertTrue(at_most(0.3, 0.1 + 0.2))


class TestAssessment(unittest.TestCase):
    def test_a_clean_run_is_procedure_followed(self):
        report = assess_radiated_emission_procedure(
            instrument(), full_scan(), BAND_START, BAND_STOP
        )
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], "procedure-followed")
        self.assertEqual(report["warmup"], WARMUP_SETTLED)

    def test_an_under_warmed_receiver_forces_a_rerun(self):
        report = assess_radiated_emission_procedure(
            instrument(elapsed=300.0), full_scan(), BAND_START, BAND_STOP
        )
        self.assertEqual(report["verdict"], "rerun-required")
        self.assertTrue(any("still owed" in m for m in report["findings"]))

    def test_a_coarse_step_forces_a_rerun(self):
        steps = full_scan()
        steps[0] = scan_step(
            BAND_START, 300.0e6, "horizontal", step_hz=200.0e3, bandwidth=120.0e3
        )
        report = assess_radiated_emission_procedure(
            instrument(), steps, BAND_START, BAND_STOP
        )
        self.assertTrue(
            any("between measurement cells" in m for m in report["findings"])
        )
        self.assertEqual(report["verdict"], "rerun-required")

    def test_mixed_dwell_is_a_limitation_not_a_finding(self):
        steps = full_scan()
        steps[1] = scan_step(300.0e6, BAND_STOP, "horizontal", dwell=0.05)
        report = assess_radiated_emission_procedure(
            instrument(), steps, BAND_START, BAND_STOP
        )
        self.assertEqual(report["findings"], [])
        self.assertTrue(any("dwell is not uniform" in m for m in report["limitations"]))
        self.assertEqual(report["verdict"], "procedure-followed")

    def test_report_carries_the_total_point_count(self):
        steps = [
            scan_step(1.0e6, 1.1e6, "horizontal", step_hz=10.0e3),
            scan_step(1.0e6, 1.1e6, "vertical", step_hz=10.0e3),
        ]
        report = assess_radiated_emission_procedure(
            instrument(), steps, 1.0e6, 1.1e6
        )
        self.assertEqual(report["point_count"], 22)

    def test_assessment_propagates_a_step_error(self):
        with self.assertRaises(ValueError):
            assess_radiated_emission_procedure(instrument(), [], BAND_START, BAND_STOP)


if __name__ == "__main__":
    unittest.main()
