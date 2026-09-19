"""Contract tests for the mechanical-test validity checks.

The cases take a finished test apart: where along the gauge length the
specimen broke, what the fracture looked like, what the run did while it was
happening, and what the lot is owed once the invalid specimens have been set
aside.
"""

import unittest

from q7045_test_validity_checks_logic import (
    DEFAULT_MAX_FORCE_DROP_FRACTION,
    DEFAULT_OUTER_FIFTH_FRACTION,
    DEFAULT_RATE_TOLERANCE_PCT,
    DEFAULT_TEMPERATURE_TOLERANCE_K,
    anomaly_findings,
    assess_test_validity,
    force_discontinuity,
    fracture_mode_verdict,
    fracture_position,
    lot_disposition,
    rate_within_band,
    specimen_verdict,
    temperature_within_band,
)

GAUGE_LENGTH_MM = 50.0
RISING_TRACE = [0.0, 100.0, 200.0, 300.0, 380.0, 420.0, 430.0, 410.0, 360.0]


def _specimen(identifier="s1", **overrides):
    record = {
        "id": identifier,
        "fracture_offset_mm": 4.0,
        "fracture_mode": "cup-and-cone",
        "actual_rate": 0.00025,
        "nominal_rate": 0.00025,
        "actual_temperature_k": 293.0,
        "nominal_temperature_k": 293.0,
        "force_trace": list(RISING_TRACE),
    }
    record.update(overrides)
    return record


def _spec(**overrides):
    spec = {
        "specimens": [_specimen("s1"), _specimen("s2"), _specimen("s3")],
        "gauge_length_mm": GAUGE_LENGTH_MM,
        "required_valid": 3,
    }
    spec.update(overrides)
    return spec


class FracturePositionTests(unittest.TestCase):
    def test_a_mid_gauge_fracture_needs_nothing(self):
        position = fracture_position(0.0, GAUGE_LENGTH_MM)
        self.assertTrue(position["inside_gauge_length"])
        self.assertFalse(position["needs_displaced_gauge"])

    def test_the_offset_is_a_fraction_of_the_gauge_length(self):
        position = fracture_position(10.0, GAUGE_LENGTH_MM)
        self.assertAlmostEqual(position["offset_fraction"], 0.2, places=12)

    def test_the_sign_of_the_offset_does_not_matter(self):
        left = fracture_position(-12.0, GAUGE_LENGTH_MM)
        right = fracture_position(12.0, GAUGE_LENGTH_MM)
        self.assertAlmostEqual(left["offset_fraction"], right["offset_fraction"], places=12)

    def test_an_outer_fracture_owes_the_displaced_gauge_treatment(self):
        position = fracture_position(20.0, GAUGE_LENGTH_MM)
        self.assertTrue(position["inside_gauge_length"])
        self.assertTrue(position["needs_displaced_gauge"])

    def test_a_fracture_exactly_on_the_outer_limit_is_still_inner(self):
        position = fracture_position(DEFAULT_OUTER_FIFTH_FRACTION * GAUGE_LENGTH_MM, GAUGE_LENGTH_MM)
        self.assertAlmostEqual(position["offset_fraction"], DEFAULT_OUTER_FIFTH_FRACTION, places=12)
        self.assertFalse(position["needs_displaced_gauge"])

    def test_a_fracture_past_the_gauge_length_is_outside_it(self):
        position = fracture_position(30.0, GAUGE_LENGTH_MM)
        self.assertFalse(position["inside_gauge_length"])

    def test_a_zero_gauge_length_is_refused(self):
        with self.assertRaises(ValueError):
            fracture_position(0.0, 0.0)

    def test_an_outer_fraction_past_the_half_length_is_refused(self):
        with self.assertRaises(ValueError):
            fracture_position(0.0, GAUGE_LENGTH_MM, 0.6)


class FractureModeTests(unittest.TestCase):
    def test_a_cup_and_cone_is_material_governed(self):
        self.assertTrue(fracture_mode_verdict("cup-and-cone")["material_governed"])

    def test_a_slant_shear_is_material_governed(self):
        self.assertTrue(fracture_mode_verdict("slant-shear")["material_governed"])

    def test_an_in_grip_fracture_is_fixture_governed(self):
        self.assertFalse(fracture_mode_verdict("in-grip")["material_governed"])

    def test_a_knife_edge_initiation_is_fixture_governed(self):
        self.assertFalse(fracture_mode_verdict("at-knife-edge")["material_governed"])

    def test_the_mode_name_is_matched_case_insensitively(self):
        self.assertEqual(fracture_mode_verdict("Cup-And-Cone")["mode"], "cup-and-cone")

    def test_an_unnamed_appearance_is_refused(self):
        with self.assertRaises(ValueError):
            fracture_mode_verdict("looked fine")

    def test_an_empty_mode_is_refused(self):
        with self.assertRaises(ValueError):
            fracture_mode_verdict("")


