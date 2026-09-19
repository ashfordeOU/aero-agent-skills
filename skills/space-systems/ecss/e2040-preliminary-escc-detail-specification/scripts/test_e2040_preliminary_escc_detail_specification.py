"""Contract test for the preliminary-escc-detail-specification leaf."""

import unittest

from e2040_preliminary_escc_detail_specification_logic import (
    BLOCK_ABSENT,
    BLOCK_DRAFTED,
    BLOCK_PRESENT,
    DIRECTION_UPPER_BOUND,
    FINDING_BLOCK_ABSENT,
    FINDING_BLOCK_DRAFTED,
    FINDING_NO_TEMPERATURE,
    FINDING_NO_TEST_CONDITION,
    FINDING_OPERATING_RANGE_COINCIDENT,
    FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE,
    NOT_OWED,
    OWED,
    REQUIRED_BLOCKS,
    ROUTE_APPLICATION_SPECIFIC,
    ROUTE_FORMAL_EVALUATION,
    ROUTE_SOURCE_DELIVERY,
    assess_preliminary_escc_detail_specification,
    block_findings,
    characteristic_findings,
    rating_findings,
    readiness_fraction,
    specification_owed,
    validate_block_map,
    validate_characteristic,
    validate_device,
    validate_rating,
)


def device(kind="asic", route=ROUTE_FORMAL_EVALUATION, did="DEV-1"):
    return {"id": did, "kind": kind, "route": route}


def all_blocks(state=BLOCK_PRESENT, **overrides):
    blocks = {name: state for name in REQUIRED_BLOCKS}
    blocks.update(overrides)
    return blocks


def characteristic(cid="icc-quiescent", **kw):
    record = {
        "id": cid,
        "direction": DIRECTION_UPPER_BOUND,
        "limit": 45.0,
        "unit": "mA",
        "test_condition": "outputs-unloaded-nominal-supply",
        "temperature_c": 125.0,
    }
    record.update(kw)
    return record


def rating(rid="core-supply", **kw):
    record = {
        "id": rid,
        "absolute_min": -0.3,
        "absolute_max": 1.32,
        "operating_min": 1.14,
        "operating_max": 1.26,
    }
    record.update(kw)
    return record


class TestValidateDevice(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        self.assertEqual(validate_device(device())["route"], ROUTE_FORMAL_EVALUATION)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_device("DEV-1")

    def test_unknown_kind_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(kind="daughterboard"))

    def test_unknown_route_raises(self):
        with self.assertRaises(ValueError):
            validate_device(device(route="word-of-mouth"))


class TestSpecificationOwed(unittest.TestCase):
    def test_evaluation_bound_packaged_device_owes_one(self):
        status, reason = specification_owed(device())
        self.assertEqual(status, OWED)
        self.assertIn("formal-part-evaluation", reason)

    def test_application_specific_device_does_not(self):
        status, reason = specification_owed(device(route=ROUTE_APPLICATION_SPECIFIC))
        self.assertEqual(status, NOT_OWED)
        self.assertIn("not-routed", reason)

    def test_source_delivered_core_does_not(self):
        status, reason = specification_owed(
            device(kind="ip-core", route=ROUTE_SOURCE_DELIVERY)
        )
        self.assertEqual(status, NOT_OWED)

    def test_core_on_the_evaluation_route_still_has_no_package(self):
        status, reason = specification_owed(
            device(kind="ip-core", route=ROUTE_FORMAL_EVALUATION)
        )
        self.assertEqual(status, NOT_OWED)
        self.assertIn("no-package", reason)


class TestBlockMap(unittest.TestCase):
    def test_unknown_block_raises(self):
        with self.assertRaises(ValueError):
            validate_block_map({"cover-art": BLOCK_PRESENT})

    def test_unknown_state_raises(self):
        with self.assertRaises(ValueError):
            validate_block_map({REQUIRED_BLOCKS[0]: "nearly"})

    def test_empty_map_raises(self):
        with self.assertRaises(ValueError):
            validate_block_map({})

    def test_complete_map_has_no_findings(self):
        self.assertEqual(block_findings(all_blocks()), [])

    def test_drafted_block_is_a_finding(self):
        findings = block_findings(all_blocks(**{"package-outline": BLOCK_DRAFTED}))
        self.assertIn(("package-outline", FINDING_BLOCK_DRAFTED), findings)

    def test_absent_block_is_a_finding(self):
        findings = block_findings(all_blocks(**{"marking-and-traceability": BLOCK_ABSENT}))
        self.assertIn(("marking-and-traceability", FINDING_BLOCK_ABSENT), findings)

    def test_omitted_block_counts_as_absent(self):
        blocks = all_blocks()
        del blocks["terminal-identification"]
        findings = block_findings(blocks)
        self.assertIn(("terminal-identification", FINDING_BLOCK_ABSENT), findings)


