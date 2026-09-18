"""Contract tests for the paint acceptance inspection logic.

The cases follow one painted batch through acceptance: the size of the
dry-film-thickness draw the area owes, the reduction of the readings, the three
thickness rules that run together, the adhesion result, the cured state, the
record that has to name instrument and calibration, and the disposition that
separates a rejected batch from one merely held on paperwork.
"""

import unittest

from q7031_acceptance_inspection_logic import (
    ADHESION_GRADES,
    MINIMUM_POINTS,
    REQUIRED_RECORD_FIELDS,
    adhesion_findings,
    assess_acceptance_campaign,
    assess_batch_acceptance,
    calibration_valid_on,
    measurement_points_required,
    parse_day,
    record_findings,
    thickness_findings,
    thickness_statistics,
)

SPEC = {"minimum_um": 40.0, "maximum_um": 80.0, "mean_low_um": 50.0, "mean_high_um": 70.0}


def _record(**overrides):
    record = {
        "batch_id": "LOT-4471",
        "unit_id": "SN-012",
        "inspector_id": "QA-19",
        "inspection_day": "2026-04-14",
        "instrument_id": "DFT-7",
        "calibration_due_day": "2026-06-30",
        "paint_lot_id": "PL-88",
    }
    record.update(overrides)
    return record


def _batch(**overrides):
    batch = {
        "name": "panel-plus-y",
        "area_m2": 1.2,
        "points_per_m2": 5.0,
        "readings_um": [58.0, 61.0, 57.0, 63.0, 59.0, 60.0],
        "thickness_spec": dict(SPEC),
        "adhesion_grade": 0,
        "cure_verified": True,
        "record": _record(),
    }
    batch.update(overrides)
    return batch


class PointSizingTests(unittest.TestCase):
    def test_draw_rounds_up_to_a_whole_point(self):
        self.assertEqual(measurement_points_required(1.2, 5.0, 1), 6)

    def test_a_small_fitting_still_owes_the_floor(self):
        self.assertEqual(measurement_points_required(0.1, 5.0), MINIMUM_POINTS)

    def test_an_exact_product_is_not_pushed_to_the_next_point(self):
        self.assertEqual(measurement_points_required(2.0, 5.0, 1), 10)

    def test_zero_area_is_refused(self):
        with self.assertRaises(ValueError):
            measurement_points_required(0.0)

    def test_a_non_positive_density_is_refused(self):
        with self.assertRaises(ValueError):
            measurement_points_required(2.0, 0.0)

    def test_a_boolean_minimum_is_refused(self):
        with self.assertRaises(ValueError):
            measurement_points_required(2.0, 5.0, True)


class StatisticsTests(unittest.TestCase):
    def test_mean_minimum_and_maximum_come_from_the_readings(self):
        stats = thickness_statistics([50.0, 60.0, 70.0])
        self.assertAlmostEqual(stats["mean_um"], 60.0, places=9)
        self.assertAlmostEqual(stats["minimum_um"], 50.0, places=9)
        self.assertAlmostEqual(stats["maximum_um"], 70.0, places=9)

    def test_a_single_reading_has_no_spread(self):
        stats = thickness_statistics([55.0])
        self.assertEqual(stats["count"], 1)
        self.assertAlmostEqual(stats["std_dev_um"], 0.0, places=9)

    def test_sample_deviation_uses_the_n_minus_one_divisor(self):
        stats = thickness_statistics([58.0, 62.0])
        self.assertAlmostEqual(stats["std_dev_um"], 2.8284271247461903, places=9)

    def test_an_empty_reading_set_is_refused(self):
        with self.assertRaises(ValueError):
            thickness_statistics([])

    def test_a_non_positive_reading_is_refused(self):
        with self.assertRaises(ValueError):
            thickness_statistics([58.0, 0.0])


class ThicknessRuleTests(unittest.TestCase):
    def test_conforming_readings_raise_nothing(self):
        stats = thickness_statistics([58.0, 61.0, 57.0, 63.0, 59.0, 60.0])
        self.assertEqual(thickness_findings(stats, SPEC), [])

    def test_a_reading_exactly_on_the_floor_is_accepted(self):
        stats = thickness_statistics([40.0, 60.0, 60.0, 60.0, 60.0, 60.0])
        self.assertAlmostEqual(stats["minimum_um"], 40.0, places=9)
        self.assertNotIn("thickness-point-below-minimum", thickness_findings(stats, SPEC))

    def test_one_thin_point_is_raised_even_with_a_healthy_mean(self):
        stats = thickness_statistics([22.0, 65.0, 65.0, 65.0, 65.0, 65.0])
        findings = thickness_findings(stats, SPEC)
        self.assertIn("thickness-point-below-minimum", findings)

    def test_a_thick_point_is_raised_on_its_own_rule(self):
        stats = thickness_statistics([60.0, 60.0, 60.0, 60.0, 60.0, 95.0])
        self.assertIn("thickness-point-above-maximum", thickness_findings(stats, SPEC))

    def test_a_mean_outside_the_nominal_band_is_raised(self):
        stats = thickness_statistics([44.0, 45.0, 46.0, 44.0, 45.0, 46.0])
        self.assertIn("mean-thickness-outside-band", thickness_findings(stats, SPEC))

    def test_too_few_points_is_its_own_finding(self):
        stats = thickness_statistics([58.0, 61.0])
        spec = dict(SPEC)
        spec["points_required"] = 6
        self.assertIn("thickness-points-short", thickness_findings(stats, spec))

    def test_an_inverted_specification_is_refused(self):
        stats = thickness_statistics([58.0])
        with self.assertRaises(ValueError):
            thickness_findings(stats, {"minimum_um": 80.0, "maximum_um": 40.0})


