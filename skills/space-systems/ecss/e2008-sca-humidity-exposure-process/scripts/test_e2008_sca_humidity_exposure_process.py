"""Contract tests for the clause 6.4.3.8.2 subgroup humidity exposure logic."""

import unittest

from e2008_sca_humidity_exposure_process_logic import (
    AMBIENT_PRESSURE_BAND_KPA,
    SAMPLE_EXPOSURE_COMPLETE,
    SAMPLE_EXPOSURE_SHORT,
    SUBGROUP_EXPOSED,
    SUBGROUP_SHORT,
    SUBGROUP_UNDERSIZED,
    ambient_hold_intervals,
    assess_subgroup_exposure,
    credit_sample_exposure,
    overlap_h,
    pressure_in_band,
    validate_chamber_record,
    validate_pressure_band,
    validate_sample_window,
    validate_subgroup,
)

NOMINAL_PRESSURE_KPA = 101.3


def _record(step=10.0, end=100.0, overrides=None):
    """Build a chamber pressure record at a fixed logging step."""
    overrides = overrides or {}
    rows = []
    count = int(round(end / step)) + 1
    for i in range(count):
        time_h = i * step
        rows.append(
            {
                "time_h": time_h,
                "pressure_kpa": overrides.get(time_h, NOMINAL_PRESSURE_KPA),
            }
        )
    return rows


def _samples(count=4, loaded=0.0, unloaded=96.0):
    return [
        {"sample_id": "SCA-%02d" % (i + 1), "loaded_h": loaded, "unloaded_h": unloaded}
        for i in range(count)
    ]


def _spec(**overrides):
    spec = {
        "samples": _samples(),
        "chamber_record": _record(),
        "required_exposure_h": 96.0,
    }
    spec.update(overrides)
    return spec


class PressureBandTests(unittest.TestCase):
    def test_band_is_returned_as_floats(self):
        self.assertEqual(validate_pressure_band((86, 106)), (86.0, 106.0))

    def test_inverted_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_pressure_band((106.0, 86.0))

    def test_non_pair_band_rejected(self):
        with self.assertRaises(ValueError):
            validate_pressure_band((101.3,))

    def test_non_positive_band_edge_rejected(self):
        with self.assertRaises(ValueError):
            validate_pressure_band((0.0, 106.0))

    def test_laboratory_pressure_is_in_the_default_band(self):
        self.assertTrue(pressure_in_band(NOMINAL_PRESSURE_KPA))

    def test_band_edge_counts_as_in_band(self):
        self.assertAlmostEqual(AMBIENT_PRESSURE_BAND_KPA[0], 86.0, places=9)
        self.assertTrue(pressure_in_band(AMBIENT_PRESSURE_BAND_KPA[0]))

    def test_partly_evacuated_chamber_is_out_of_band(self):
        self.assertFalse(pressure_in_band(50.0))

    def test_non_numeric_pressure_rejected(self):
        with self.assertRaises(ValueError):
            pressure_in_band("101.3")


class ChamberRecordTests(unittest.TestCase):
    def test_ordered_record_is_accepted(self):
        self.assertEqual(len(validate_chamber_record(_record())), 11)

    def test_single_entry_record_rejected(self):
        with self.assertRaises(ValueError):
            validate_chamber_record([{"time_h": 0.0, "pressure_kpa": NOMINAL_PRESSURE_KPA}])

    def test_repeated_time_stamp_rejected(self):
        rows = _record(step=10.0, end=20.0)
        rows[2]["time_h"] = 10.0
        with self.assertRaises(ValueError):
            validate_chamber_record(rows)

    def test_missing_pressure_field_rejected(self):
        rows = _record(step=10.0, end=20.0)
        del rows[1]["pressure_kpa"]
        with self.assertRaises(ValueError):
            validate_chamber_record(rows)

    def test_zero_pressure_rejected(self):
        rows = _record(step=10.0, end=20.0, overrides={10.0: 0.0})
        with self.assertRaises(ValueError):
            validate_chamber_record(rows)


class SubgroupRosterTests(unittest.TestCase):
    def test_roster_is_normalized(self):
        roster = validate_subgroup(_samples(count=2))
        self.assertEqual(roster[0]["sample_id"], "SCA-01")
        self.assertAlmostEqual(roster[0]["unloaded_h"], 96.0, places=9)

    def test_empty_subgroup_rejected(self):
        with self.assertRaises(ValueError):
            validate_subgroup([])

    def test_duplicate_sample_id_rejected(self):
        samples = _samples(count=2)
        samples[1]["sample_id"] = samples[0]["sample_id"]
        with self.assertRaises(ValueError):
            validate_subgroup(samples)

    def test_unload_before_load_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_window(
                {"sample_id": "SCA-01", "loaded_h": 40.0, "unloaded_h": 10.0}, 0
            )

    def test_blank_sample_id_rejected(self):
        with self.assertRaises(ValueError):
            validate_sample_window(
                {"sample_id": "   ", "loaded_h": 0.0, "unloaded_h": 10.0}, 0
            )


