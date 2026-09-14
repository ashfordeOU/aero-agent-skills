"""Contract tests for the clause 4.2.3.4 evaluation-campaign logic."""

import unittest

from q6013_class_1_evaluation_testing_logic import (
    DEVICE_HOUR_TOLERANCE,
    ENDURANCE_BLOCKS,
    MANDATORY_BLOCKS,
    assess_block,
    assess_evaluation_campaign,
    block_device_hours,
    campaign_device_hours,
    lot_diversity,
    missing_blocks,
    validate_block,
    validate_part_type,
)

PART = {
    "manufacturer": "Example Semiconductor",
    "part_number": "XS-4417-QT",
    "date_codes": ["2431", "2436", "2503"],
}


def _full_blocks(**overrides):
    blocks = [
        {"name": "construction-analysis", "samples": 5, "failures": 0},
        {"name": "electrical-characterization", "samples": 22, "failures": 0},
        {"name": "environmental-stress", "samples": 22, "failures": 0, "duration_h": 100.0},
        {"name": "endurance", "samples": 22, "failures": 0, "duration_h": 2000.0},
        {"name": "radiation", "samples": 11, "failures": 0, "minimum_samples": 10},
    ]
    for name, patch in overrides.items():
        target = name.replace("_", "-")
        for block in blocks:
            if block["name"] == target:
                block.update(patch)
    return blocks


def _spec(**overrides):
    spec = {
        "part_type": dict(PART),
        "blocks": _full_blocks(),
        "minimum_samples": 5,
        "minimum_lots": 3,
        "required_device_hours": 46200.0,
    }
    spec.update(overrides)
    return spec


class PartTypeIdentityTests(unittest.TestCase):
    def test_identity_returned_normalized(self):
        identity = validate_part_type(PART)
        self.assertEqual(identity["part_number"], "XS-4417-QT")
        self.assertEqual(len(identity["date_codes"]), 3)

    def test_blank_manufacturer_rejected(self):
        bad = dict(PART, manufacturer="   ")
        with self.assertRaises(ValueError):
            validate_part_type(bad)

    def test_missing_part_number_rejected(self):
        bad = {"manufacturer": "Example", "date_codes": ["2431"]}
        with self.assertRaises(ValueError):
            validate_part_type(bad)

    def test_empty_date_codes_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_type(dict(PART, date_codes=[]))

    def test_non_mapping_part_type_rejected(self):
        with self.assertRaises(ValueError):
            validate_part_type(["Example", "XS-4417-QT"])

    def test_repeated_date_code_counts_once(self):
        self.assertEqual(lot_diversity(dict(PART, date_codes=["2431", "2431"])), 1)

    def test_distinct_date_codes_counted(self):
        self.assertEqual(lot_diversity(PART), 3)


class BlockValidationTests(unittest.TestCase):
    def test_name_normalized_to_hyphen_form(self):
        record = validate_block({"name": "Electrical Characterization", "samples": 5,
                                 "failures": 0})
        self.assertEqual(record["name"], "electrical-characterization")

    def test_underscore_name_normalized(self):
        record = validate_block({"name": "construction_analysis", "samples": 3,
                                 "failures": 0})
        self.assertEqual(record["name"], "construction-analysis")

    def test_zero_samples_rejected(self):
        with self.assertRaises(ValueError):
            validate_block({"name": "endurance", "samples": 0, "failures": 0})

    def test_negative_failures_rejected(self):
        with self.assertRaises(ValueError):
            validate_block({"name": "endurance", "samples": 10, "failures": -1})

    def test_boolean_sample_count_rejected(self):
        with self.assertRaises(ValueError):
            validate_block({"name": "endurance", "samples": True, "failures": 0})

    def test_failures_above_samples_rejected(self):
        with self.assertRaises(ValueError):
            validate_block({"name": "endurance", "samples": 4, "failures": 5})

    def test_negative_duration_rejected(self):
        with self.assertRaises(ValueError):
            validate_block({"name": "endurance", "samples": 4, "failures": 0,
                            "duration_h": -10.0})

    def test_device_hours_is_samples_times_duration(self):
        hours = block_device_hours({"name": "endurance", "samples": 22, "failures": 0,
                                    "duration_h": 2000.0})
        self.assertAlmostEqual(hours, 44000.0, places=9)


class BlockVerdictTests(unittest.TestCase):
    def test_clean_block_passes(self):
        record = assess_block({"name": "endurance", "samples": 22, "failures": 0}, 22)
        self.assertTrue(record["passed"])
        self.assertEqual(record["findings"], [])

    def test_sample_shortfall_is_a_finding(self):
        record = assess_block({"name": "endurance", "samples": 8, "failures": 0}, 22)
        self.assertFalse(record["passed"])
        self.assertEqual(len(record["findings"]), 1)

    def test_sample_count_exactly_at_floor_passes(self):
        record = assess_block({"name": "endurance", "samples": 22, "failures": 0}, 22)
        self.assertEqual(record["applied_minimum_samples"], 22)
        self.assertTrue(record["passed"])

    def test_failure_above_allowance_is_a_finding(self):
        record = assess_block({"name": "endurance", "samples": 22, "failures": 1}, 22)
        self.assertFalse(record["passed"])

    def test_failure_within_declared_allowance_passes(self):
        record = assess_block(
            {"name": "endurance", "samples": 22, "failures": 1, "allowed_failures": 1}, 22
        )
        self.assertTrue(record["passed"])

    def test_both_shortfalls_reported_not_just_the_first(self):
        record = assess_block({"name": "endurance", "samples": 3, "failures": 2}, 22)
        self.assertEqual(len(record["findings"]), 2)

    def test_block_minimum_overrides_campaign_default(self):
        record = assess_block(
            {"name": "radiation", "samples": 11, "failures": 0, "minimum_samples": 10}, 22
        )
        self.assertEqual(record["applied_minimum_samples"], 10)
        self.assertTrue(record["passed"])