class AdhesionAndCalibrationTests(unittest.TestCase):
    def test_the_best_grade_is_accepted(self):
        self.assertEqual(adhesion_findings(0, 1), [])

    def test_a_grade_on_the_ceiling_is_accepted(self):
        self.assertEqual(adhesion_findings(1, 1), [])

    def test_a_grade_past_the_ceiling_is_raised(self):
        self.assertEqual(adhesion_findings(3, 1), ["adhesion-grade-exceeded"])

    def test_an_absent_adhesion_result_is_a_finding_not_a_pass(self):
        self.assertEqual(adhesion_findings(None), ["adhesion-result-absent"])

    def test_a_grade_off_the_scale_is_refused(self):
        with self.assertRaises(ValueError):
            adhesion_findings(9)

    def test_every_catalogued_grade_is_gradeable(self):
        for grade in ADHESION_GRADES:
            self.assertIsInstance(adhesion_findings(grade, 5), list)

    def test_calibration_running_to_the_due_day_is_still_valid(self):
        self.assertTrue(calibration_valid_on("2026-04-14", "2026-04-14"))

    def test_calibration_lapsed_before_the_inspection_is_invalid(self):
        self.assertFalse(calibration_valid_on("2026-04-13", "2026-04-14"))

    def test_a_non_iso_day_is_refused(self):
        with self.assertRaises(ValueError):
            parse_day("inspection_day", "14/04/2026")

    def test_a_day_the_month_does_not_have_is_refused(self):
        with self.assertRaises(ValueError):
            parse_day("inspection_day", "2026-02-30")

    def test_a_leap_day_is_accepted_in_a_leap_year(self):
        self.assertEqual(parse_day("inspection_day", "2024-02-29"), (2024, 2, 29))


class RecordTests(unittest.TestCase):
    def test_a_complete_record_raises_nothing(self):
        self.assertEqual(record_findings(_record()), [])

    def test_each_required_field_is_named_when_missing(self):
        for field in REQUIRED_RECORD_FIELDS:
            findings = record_findings(_record(**{field: None}))
            self.assertIn("record-field-missing:%s" % field, findings)

    def test_a_blank_string_counts_as_missing(self):
        self.assertIn("record-field-missing:inspector_id", record_findings(_record(inspector_id="   ")))

    def test_a_lapsed_calibration_is_raised_from_the_record(self):
        findings = record_findings(_record(calibration_due_day="2026-01-01"))
        self.assertIn("instrument-calibration-lapsed", findings)

    def test_a_non_mapping_record_is_refused(self):
        with self.assertRaises(ValueError):
            record_findings(["batch_id"])


class BatchDispositionTests(unittest.TestCase):
    def test_a_conforming_batch_is_accepted(self):
        result = assess_batch_acceptance(_batch())
        self.assertEqual(result["findings"], [])
        self.assertEqual(result["disposition"], "accepted")
        self.assertEqual(result["points_required"], 6)

    def test_a_thin_point_rejects_the_batch(self):
        result = assess_batch_acceptance(
            _batch(readings_um=[22.0, 65.0, 65.0, 65.0, 65.0, 65.0])
        )
        self.assertEqual(result["disposition"], "rejected")

    def test_a_paperwork_only_gap_holds_rather_than_rejects(self):
        result = assess_batch_acceptance(_batch(record=_record(instrument_id=None)))
        self.assertEqual(result["disposition"], "record-hold")
        self.assertFalse(result["accepted"])

    def test_an_unverified_cure_is_raised(self):
        result = assess_batch_acceptance(_batch(cure_verified=False))
        self.assertIn("cure-not-verified", result["findings"])

    def test_a_short_reading_set_is_raised_against_the_sized_draw(self):
        result = assess_batch_acceptance(_batch(readings_um=[58.0, 61.0, 60.0]))
        self.assertIn("thickness-points-short", result["findings"])

    def test_a_batch_without_a_name_is_refused(self):
        with self.assertRaises(ValueError):
            assess_batch_acceptance(_batch(name=""))


class CampaignTests(unittest.TestCase):
    def test_a_campaign_of_conforming_batches_passes(self):
        campaign = assess_acceptance_campaign([_batch(), _batch(name="panel-minus-y")])
        self.assertTrue(campaign["campaign_accepted"])
        self.assertEqual(campaign["rejected_batches"], [])

    def test_one_rejected_batch_fails_the_campaign(self):
        campaign = assess_acceptance_campaign([
            _batch(),
            _batch(name="panel-minus-y", adhesion_grade=4),
        ])
        self.assertFalse(campaign["campaign_accepted"])
        self.assertEqual(campaign["rejected_batches"], ["panel-minus-y"])

    def test_held_batches_are_reported_separately_from_rejected_ones(self):
        campaign = assess_acceptance_campaign([
            _batch(name="panel-minus-y", record=_record(paint_lot_id=None)),
        ])
        self.assertEqual(campaign["held_batches"], ["panel-minus-y"])
        self.assertEqual(campaign["rejected_batches"], [])

    def test_duplicate_batch_names_are_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_campaign([_batch(), _batch()])

    def test_an_empty_campaign_is_refused(self):
        with self.assertRaises(ValueError):
            assess_acceptance_campaign([])


if __name__ == "__main__":
    unittest.main()
