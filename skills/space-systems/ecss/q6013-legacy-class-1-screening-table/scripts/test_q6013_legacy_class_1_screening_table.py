"""Contract tests for the Table 8-10 legacy screening list logic.

The cases follow the workflow one step at a time: lot validation, sequence
coverage, the canonical ordering and the burn-in bracket, the cumulative
walk that hands survivors from one screen to the next, the per-part drift
across the bracket, and the percent-defective comparison that can reject a
lot whose survivors are individually good. Percentages are compared with
assertAlmostEqual so a value landing on a bound reads the same everywhere.
"""

import unittest

from q6013_legacy_class_1_screening_table_logic import (
    BURN_IN_SCREEN,
    DRIFT_TOLERANCE,
    PDA_TOLERANCE,
    POST_BURN_IN_SCREEN,
    PRE_BURN_IN_SCREEN,
    REQUIRED_SCREENS,
    assess_legacy_screening_table,
    parameter_drift_percent,
    part_drift_verdict,
    percent_defective,
    screen_coverage,
    sequence_findings,
    validate_lot_size,
    walk_sequence,
)

BANDS = {"input-offset-voltage": 10.0, "supply-current": 5.0}


def _sequence(**rejects_by_screen):
    return [
        {"screen": screen, "rejects": rejects_by_screen.get(screen, 0)}
        for screen in REQUIRED_SCREENS
    ]


def _part(reference="sn-0001", offset_post=1.02, current_post=10.2):
    return {
        "reference": reference,
        "pre": {"input-offset-voltage": 1.0, "supply-current": 10.0},
        "post": {"input-offset-voltage": offset_post, "supply-current": current_post},
    }


def _spec(**overrides):
    spec = {
        "lot_size": 500,
        "sequence": _sequence(),
        "percent_defective_allowable": 5.0,
        "drift_bands": BANDS,
        "parts": [_part()],
    }
    spec.update(overrides)
    return spec


class LotValidationTests(unittest.TestCase):
    def test_positive_lot_is_returned(self):
        self.assertEqual(validate_lot_size(500), 500)

    def test_single_part_lot_allowed(self):
        self.assertEqual(validate_lot_size(1), 1)

    def test_zero_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(0)

    def test_negative_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(-10)

    def test_float_lot_rejected(self):
        with self.assertRaises(ValueError):
            validate_lot_size(500.0)


class CoverageTests(unittest.TestCase):
    def test_full_sequence_is_complete(self):
        coverage = screen_coverage(_sequence())
        self.assertTrue(coverage["complete"])
        self.assertEqual(coverage["missing"], [])

    def test_missing_screen_is_named(self):
        sequence = [s for s in _sequence() if s["screen"] != "seal-test"]
        coverage = screen_coverage(sequence)
        self.assertIn("seal-test", coverage["missing"])

    def test_duplicated_screen_is_named(self):
        sequence = _sequence() + [{"screen": "external-visual", "rejects": 0}]
        coverage = screen_coverage(sequence)
        self.assertEqual(coverage["duplicated"], ["external-visual"])

    def test_added_screen_does_not_block_coverage(self):
        sequence = _sequence() + [{"screen": "solderability-sample", "rejects": 0}]
        coverage = screen_coverage(sequence)
        self.assertEqual(coverage["unrecognized"], ["solderability-sample"])
        self.assertTrue(coverage["complete"])

    def test_empty_sequence_rejected(self):
        with self.assertRaises(ValueError):
            screen_coverage([])

    def test_entry_without_a_screen_name_rejected(self):
        with self.assertRaises(ValueError):
            screen_coverage([{"rejects": 0}])


class OrderingTests(unittest.TestCase):
    def test_canonical_sequence_is_ordered(self):
        record = sequence_findings(_sequence())
        self.assertTrue(record["ordered"])
        self.assertEqual(record["findings"], [])

    def test_a_swapped_pair_is_reported(self):
        sequence = _sequence()
        sequence[1], sequence[2] = sequence[2], sequence[1]
        record = sequence_findings(sequence)
        self.assertFalse(record["ordered"])

    def test_burn_in_before_its_pre_reading_is_reported(self):
        sequence = [
            s for s in _sequence() if s["screen"] not in (PRE_BURN_IN_SCREEN, BURN_IN_SCREEN)
        ]
        sequence = (
            [{"screen": BURN_IN_SCREEN, "rejects": 0}]
            + sequence
            + [{"screen": PRE_BURN_IN_SCREEN, "rejects": 0}]
        )
        record = sequence_findings(sequence)
        self.assertFalse(record["ordered"])

    def test_burn_in_with_no_post_reading_is_reported(self):
        sequence = [s for s in _sequence() if s["screen"] != POST_BURN_IN_SCREEN]
        record = sequence_findings(sequence)
        self.assertIn("burn-in has no electrical reading behind it", record["findings"])

    def test_an_inserted_extra_screen_does_not_break_the_order(self):
        sequence = _sequence()
        sequence.insert(3, {"screen": "solderability-sample", "rejects": 0})
        record = sequence_findings(sequence)
        self.assertTrue(record["ordered"])


