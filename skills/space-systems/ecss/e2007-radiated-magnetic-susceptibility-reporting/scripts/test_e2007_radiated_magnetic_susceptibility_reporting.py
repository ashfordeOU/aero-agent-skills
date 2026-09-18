#!/usr/bin/env python3
"""Gate 3 contract test for e2007-radiated-magnetic-susceptibility-reporting.

stdlib unittest, offline, deterministic. Run:
    python3 test_e2007_radiated_magnetic_susceptibility_reporting.py
"""

import unittest

from e2007_radiated_magnetic_susceptibility_reporting_logic import (
    CATEGORY_ABOVE,
    CATEGORY_AT_LEVEL,
    CATEGORY_SHORT,
    REQUIRED_ARTEFACTS,
    VERDICT_COMPLETE,
    VERDICT_DEFICIENT,
    assess_radiated_magnetic_susceptibility_reporting,
    categorize_exposure,
    dbpt_to_tesla,
    exposure_margin_db,
    loop_axial_flux_density_t,
    missing_artefacts,
    missing_required_frequencies,
    tesla_to_dbpt,
    validate_exposure_table,
    verify_loop,
)

# A ten-turn loop of 50 mm radius driven with one ampere, measured on its own
# plane. The independent value below is the textbook centre-of-loop field for
# that geometry, written out rather than recomputed from the module.
CENTRE_FIELD_T = 1.2566370614359172e-04
CENTRE_FIELD_DBPT = 161.98419728044195


def good_loop(**over):
    record = {
        "current_a": 1.0,
        "turns": 10,
        "radius_m": 0.05,
        "separation_m": 0.0,
        "measured_dbpt": CENTRE_FIELD_DBPT,
    }
    record.update(over)
    return record


def good_rows():
    return [
        {
            "frequency_hz": 30.0,
            "level_reached_dbpt": 140.0,
            "level_required_dbpt": 140.0,
        },
        {
            "frequency_hz": 1000.0,
            "level_reached_dbpt": 134.0,
            "level_required_dbpt": 130.0,
        },
        {
            "frequency_hz": 50000.0,
            "level_reached_dbpt": 120.0,
            "level_required_dbpt": 120.0,
        },
    ]


def good_pack(**over):
    pack = {
        "artefacts": {artefact: True for artefact in REQUIRED_ARTEFACTS},
        "loop_verification": good_loop(),
        "exposure_table": good_rows(),
        "required_frequencies_hz": [30.0, 1000.0, 50000.0],
    }
    pack.update(over)
    return pack


class TestLoopField(unittest.TestCase):
    def test_centre_of_loop_field_matches_the_independent_value(self):
        field = loop_axial_flux_density_t(1.0, 10, 0.05, 0.0)
        self.assertAlmostEqual(field / CENTRE_FIELD_T, 1.0, places=9)

    def test_field_falls_off_with_separation(self):
        near = loop_axial_flux_density_t(1.0, 10, 0.05, 0.0)
        far = loop_axial_flux_density_t(1.0, 10, 0.05, 0.5)
        self.assertLess(far, near / 100.0)

    def test_field_scales_with_the_turn_count(self):
        one = loop_axial_flux_density_t(1.0, 1, 0.05, 0.02)
        ten = loop_axial_flux_density_t(1.0, 10, 0.05, 0.02)
        self.assertAlmostEqual(ten / one, 10.0, places=9)

    def test_fractional_turn_count_is_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_flux_density_t(1.0, 2.5, 0.05, 0.0)

    def test_zero_current_is_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_flux_density_t(0.0, 10, 0.05, 0.0)

    def test_negative_separation_is_rejected(self):
        with self.assertRaises(ValueError):
            loop_axial_flux_density_t(1.0, 10, 0.05, -0.01)