class BandTests(unittest.TestCase):
    def test_a_rate_on_nominal_is_inside_its_band(self):
        self.assertTrue(rate_within_band(0.00025, 0.00025)["within"])

    def test_a_rate_far_from_nominal_is_outside_its_band(self):
        band = rate_within_band(0.0005, 0.00025)
        self.assertFalse(band["within"])
        self.assertAlmostEqual(band["deviation_pct"], 100.0, places=9)

    def test_a_rate_exactly_on_the_tolerance_is_accepted(self):
        band = rate_within_band(0.00025 * 1.2, 0.00025, DEFAULT_RATE_TOLERANCE_PCT)
        self.assertAlmostEqual(band["deviation_pct"], DEFAULT_RATE_TOLERANCE_PCT, places=9)
        self.assertTrue(band["within"])

    def test_a_soak_on_nominal_is_inside_its_band(self):
        self.assertTrue(temperature_within_band(293.0, 293.0)["within"])

    def test_a_soak_outside_its_band_is_reported_in_kelvin(self):
        band = temperature_within_band(300.0, 293.0)
        self.assertFalse(band["within"])
        self.assertAlmostEqual(band["deviation_k"], 7.0, places=9)

    def test_a_soak_exactly_on_the_tolerance_is_accepted(self):
        band = temperature_within_band(293.0 + DEFAULT_TEMPERATURE_TOLERANCE_K, 293.0)
        self.assertAlmostEqual(band["deviation_k"], DEFAULT_TEMPERATURE_TOLERANCE_K, places=9)
        self.assertTrue(band["within"])

    def test_a_zero_nominal_rate_is_refused(self):
        with self.assertRaises(ValueError):
            rate_within_band(0.0002, 0.0)


class DiscontinuityTests(unittest.TestCase):
    def test_a_clean_rise_holds_no_discontinuity(self):
        self.assertFalse(force_discontinuity(RISING_TRACE)["found"])

    def test_necking_after_maximum_force_is_not_an_anomaly(self):
        trace = RISING_TRACE + [200.0, 50.0]
        self.assertFalse(force_discontinuity(trace)["found"])

    def test_a_slip_before_maximum_force_is_found(self):
        trace = [0.0, 100.0, 200.0, 150.0, 300.0, 420.0, 430.0, 360.0]
        step = force_discontinuity(trace)
        self.assertTrue(step["found"])
        self.assertEqual(step["index"], 3)

    def test_the_drop_is_reported_as_a_fraction_of_the_running_force(self):
        trace = [0.0, 100.0, 200.0, 150.0, 300.0, 420.0, 430.0, 360.0]
        step = force_discontinuity(trace)
        self.assertAlmostEqual(step["drop_fraction"], 0.25, places=12)

    def test_a_very_short_trace_is_refused(self):
        with self.assertRaises(ValueError):
            force_discontinuity([0.0, 100.0])

    def test_an_allowance_of_one_is_refused(self):
        with self.assertRaises(ValueError):
            force_discontinuity(RISING_TRACE, 1.0)

    def test_the_default_allowance_is_two_percent(self):
        self.assertAlmostEqual(DEFAULT_MAX_FORCE_DROP_FRACTION, 0.02, places=12)


class AnomalyTests(unittest.TestCase):
    def test_a_clean_run_raises_nothing(self):
        self.assertEqual(anomaly_findings(_specimen()), [])

    def test_a_slipped_extensometer_is_raised(self):
        self.assertEqual(len(anomaly_findings(_specimen(extensometer_slipped=True))), 1)

    def test_a_machine_stop_is_raised(self):
        self.assertEqual(len(anomaly_findings(_specimen(machine_stopped=True))), 1)

    def test_a_rate_excursion_is_raised(self):
        self.assertTrue(anomaly_findings(_specimen(actual_rate=0.001)))

    def test_a_temperature_excursion_is_raised(self):
        self.assertTrue(anomaly_findings(_specimen(actual_temperature_k=310.0)))

    def test_channels_that_were_not_recorded_are_not_graded(self):
        record = _specimen()
        record["actual_rate"] = None
        record["actual_temperature_k"] = None
        record["force_trace"] = None
        self.assertEqual(anomaly_findings(record), [])

    def test_a_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            anomaly_findings(["s1"])