class TestReadinessFraction(unittest.TestCase):
    def test_complete_draft_is_one(self):
        self.assertAlmostEqual(readiness_fraction(all_blocks()), 1.0, places=9)

    def test_one_block_missing(self):
        value = readiness_fraction(all_blocks(**{"package-outline": BLOCK_ABSENT}))
        self.assertAlmostEqual(
            value, (len(REQUIRED_BLOCKS) - 1) / len(REQUIRED_BLOCKS), places=9
        )

    def test_all_absent_is_zero(self):
        self.assertAlmostEqual(readiness_fraction(all_blocks(BLOCK_ABSENT)), 0.0, places=9)

    def test_drafted_does_not_count_as_present(self):
        self.assertAlmostEqual(readiness_fraction(all_blocks(BLOCK_DRAFTED)), 0.0, places=9)


class TestCharacteristics(unittest.TestCase):
    def test_complete_entry_has_no_findings(self):
        self.assertEqual(characteristic_findings(characteristic()), [])

    def test_missing_test_condition_is_a_finding(self):
        self.assertIn(
            FINDING_NO_TEST_CONDITION,
            characteristic_findings(characteristic(test_condition=None)),
        )

    def test_missing_temperature_is_a_finding(self):
        self.assertIn(
            FINDING_NO_TEMPERATURE,
            characteristic_findings(characteristic(temperature_c=None)),
        )

    def test_non_finite_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(limit=float("nan")))

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            validate_characteristic(characteristic(direction="around"))


class TestRatings(unittest.TestCase):
    def test_operating_range_inside_absolute_is_clean(self):
        self.assertEqual(rating_findings(rating()), [])

    def test_operating_max_above_absolute_max_is_a_finding(self):
        self.assertIn(
            FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE,
            rating_findings(rating(operating_max=1.4)),
        )

    def test_operating_min_below_absolute_min_is_a_finding(self):
        self.assertIn(
            FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE,
            rating_findings(rating(operating_min=-0.5)),
        )

    def test_coincident_bound_is_reported_as_coincident(self):
        findings = rating_findings(rating(operating_max=1.32))
        self.assertIn(FINDING_OPERATING_RANGE_COINCIDENT, findings)
        self.assertNotIn(FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE, findings)

    def test_inverted_absolute_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(absolute_min=2.0, absolute_max=1.0))

    def test_inverted_operating_pair_raises(self):
        with self.assertRaises(ValueError):
            validate_rating(rating(operating_min=1.3, operating_max=1.1))


class TestAssessment(unittest.TestCase):
    def test_complete_draft_is_review_ready(self):
        report = assess_preliminary_escc_detail_specification(
            device(), all_blocks(), [characteristic()], [rating()]
        )
        self.assertEqual(report["status"], OWED)
        self.assertTrue(report["review_ready"])
        self.assertAlmostEqual(report["readiness"], 1.0, places=9)
        self.assertEqual(report["open_blocks"], [])

    def test_not_owed_device_needs_no_draft(self):
        report = assess_preliminary_escc_detail_specification(
            device(route=ROUTE_APPLICATION_SPECIFIC)
        )
        self.assertEqual(report["status"], NOT_OWED)
        self.assertIsNone(report["readiness"])
        self.assertTrue(report["review_ready"])

    def test_owed_device_without_a_block_map_raises(self):
        with self.assertRaises(ValueError):
            assess_preliminary_escc_detail_specification(device())

    def test_open_blocks_are_named(self):
        report = assess_preliminary_escc_detail_specification(
            device(), all_blocks(**{"package-outline": BLOCK_DRAFTED})
        )
        self.assertEqual(report["open_blocks"], ["package-outline"])
        self.assertFalse(report["review_ready"])

    def test_characteristic_finding_blocks_the_review(self):
        report = assess_preliminary_escc_detail_specification(
            device(), all_blocks(), [characteristic(test_condition=None)]
        )
        self.assertIn(("icc-quiescent", FINDING_NO_TEST_CONDITION), report["findings"])
        self.assertFalse(report["review_ready"])

    def test_rating_finding_blocks_the_review(self):
        report = assess_preliminary_escc_detail_specification(
            device(), all_blocks(), [], [rating(operating_max=1.4)]
        )
        self.assertIn(
            ("core-supply", FINDING_OPERATING_RANGE_OUTSIDE_ABSOLUTE),
            report["findings"],
        )

    def test_duplicate_characteristic_raises(self):
        with self.assertRaises(ValueError):
            assess_preliminary_escc_detail_specification(
                device(), all_blocks(), [characteristic(), characteristic()]
            )

    def test_duplicate_rating_raises(self):
        with self.assertRaises(ValueError):
            assess_preliminary_escc_detail_specification(
                device(), all_blocks(), [], [rating(), rating()]
            )

    def test_non_list_characteristics_raises(self):
        with self.assertRaises(ValueError):
            assess_preliminary_escc_detail_specification(
                device(), all_blocks(), characteristic()
            )


if __name__ == "__main__":
    unittest.main()