class TestLevelScale(unittest.TestCase):
    def test_one_picotesla_is_the_zero_of_the_scale(self):
        self.assertAlmostEqual(tesla_to_dbpt(1.0e-12), 0.0, places=9)

    def test_a_microtesla_sits_at_one_hundred_and_twenty_decibels(self):
        self.assertAlmostEqual(tesla_to_dbpt(1.0e-6), 120.0, places=9)

    def test_the_scale_round_trips(self):
        back = dbpt_to_tesla(tesla_to_dbpt(CENTRE_FIELD_T))
        self.assertAlmostEqual(back / CENTRE_FIELD_T, 1.0, places=9)

    def test_a_non_positive_flux_density_has_no_decibel_level(self):
        with self.assertRaises(ValueError):
            tesla_to_dbpt(0.0)


class TestLoopVerification(unittest.TestCase):
    def test_a_reading_on_the_prediction_is_within_tolerance(self):
        result = verify_loop(good_loop())
        self.assertTrue(result["within_tolerance"])
        self.assertAlmostEqual(result["deviation_db"], 0.0, places=6)

    def test_a_reading_exactly_at_the_allowed_deviation_is_accepted(self):
        result = verify_loop(good_loop(measured_dbpt=CENTRE_FIELD_DBPT + 3.0), 3.0)
        self.assertAlmostEqual(result["deviation_db"], 3.0, places=6)
        self.assertTrue(result["within_tolerance"])

    def test_a_reading_well_past_the_allowance_is_out_of_tolerance(self):
        result = verify_loop(good_loop(measured_dbpt=CENTRE_FIELD_DBPT + 9.0), 3.0)
        self.assertFalse(result["within_tolerance"])

    def test_a_low_reading_is_out_of_tolerance_the_same_way(self):
        result = verify_loop(good_loop(measured_dbpt=CENTRE_FIELD_DBPT - 9.0), 3.0)
        self.assertFalse(result["within_tolerance"])

    def test_the_prediction_comes_from_the_geometry_not_the_reading(self):
        result = verify_loop(good_loop(measured_dbpt=10.0), 3.0)
        self.assertAlmostEqual(
            result["predicted_dbpt"] / CENTRE_FIELD_DBPT, 1.0, places=9
        )

    def test_a_missing_geometry_field_is_rejected(self):
        record = good_loop()
        del record["radius_m"]
        with self.assertRaises(ValueError):
            verify_loop(record)

    def test_a_non_positive_allowance_is_rejected(self):
        with self.assertRaises(ValueError):
            verify_loop(good_loop(), 0.0)


class TestExposureTable(unittest.TestCase):
    def test_a_level_on_the_requirement_is_grouped_as_reached(self):
        self.assertEqual(categorize_exposure(0.0), CATEGORY_AT_LEVEL)

    def test_a_level_under_the_requirement_is_a_shortfall(self):
        self.assertEqual(categorize_exposure(-2.0), CATEGORY_SHORT)

    def test_a_level_over_the_requirement_is_grouped_as_above(self):
        self.assertEqual(categorize_exposure(4.0), CATEGORY_ABOVE)

    def test_margin_is_the_reached_level_less_the_required_level(self):
        self.assertAlmostEqual(exposure_margin_db(134.0, 130.0), 4.0, places=9)

    def test_a_good_table_normalizes_with_a_category_per_row(self):
        table = validate_exposure_table(good_rows())
        self.assertEqual(len(table), 3)
        self.assertEqual(table[0]["category"], CATEGORY_AT_LEVEL)
        self.assertEqual(table[1]["category"], CATEGORY_ABOVE)

    def test_a_table_whose_frequencies_do_not_increase_is_rejected(self):
        rows = good_rows()
        rows[2]["frequency_hz"] = 10.0
        with self.assertRaises(ValueError):
            validate_exposure_table(rows)

    def test_an_empty_table_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_exposure_table([])

    def test_a_row_missing_the_required_level_is_rejected(self):
        rows = good_rows()
        del rows[1]["level_required_dbpt"]
        with self.assertRaises(ValueError):
            validate_exposure_table(rows)

    def test_a_required_frequency_absent_from_the_table_is_reported(self):
        table = validate_exposure_table(good_rows())
        absent = missing_required_frequencies(table, [30.0, 200.0])
        self.assertEqual(absent, [200.0])

    def test_every_recorded_frequency_counts_as_covered(self):
        table = validate_exposure_table(good_rows())
        self.assertEqual(missing_required_frequencies(table, [30.0, 50000.0]), [])