class DriftTests(unittest.TestCase):
    def test_drift_is_signed_and_relative_to_the_pre_reading(self):
        self.assertAlmostEqual(parameter_drift_percent(10.0, 10.5), 5.0, places=9)

    def test_a_falling_parameter_drifts_negative(self):
        self.assertAlmostEqual(parameter_drift_percent(10.0, 9.0), -10.0, places=9)

    def test_a_negative_pre_reading_uses_its_magnitude(self):
        self.assertAlmostEqual(parameter_drift_percent(-10.0, -11.0), -10.0, places=9)

    def test_a_zero_pre_reading_rejected(self):
        with self.assertRaises(ValueError):
            parameter_drift_percent(0.0, 1.0)

    def test_a_part_inside_every_band_is_retained(self):
        record = part_drift_verdict(_part(), BANDS)
        self.assertTrue(record["retained"])
        self.assertEqual(record["exceeded"], [])

    def test_a_part_outside_one_band_is_removed(self):
        record = part_drift_verdict(_part(offset_post=1.2), BANDS)
        self.assertFalse(record["retained"])
        self.assertEqual(record["exceeded"], ["input-offset-voltage"])

    def test_a_drift_exactly_on_its_band_is_retained(self):
        record = part_drift_verdict(_part(offset_post=1.1), BANDS)
        self.assertAlmostEqual(record["drift_percent"]["input-offset-voltage"], 10.0, places=9)
        self.assertTrue(record["retained"])

    def test_a_downward_drift_is_caught_as_well_as_an_upward_one(self):
        record = part_drift_verdict(_part(current_post=9.0), BANDS)
        self.assertEqual(record["exceeded"], ["supply-current"])

    def test_a_missing_post_reading_rejected(self):
        part = _part()
        del part["post"]["supply-current"]
        with self.assertRaises(ValueError):
            part_drift_verdict(part, BANDS)

    def test_a_negative_band_rejected(self):
        with self.assertRaises(ValueError):
            part_drift_verdict(_part(), {"supply-current": -1.0})

    def test_empty_bands_rejected(self):
        with self.assertRaises(ValueError):
            part_drift_verdict(_part(), {})


class WalkTests(unittest.TestCase):
    def test_a_clean_lot_passes_every_part_through(self):
        record = walk_sequence(_sequence(), 500)
        self.assertEqual(record["surviving"], 500)
        self.assertEqual(record["count_rejects"], 0)

    def test_each_screen_receives_what_the_previous_one_passed(self):
        record = walk_sequence(_sequence(**{"temperature-cycling": 12}), 500)
        steps = {step["screen"]: step for step in record["steps"]}
        self.assertEqual(steps["temperature-cycling"]["entering"], 500)
        self.assertEqual(steps["constant-acceleration"]["entering"], 488)

    def test_rejects_accumulate_across_the_sequence(self):
        record = walk_sequence(
            _sequence(**{"temperature-cycling": 5, BURN_IN_SCREEN: 7}), 500
        )
        self.assertEqual(record["count_rejects"], 12)
        self.assertEqual(record["surviving"], 488)

    def test_a_screen_rejecting_more_than_reached_it_is_refused(self):
        with self.assertRaises(ValueError):
            walk_sequence(_sequence(**{"internal-visual": 600}), 500)

    def test_a_screen_without_a_reject_count_is_refused(self):
        sequence = _sequence()
        del sequence[0]["rejects"]
        with self.assertRaises(ValueError):
            walk_sequence(sequence, 500)


class PercentDefectiveTests(unittest.TestCase):
    def test_a_clean_lot_is_zero_percent_defective(self):
        self.assertAlmostEqual(percent_defective(0, 500), 0.0, places=9)

    def test_the_share_is_reported_in_percent(self):
        self.assertAlmostEqual(percent_defective(25, 500), 5.0, places=9)

    def test_a_whole_lot_removed_is_one_hundred_percent(self):
        self.assertAlmostEqual(percent_defective(500, 500), 100.0, places=9)

    def test_more_rejects_than_the_lot_refused(self):
        with self.assertRaises(ValueError):
            percent_defective(600, 500)


