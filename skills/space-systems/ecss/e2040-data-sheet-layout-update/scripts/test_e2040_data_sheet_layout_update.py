"""Contract test for the data-sheet-layout-update leaf (stdlib unittest)."""

import unittest

from e2040_data_sheet_layout_update_logic import (
    DIRECTION_LOWER_BOUND,
    DIRECTION_UPPER_BOUND,
    FINDING_LIMIT_VIOLATED,
    FINDING_NOT_REFRESHED,
    FINDING_OPTIMISTIC_PUBLISHED_VALUE,
    FINDING_SINGLE_CORNER,
    assess_data_sheet_layout_update,
    assess_parameter,
    is_more_favourable,
    margin_fraction,
    meets_limit,
    validate_parameter,
    worst_corner,
)


def delay(pid="tpd-clk-q", published=8.0, limit=10.0, corners=None, **kw):
    record = {
        "id": pid,
        "direction": DIRECTION_UPPER_BOUND,
        "unit": "ns",
        "specification_limit": limit,
        "published_value": published,
        "extracted_by_corner": corners
        if corners is not None
        else {"slow-cold": 8.0, "typical": 6.0, "fast-hot": 5.0},
    }
    record.update(kw)
    return record


def fmax(pid="f-max", published=120.0, limit=100.0, corners=None, **kw):
    record = {
        "id": pid,
        "direction": DIRECTION_LOWER_BOUND,
        "unit": "MHz",
        "specification_limit": limit,
        "published_value": published,
        "extracted_by_corner": corners
        if corners is not None
        else {"slow-cold": 120.0, "typical": 150.0, "fast-hot": 160.0},
    }
    record.update(kw)
    return record


class TestValidateParameter(unittest.TestCase):
    def test_normalizes_a_good_record(self):
        norm = validate_parameter(delay())
        self.assertEqual(norm["id"], "tpd-clk-q")
        self.assertEqual(norm["unit"], "ns")
        self.assertEqual(len(norm["extracted_by_corner"]), 3)

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(["tpd"])

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(direction="sideways"))

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(limit=0.0))

    def test_empty_corner_map_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(corners={}))

    def test_non_numeric_corner_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(corners={"typical": "slow"}))

    def test_non_finite_published_value_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(published=float("inf")))

    def test_blank_unit_raises(self):
        with self.assertRaises(ValueError):
            validate_parameter(delay(unit="  "))


class TestWorstCorner(unittest.TestCase):
    def test_upper_bounded_parameter_takes_the_largest(self):
        name, value = worst_corner(delay())
        self.assertEqual(name, "slow-cold")
        self.assertAlmostEqual(value, 8.0, places=9)

    def test_lower_bounded_parameter_takes_the_smallest(self):
        name, value = worst_corner(fmax())
        self.assertEqual(name, "slow-cold")
        self.assertAlmostEqual(value, 120.0, places=9)

    def test_tie_breaks_on_the_corner_name(self):
        name, _ = worst_corner(
            delay(corners={"zz-corner": 9.0, "aa-corner": 9.0})
        )
        self.assertEqual(name, "aa-corner")

    def test_direction_changes_the_selected_corner(self):
        corners = {"slow-cold": 4.0, "fast-hot": 9.0}
        up, _ = worst_corner(delay(corners=corners))
        down, _ = worst_corner(fmax(corners=corners, published=4.0, limit=1.0))
        self.assertEqual(up, "fast-hot")
        self.assertEqual(down, "slow-cold")


class TestMarginFraction(unittest.TestCase):
    def test_upper_bound_margin(self):
        self.assertAlmostEqual(
            margin_fraction(8.0, 10.0, DIRECTION_UPPER_BOUND), 0.2, places=9
        )

    def test_lower_bound_margin(self):
        self.assertAlmostEqual(
            margin_fraction(120.0, 100.0, DIRECTION_LOWER_BOUND), 0.2, places=9
        )

    def test_value_on_the_limit_is_zero_margin(self):
        self.assertAlmostEqual(
            margin_fraction(10.0, 10.0, DIRECTION_UPPER_BOUND), 0.0, places=9
        )

    def test_violation_is_negative(self):
        self.assertAlmostEqual(
            margin_fraction(12.0, 10.0, DIRECTION_UPPER_BOUND), -0.2, places=9
        )

    def test_unknown_direction_raises(self):
        with self.assertRaises(ValueError):
            margin_fraction(1.0, 2.0, "sideways")

    def test_zero_limit_raises(self):
        with self.assertRaises(ValueError):
            margin_fraction(1.0, 0.0, DIRECTION_UPPER_BOUND)