class AmbientHoldTests(unittest.TestCase):
    def test_clean_record_is_one_continuous_hold(self):
        intervals = ambient_hold_intervals(_record())
        self.assertEqual(len(intervals), 1)
        self.assertAlmostEqual(intervals[0][1] - intervals[0][0], 100.0, places=9)

    def test_one_out_of_band_entry_splits_the_hold(self):
        intervals = ambient_hold_intervals(_record(overrides={40.0: 50.0}))
        self.assertEqual(len(intervals), 2)
        self.assertAlmostEqual(intervals[0][1], 30.0, places=9)
        self.assertAlmostEqual(intervals[1][0], 50.0, places=9)

    def test_fully_evacuated_record_holds_nothing(self):
        rows = [
            {"time_h": 0.0, "pressure_kpa": 10.0},
            {"time_h": 50.0, "pressure_kpa": 10.0},
        ]
        self.assertEqual(ambient_hold_intervals(rows), [])

    def test_declared_band_admits_a_mountain_laboratory(self):
        intervals = ambient_hold_intervals(_record(overrides={40.0: 80.0}), (78.0, 106.0))
        self.assertEqual(len(intervals), 1)

    def test_overlap_of_disjoint_spans_is_zero(self):
        self.assertAlmostEqual(overlap_h((0.0, 10.0), (20.0, 30.0)), 0.0, places=9)

    def test_overlap_is_the_shared_part(self):
        self.assertAlmostEqual(overlap_h((0.0, 30.0), (20.0, 50.0)), 10.0, places=9)

    def test_malformed_overlap_pair_rejected(self):
        with self.assertRaises(ValueError):
            overlap_h((0.0,), (20.0, 50.0))


class SampleCreditTests(unittest.TestCase):
    def test_clean_run_credits_the_whole_window(self):
        accounting = credit_sample_exposure(_samples(count=1)[0], _record())
        self.assertAlmostEqual(accounting["credited_exposure_h"], 96.0, places=9)
        self.assertAlmostEqual(accounting["uncredited_h"], 0.0, places=9)

    def test_pressure_loss_is_charged_against_the_credit(self):
        accounting = credit_sample_exposure(
            _samples(count=1)[0], _record(overrides={40.0: 50.0})
        )
        self.assertAlmostEqual(accounting["credited_exposure_h"], 76.0, places=9)
        self.assertAlmostEqual(accounting["uncredited_h"], 20.0, places=9)

    def test_time_outside_the_logged_record_earns_nothing(self):
        sample = {"sample_id": "SCA-01", "loaded_h": 0.0, "unloaded_h": 110.0}
        accounting = credit_sample_exposure(sample, _record())
        self.assertAlmostEqual(accounting["credited_exposure_h"], 100.0, places=9)
        self.assertAlmostEqual(accounting["unlogged_h"], 10.0, places=9)

    def test_late_loading_shortens_the_credit(self):
        sample = {"sample_id": "SCA-09", "loaded_h": 20.0, "unloaded_h": 96.0}
        accounting = credit_sample_exposure(sample, _record())
        self.assertAlmostEqual(accounting["credited_exposure_h"], 76.0, places=9)

    def test_longest_hold_is_reported(self):
        accounting = credit_sample_exposure(
            _samples(count=1)[0], _record(overrides={40.0: 50.0})
        )
        self.assertAlmostEqual(accounting["longest_ambient_hold_h"], 50.0, places=9)
        self.assertEqual(accounting["ambient_hold_count"], 2)


class SubgroupAssessmentTests(unittest.TestCase):
    def test_nominal_subgroup_is_exposed(self):
        result = assess_subgroup_exposure(_spec())
        self.assertEqual(result["verdict"], SUBGROUP_EXPOSED)
        self.assertEqual(result["findings"], [])

    def test_exposure_landing_on_the_period_is_complete(self):
        result = assess_subgroup_exposure(_spec())
        self.assertAlmostEqual(
            result["samples"][0]["credited_exposure_h"],
            result["required_exposure_h"],
            places=9,
        )
        self.assertEqual(result["samples"][0]["verdict"], SAMPLE_EXPOSURE_COMPLETE)

    def test_one_short_sample_holds_the_whole_subgroup(self):
        samples = _samples()
        samples[2]["loaded_h"] = 30.0
        result = assess_subgroup_exposure(_spec(samples=samples))
        self.assertEqual(result["verdict"], SUBGROUP_SHORT)
        self.assertEqual(result["samples"][2]["verdict"], SAMPLE_EXPOSURE_SHORT)
        self.assertAlmostEqual(result["samples"][2]["shortfall_h"], 30.0, places=9)

    def test_pressure_loss_shortens_every_sample(self):
        result = assess_subgroup_exposure(
            _spec(chamber_record=_record(overrides={40.0: 50.0}))
        )
        self.assertEqual(result["verdict"], SUBGROUP_SHORT)
        self.assertEqual(len(result["findings"]), 4)

    def test_undersized_subgroup_is_its_own_verdict(self):
        result = assess_subgroup_exposure(_spec(samples=_samples(count=2)))
        self.assertEqual(result["verdict"], SUBGROUP_UNDERSIZED)

    def test_declared_subgroup_floor_is_honoured(self):
        result = assess_subgroup_exposure(
            _spec(samples=_samples(count=2), min_subgroup_size=2)
        )
        self.assertEqual(result["verdict"], SUBGROUP_EXPOSED)

    def test_ambient_hold_total_is_reported(self):
        result = assess_subgroup_exposure(_spec())
        self.assertAlmostEqual(result["ambient_hold_h"], 100.0, places=9)
        self.assertAlmostEqual(result["record_span_h"], 100.0, places=9)

    def test_unlogged_chamber_time_raises_a_finding(self):
        samples = _samples()
        for sample in samples:
            sample["unloaded_h"] = 110.0
        result = assess_subgroup_exposure(_spec(samples=samples))
        self.assertEqual(
            len([f for f in result["findings"] if "outside the logged record" in f]), 4
        )

    def test_zero_required_period_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_exposure(_spec(required_exposure_h=0.0))

    def test_non_integer_subgroup_floor_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_exposure(_spec(min_subgroup_size=2.5))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["chamber_record"]
        with self.assertRaises(ValueError):
            assess_subgroup_exposure(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_subgroup_exposure(["samples"])


if __name__ == "__main__":
    unittest.main()