class TestArtefacts(unittest.TestCase):
    def test_a_complete_declaration_has_no_absent_artefact(self):
        self.assertEqual(
            missing_artefacts({a: True for a in REQUIRED_ARTEFACTS}), []
        )

    def test_an_undeclared_diagram_is_reported(self):
        declared = {a: True for a in REQUIRED_ARTEFACTS}
        declared["setup-diagram"] = False
        self.assertEqual(missing_artefacts(declared), ["setup-diagram"])

    def test_a_non_boolean_artefact_flag_is_rejected(self):
        declared = {a: True for a in REQUIRED_ARTEFACTS}
        declared["exposure-level-table"] = "yes"
        with self.assertRaises(ValueError):
            missing_artefacts(declared)


class TestFullAssessment(unittest.TestCase):
    def test_a_complete_pack_is_reported_complete(self):
        report = assess_radiated_magnetic_susceptibility_reporting(good_pack())
        self.assertEqual(report["findings"], [])
        self.assertEqual(report["verdict"], VERDICT_COMPLETE)

    def test_an_overdriven_frequency_is_a_limitation_not_a_finding(self):
        report = assess_radiated_magnetic_susceptibility_reporting(good_pack())
        self.assertEqual(report["overdriven_count"], 1)
        self.assertTrue(any("exposed harder" in m for m in report["limitations"]))

    def test_a_level_short_of_the_requirement_is_a_finding(self):
        rows = good_rows()
        rows[0]["level_reached_dbpt"] = 134.0
        report = assess_radiated_magnetic_susceptibility_reporting(
            good_pack(exposure_table=rows)
        )
        self.assertEqual(report["shortfall_count"], 1)
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_an_absent_diagram_fails_the_pack(self):
        artefacts = {a: True for a in REQUIRED_ARTEFACTS}
        artefacts["setup-diagram"] = False
        report = assess_radiated_magnetic_susceptibility_reporting(
            good_pack(artefacts=artefacts)
        )
        self.assertTrue(any("setup-diagram" in f for f in report["findings"]))
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_loop_reading_off_the_prediction_fails_the_pack(self):
        report = assess_radiated_magnetic_susceptibility_reporting(
            good_pack(loop_verification=good_loop(measured_dbpt=CENTRE_FIELD_DBPT - 12.0))
        )
        self.assertFalse(report["loop_verification"]["within_tolerance"])
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_an_unrecorded_required_frequency_fails_the_pack(self):
        report = assess_radiated_magnetic_susceptibility_reporting(
            good_pack(required_frequencies_hz=[30.0, 2000.0])
        )
        self.assertEqual(report["uncovered_frequencies_hz"], [2000.0])
        self.assertEqual(report["verdict"], VERDICT_DEFICIENT)

    def test_a_pack_missing_its_exposure_table_is_rejected(self):
        pack = good_pack()
        del pack["exposure_table"]
        with self.assertRaises(ValueError):
            assess_radiated_magnetic_susceptibility_reporting(pack)

    def test_the_report_carries_the_predicted_field_it_graded_against(self):
        report = assess_radiated_magnetic_susceptibility_reporting(good_pack())
        predicted = report["loop_verification"]["predicted_flux_density_t"]
        self.assertAlmostEqual(predicted / CENTRE_FIELD_T, 1.0, places=9)


if __name__ == "__main__":
    unittest.main()