class SpecimenVerdictTests(unittest.TestCase):
    def test_a_clean_specimen_is_valid(self):
        verdict = specimen_verdict(_specimen(), GAUGE_LENGTH_MM)
        self.assertTrue(verdict["valid"])
        self.assertEqual(verdict["qualifications"], [])

    def test_an_outer_fracture_is_valid_but_qualified(self):
        verdict = specimen_verdict(_specimen(fracture_offset_mm=20.0), GAUGE_LENGTH_MM)
        self.assertTrue(verdict["valid"])
        self.assertTrue(verdict["qualifications"])

    def test_a_fracture_outside_the_gauge_length_is_invalid(self):
        verdict = specimen_verdict(_specimen(fracture_offset_mm=40.0), GAUGE_LENGTH_MM)
        self.assertFalse(verdict["valid"])

    def test_an_in_grip_fracture_is_invalid(self):
        verdict = specimen_verdict(_specimen(fracture_mode="in-grip"), GAUGE_LENGTH_MM)
        self.assertFalse(verdict["valid"])

    def test_several_defects_are_all_reported(self):
        verdict = specimen_verdict(
            _specimen(fracture_mode="in-grip", extensometer_slipped=True), GAUGE_LENGTH_MM
        )
        self.assertGreaterEqual(len(verdict["reasons"]), 2)

    def test_a_record_missing_a_key_is_refused(self):
        record = _specimen()
        del record["fracture_mode"]
        with self.assertRaises(ValueError):
            specimen_verdict(record, GAUGE_LENGTH_MM)


class LotDispositionTests(unittest.TestCase):
    def test_enough_valid_specimens_accept_the_lot(self):
        verdicts = [{"id": "s%d" % i, "valid": True} for i in range(3)]
        self.assertEqual(lot_disposition(verdicts, 3)["disposition"], "accept")

    def test_a_shortfall_with_no_repeats_allowed_rejects(self):
        verdicts = [{"id": "s1", "valid": True}, {"id": "s2", "valid": False}]
        self.assertEqual(lot_disposition(verdicts, 2)["disposition"], "reject")

    def test_a_shortfall_inside_the_repeat_allowance_calls_a_repeat(self):
        verdicts = [{"id": "s1", "valid": True}, {"id": "s2", "valid": False}]
        result = lot_disposition(verdicts, 2, max_repeats=1)
        self.assertEqual(result["disposition"], "repeat")
        self.assertEqual(result["repeat_ids"], ["s2"])

    def test_the_counts_are_reported_either_way(self):
        verdicts = [{"id": "s1", "valid": True}, {"id": "s2", "valid": False}]
        result = lot_disposition(verdicts, 2)
        self.assertEqual(result["valid_count"], 1)
        self.assertEqual(result["invalid_count"], 1)
        self.assertEqual(result["shortfall"], 1)

    def test_an_empty_lot_is_refused(self):
        with self.assertRaises(ValueError):
            lot_disposition([], 1)

    def test_a_required_count_below_one_is_refused(self):
        with self.assertRaises(ValueError):
            lot_disposition([{"id": "s1", "valid": True}], 0)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_lot_is_acceptable(self):
        result = assess_test_validity(_spec())
        self.assertTrue(result["acceptable"])
        self.assertEqual(result["findings"], [])

    def test_one_invalid_specimen_short_of_the_requirement_rejects(self):
        spec = _spec()
        spec["specimens"][1] = _specimen("s2", fracture_mode="in-grip")
        result = assess_test_validity(spec)
        self.assertFalse(result["acceptable"])
        self.assertEqual(result["lot"]["disposition"], "reject")

    def test_the_same_lot_with_a_repeat_allowed_calls_a_repeat(self):
        spec = _spec(max_repeats=1)
        spec["specimens"][1] = _specimen("s2", fracture_mode="in-grip")
        result = assess_test_validity(spec)
        self.assertEqual(result["lot"]["disposition"], "repeat")

    def test_findings_name_the_specimen_they_came_from(self):
        spec = _spec()
        spec["specimens"][2] = _specimen("s3", machine_stopped=True)
        result = assess_test_validity(spec)
        self.assertTrue(any("s3" in message for message in result["findings"]))

    def test_a_qualified_specimen_still_counts_as_valid(self):
        spec = _spec()
        spec["specimens"][0] = _specimen("s1", fracture_offset_mm=20.0)
        result = assess_test_validity(spec)
        self.assertTrue(result["acceptable"])
        self.assertTrue(result["qualifications"])

    def test_an_empty_lot_is_refused(self):
        with self.assertRaises(ValueError):
            assess_test_validity(_spec(specimens=[]))

    def test_a_missing_key_is_refused(self):
        spec = _spec()
        del spec["gauge_length_mm"]
        with self.assertRaises(ValueError):
            assess_test_validity(spec)

    def test_a_non_mapping_spec_is_refused(self):
        with self.assertRaises(ValueError):
            assess_test_validity([_specimen()])


if __name__ == "__main__":
    unittest.main()