class TestComparators(unittest.TestCase):
    def test_lower_delay_is_more_favourable(self):
        self.assertTrue(is_more_favourable(7.0, 8.0, DIRECTION_UPPER_BOUND))

    def test_higher_frequency_is_more_favourable(self):
        self.assertTrue(is_more_favourable(130.0, 120.0, DIRECTION_LOWER_BOUND))

    def test_equal_values_are_not_more_favourable(self):
        self.assertFalse(is_more_favourable(8.0, 8.0, DIRECTION_UPPER_BOUND))

    def test_value_on_the_limit_meets_it(self):
        self.assertTrue(meets_limit(10.0, 10.0, DIRECTION_UPPER_BOUND))
        self.assertTrue(meets_limit(100.0, 100.0, DIRECTION_LOWER_BOUND))

    def test_value_past_the_limit_fails_it(self):
        self.assertFalse(meets_limit(10.5, 10.0, DIRECTION_UPPER_BOUND))
        self.assertFalse(meets_limit(99.5, 100.0, DIRECTION_LOWER_BOUND))


class TestAssessParameter(unittest.TestCase):
    def test_published_worst_corner_is_clean(self):
        result = assess_parameter(delay())
        self.assertTrue(result["compliant"])
        self.assertEqual(result["worst_corner"], "slow-cold")
        self.assertAlmostEqual(result["margin_fraction"], 0.2, places=9)

    def test_more_conservative_publication_is_allowed(self):
        result = assess_parameter(delay(published=9.0))
        self.assertTrue(result["compliant"])

    def test_optimistic_publication_is_a_finding(self):
        result = assess_parameter(delay(published=6.0))
        self.assertIn(FINDING_OPTIMISTIC_PUBLISHED_VALUE, result["findings"])

    def test_optimistic_publication_for_a_lower_bound(self):
        result = assess_parameter(fmax(published=150.0))
        self.assertIn(FINDING_OPTIMISTIC_PUBLISHED_VALUE, result["findings"])

    def test_unrefreshed_estimate_is_a_finding(self):
        result = assess_parameter(delay(published=7.0, pre_layout_estimate=7.0))
        self.assertIn(FINDING_NOT_REFRESHED, result["findings"])

    def test_estimate_matching_the_corner_is_not_a_stale_figure(self):
        result = assess_parameter(delay(published=8.0, pre_layout_estimate=8.0))
        self.assertNotIn(FINDING_NOT_REFRESHED, result["findings"])

    def test_single_corner_is_a_coverage_finding(self):
        result = assess_parameter(delay(corners={"typical": 8.0}))
        self.assertIn(FINDING_SINGLE_CORNER, result["findings"])

    def test_worst_corner_outside_the_limit_is_a_finding(self):
        result = assess_parameter(
            delay(published=12.0, corners={"slow-cold": 12.0, "typical": 6.0})
        )
        self.assertIn(FINDING_LIMIT_VIOLATED, result["findings"])
        self.assertAlmostEqual(result["margin_fraction"], -0.2, places=9)

    def test_corner_exactly_on_the_limit_still_meets_it(self):
        result = assess_parameter(
            delay(published=10.0, corners={"slow-cold": 10.0, "typical": 6.0})
        )
        self.assertNotIn(FINDING_LIMIT_VIOLATED, result["findings"])
        self.assertAlmostEqual(result["margin_fraction"], 0.0, places=9)


class TestAssessRevision(unittest.TestCase):
    def test_clean_revision_is_complete(self):
        report = assess_data_sheet_layout_update([delay(), fmax()])
        self.assertTrue(report["revision_complete"])
        self.assertEqual(report["non_compliant_ids"], [])

    def test_tightest_parameter_is_reported(self):
        tight = delay(pid="tsu", published=9.9, corners={"slow-cold": 9.9, "typical": 5.0})
        report = assess_data_sheet_layout_update([delay(), tight])
        self.assertEqual(report["tightest_parameter_id"], "tsu")
        self.assertAlmostEqual(report["tightest_margin_fraction"], 0.01, places=9)

    def test_one_bad_parameter_blocks_the_revision(self):
        report = assess_data_sheet_layout_update([delay(), fmax(published=150.0)])
        self.assertFalse(report["revision_complete"])
        self.assertEqual(report["non_compliant_ids"], ["f-max"])

    def test_duplicate_parameter_id_raises(self):
        with self.assertRaises(ValueError):
            assess_data_sheet_layout_update([delay(), delay()])

    def test_empty_parameter_list_raises(self):
        with self.assertRaises(ValueError):
            assess_data_sheet_layout_update([])

    def test_non_list_input_raises(self):
        with self.assertRaises(ValueError):
            assess_data_sheet_layout_update(delay())


if __name__ == "__main__":
    unittest.main()