class AssessmentTests(unittest.TestCase):
    def test_a_clean_ordered_sequence_releases_the_lot(self):
        result = assess_legacy_screening_table(_spec())
        self.assertTrue(result["released"])
        self.assertEqual(result["disposition"], "release-for-acceptance")

    def test_the_delivered_quantity_drops_by_every_reject(self):
        spec = _spec(sequence=_sequence(**{"seal-test": 9}))
        result = assess_legacy_screening_table(spec)
        self.assertEqual(result["total_rejects"], 9)
        self.assertEqual(result["delivered_quantity"], 491)

    def test_a_drifted_part_counts_towards_the_percent_defective(self):
        spec = _spec(parts=[_part(reference="sn-0002", offset_post=1.5)])
        result = assess_legacy_screening_table(spec)
        self.assertEqual(result["drift_rejects"], 1)
        self.assertEqual(result["total_rejects"], 1)
        self.assertEqual(result["delivered_quantity"], 499)

    def test_a_removed_part_is_named_without_failing_the_lot(self):
        spec = _spec(parts=[_part(reference="sn-0002", offset_post=1.5)])
        result = assess_legacy_screening_table(spec)
        self.assertTrue(result["released"])
        self.assertEqual(len(result["removed_parts"]), 1)
        self.assertEqual(result["findings"], [])

    def test_enough_drifted_parts_take_the_lot_over_the_allowable(self):
        parts = [_part(reference="sn-%04d" % n, offset_post=1.5) for n in range(30)]
        spec = _spec(lot_size=100, parts=parts)
        result = assess_legacy_screening_table(spec)
        self.assertAlmostEqual(result["percent_defective"], 30.0, places=9)
        self.assertFalse(result["released"])
        self.assertEqual(result["disposition"], "reject-lot")

    def test_a_lot_on_the_allowable_is_still_released(self):
        spec = _spec(sequence=_sequence(**{"temperature-cycling": 25}), parts=[])
        result = assess_legacy_screening_table(spec)
        self.assertAlmostEqual(result["percent_defective"], 5.0, places=9)
        self.assertTrue(result["within_allowable"])
        self.assertEqual(len(result["advisories"]), 1)

    def test_a_lot_over_the_allowable_is_rejected_whole(self):
        spec = _spec(sequence=_sequence(**{"temperature-cycling": 40}), parts=[])
        result = assess_legacy_screening_table(spec)
        self.assertFalse(result["released"])
        self.assertEqual(result["disposition"], "reject-lot")
        self.assertGreater(result["delivered_quantity"], 0)

    def test_an_out_of_order_sequence_is_rejected_even_when_clean(self):
        sequence = _sequence()
        sequence[0], sequence[1] = sequence[1], sequence[0]
        result = assess_legacy_screening_table(_spec(sequence=sequence))
        self.assertFalse(result["released"])

    def test_a_missing_screen_is_a_finding(self):
        sequence = [s for s in _sequence() if s["screen"] != "radiographic-inspection"]
        result = assess_legacy_screening_table(_spec(sequence=sequence))
        self.assertFalse(result["released"])

    def test_parts_offered_without_bands_are_refused(self):
        spec = _spec()
        del spec["drift_bands"]
        with self.assertRaises(ValueError):
            assess_legacy_screening_table(spec)

    def test_more_drifted_parts_than_survivors_refused(self):
        spec = _spec(
            lot_size=2,
            sequence=_sequence(**{"internal-visual": 2}),
            parts=[_part("sn-1", offset_post=2.0), _part("sn-2", offset_post=2.0)],
        )
        with self.assertRaises(ValueError):
            assess_legacy_screening_table(spec)

    def test_an_allowable_outside_zero_to_one_hundred_refused(self):
        with self.assertRaises(ValueError):
            assess_legacy_screening_table(_spec(percent_defective_allowable=140.0))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["sequence"]
        with self.assertRaises(ValueError):
            assess_legacy_screening_table(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_legacy_screening_table(["lot_size"])

    def test_the_tolerances_are_small_enough_not_to_widen_a_limit(self):
        self.assertLess(PDA_TOLERANCE, 1e-6)
        self.assertLess(DRIFT_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