class CoverageTests(unittest.TestCase):
    def test_full_campaign_has_no_missing_blocks(self):
        records = [assess_block(b, 5) for b in _full_blocks()]
        self.assertEqual(missing_blocks(records), [])

    def test_absent_block_is_reported(self):
        blocks = [b for b in _full_blocks() if b["name"] != "radiation"]
        records = [assess_block(b, 5) for b in blocks]
        self.assertEqual(missing_blocks(records), ["radiation"])

    def test_missing_blocks_preserve_mandatory_order(self):
        records = [assess_block({"name": "endurance", "samples": 5, "failures": 0}, 5)]
        self.assertEqual(missing_blocks(records), [
            name for name in MANDATORY_BLOCKS if name != "endurance"
        ])

    def test_missing_blocks_rejects_malformed_record(self):
        with self.assertRaises(ValueError):
            missing_blocks([{"samples": 5}])

    def test_only_endurance_bearing_blocks_accumulate_hours(self):
        records = [assess_block(b, 5) for b in _full_blocks()]
        expected = 22 * 2000.0 + 22 * 100.0
        self.assertAlmostEqual(campaign_device_hours(records), expected, places=9)

    def test_endurance_block_names_are_a_subset_of_the_mandatory_set(self):
        for name in ENDURANCE_BLOCKS:
            self.assertIn(name, MANDATORY_BLOCKS)


class CampaignAssessmentTests(unittest.TestCase):
    def test_complete_campaign_qualifies(self):
        result = assess_evaluation_campaign(_spec())
        self.assertTrue(result["qualified"])
        self.assertEqual(result["findings"], [])

    def test_accumulated_hours_exactly_at_floor_is_met(self):
        result = assess_evaluation_campaign(_spec())
        self.assertAlmostEqual(
            result["accumulated_device_hours"],
            result["required_device_hours"],
            places=9,
        )
        self.assertTrue(result["device_hours_met"])

    def test_hours_below_floor_blocks_qualification(self):
        result = assess_evaluation_campaign(_spec(required_device_hours=60000.0))
        self.assertFalse(result["qualified"])
        self.assertFalse(result["device_hours_met"])

    def test_single_lot_sample_set_blocks_qualification(self):
        spec = _spec(part_type=dict(PART, date_codes=["2431"]))
        result = assess_evaluation_campaign(spec)
        self.assertEqual(result["lots"], 1)
        self.assertFalse(result["qualified"])

    def test_missing_mandatory_block_blocks_qualification(self):
        blocks = [b for b in _full_blocks() if b["name"] != "construction-analysis"]
        result = assess_evaluation_campaign(_spec(blocks=blocks))
        self.assertIn("construction-analysis", result["missing_blocks"])
        self.assertFalse(result["qualified"])

    def test_failure_in_one_block_blocks_qualification(self):
        blocks = _full_blocks(endurance={"failures": 1})
        result = assess_evaluation_campaign(_spec(blocks=blocks))
        self.assertFalse(result["qualified"])

    def test_duplicate_block_declaration_rejected(self):
        blocks = _full_blocks() + [{"name": "endurance", "samples": 5, "failures": 0}]
        with self.assertRaises(ValueError):
            assess_evaluation_campaign(_spec(blocks=blocks))

    def test_empty_block_list_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_campaign(_spec(blocks=[]))

    def test_missing_spec_key_rejected(self):
        spec = _spec()
        del spec["minimum_lots"]
        with self.assertRaises(ValueError):
            assess_evaluation_campaign(spec)

    def test_non_mapping_spec_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_campaign(["part_type"])

    def test_zero_minimum_samples_rejected(self):
        with self.assertRaises(ValueError):
            assess_evaluation_campaign(_spec(minimum_samples=0))

    def test_every_shortfall_is_named_not_only_the_first(self):
        blocks = _full_blocks(endurance={"failures": 2}, radiation={"samples": 1,
                                                                   "minimum_samples": 10})
        spec = _spec(blocks=blocks, part_type=dict(PART, date_codes=["2431"]))
        result = assess_evaluation_campaign(spec)
        self.assertGreaterEqual(len(result["findings"]), 3)

    def test_tolerance_is_small_enough_to_be_representation_only(self):
        self.assertLess(DEVICE_HOUR_TOLERANCE, 1e-6)


if __name__ == "__main__":
    unittest.main()
