"""Contract test for the mechanism margin-of-safety leaf (stdlib unittest)."""

import unittest

from e3301_margin_of_safety_factors_of_safety_logic import (
    CATEGORIES_WITHOUT_YIELD_POINT,
    MODE_ULTIMATE,
    MODE_YIELD,
    VERDICT_NEGATIVE,
    VERDICT_POSITIVE,
    VERDICT_ZERO,
    assess_load_case,
    assess_margins,
    category_has_yield_point,
    factors_of_safety,
    margin_of_safety,
    margin_verdict,
    validate_load_case,
)


def case(cid="LC-1", **kw):
    record = {
        "id": cid,
        "design_limit_load": 1000.0,
        "yield_allowable": 2000.0,
        "ultimate_allowable": 2600.0,
    }
    record.update(kw)
    return record


def item(**kw):
    record = {
        "id": "DRIVE-SHAFT",
        "verification_approach": "qualification-test",
        "material_category": "metallic-ductile",
        "load_cases": [case("LC-1")],
    }
    record.update(kw)
    return record


class TestFactorsOfSafety(unittest.TestCase):
    def test_test_route_is_lighter_than_analysis_route(self):
        tested = factors_of_safety("qualification-test", "metallic-ductile")
        analysed = factors_of_safety("analysis-only", "metallic-ductile")
        self.assertLess(tested[MODE_ULTIMATE], analysed[MODE_ULTIMATE])
        self.assertLess(tested[MODE_YIELD], analysed[MODE_YIELD])

    def test_ductile_metal_carries_no_special_factor(self):
        factors = factors_of_safety("protoflight-test", "metallic-ductile")
        self.assertAlmostEqual(factors["special"], 1.0, places=9)

    def test_bonded_joint_carries_a_special_factor(self):
        factors = factors_of_safety("protoflight-test", "bonded-joint")
        self.assertGreater(factors["special"], 1.0)

    def test_unknown_approach_raises(self):
        with self.assertRaises(ValueError):
            factors_of_safety("wishful-thinking", "metallic-ductile")

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            factors_of_safety("analysis-only", "unobtainium")


class TestYieldApplicability(unittest.TestCase):
    def test_ductile_metal_has_a_yield_point(self):
        self.assertTrue(category_has_yield_point("metallic-ductile"))

    def test_brittle_categories_have_no_yield_point(self):
        for category in CATEGORIES_WITHOUT_YIELD_POINT:
            self.assertFalse(category_has_yield_point(category))

    def test_unknown_category_raises(self):
        with self.assertRaises(ValueError):
            category_has_yield_point("cheese")


class TestMarginOfSafety(unittest.TestCase):
    def test_double_the_factored_load_gives_unit_margin(self):
        value = margin_of_safety(2000.0, 1000.0, 1.0, 1.0)
        self.assertAlmostEqual(value, 1.0, places=9)

    def test_allowable_equal_to_the_factored_load_gives_zero(self):
        value = margin_of_safety(1250.0, 1000.0, 1.25, 1.0)
        self.assertAlmostEqual(value, 0.0, places=9)

    def test_special_factor_eats_the_margin(self):
        plain = margin_of_safety(2000.0, 1000.0, 1.25, 1.0)
        special = margin_of_safety(2000.0, 1000.0, 1.25, 1.25)
        self.assertGreater(plain, special)

    def test_zero_load_raises(self):
        with self.assertRaises(ValueError):
            margin_of_safety(2000.0, 0.0, 1.25)

    def test_zero_allowable_raises(self):
        with self.assertRaises(ValueError):
            margin_of_safety(0.0, 1000.0, 1.25)

    def test_factor_below_unity_raises(self):
        with self.assertRaises(ValueError):
            margin_of_safety(2000.0, 1000.0, 0.9)

    def test_boolean_allowable_raises(self):
        with self.assertRaises(ValueError):
            margin_of_safety(True, 1000.0, 1.25)


class TestMarginVerdict(unittest.TestCase):
    def test_clear_reserve_is_positive(self):
        self.assertEqual(margin_verdict(0.31), VERDICT_POSITIVE)

    def test_exact_zero_is_grouped_as_zero(self):
        self.assertEqual(margin_verdict(0.0), VERDICT_ZERO)

    def test_last_place_noise_is_grouped_as_zero(self):
        self.assertEqual(margin_verdict(-1.0e-15), VERDICT_ZERO)

    def test_real_shortfall_is_negative(self):
        self.assertEqual(margin_verdict(-0.04), VERDICT_NEGATIVE)


class TestValidateLoadCase(unittest.TestCase):
    def test_absent_allowables_normalize_to_none(self):
        norm = validate_load_case({"id": "LC-1", "design_limit_load": 10.0})
        self.assertIsNone(norm["yield_allowable"])
        self.assertIsNone(norm["ultimate_allowable"])

    def test_non_mapping_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case("LC-1")

    def test_zero_design_limit_load_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", design_limit_load=0.0))

    def test_negative_ultimate_allowable_raises(self):
        with self.assertRaises(ValueError):
            validate_load_case(case("LC-1", ultimate_allowable=-5.0))


class TestAssessLoadCase(unittest.TestCase):
    def test_both_margins_are_computed_for_a_ductile_metal(self):
        result = assess_load_case(case(), "qualification-test", "metallic-ductile")
        self.assertAlmostEqual(result["yield_margin"], 2000.0 / 1100.0 - 1.0, places=9)
        self.assertAlmostEqual(
            result["ultimate_margin"], 2600.0 / 1250.0 - 1.0, places=9
        )
        self.assertTrue(result["compliant"])

    def test_ultimate_can_govern_over_yield(self):
        result = assess_load_case(
            case(yield_allowable=2000.0, ultimate_allowable=2100.0),
            "qualification-test",
            "metallic-ductile",
        )
        self.assertEqual(result["governing_mode"], MODE_ULTIMATE)

    def test_yield_can_govern_over_ultimate(self):
        result = assess_load_case(
            case(yield_allowable=1150.0, ultimate_allowable=3000.0),
            "qualification-test",
            "metallic-ductile",
        )
        self.assertEqual(result["governing_mode"], MODE_YIELD)

    def test_composite_reports_yield_as_not_applicable(self):
        result = assess_load_case(
            case(yield_allowable=None), "qualification-test", "fibre-composite"
        )
        self.assertIsNone(result["yield_margin"])
        self.assertFalse(result["yield_applicable"])
        self.assertEqual(result["governing_mode"], MODE_ULTIMATE)
        self.assertTrue(result["compliant"])

    def test_yield_allowable_on_a_composite_is_a_finding(self):
        result = assess_load_case(case(), "qualification-test", "fibre-composite")
        self.assertIn(
            "yield-allowable-declared-for-category-without-yield", result["findings"]
        )

    def test_missing_ultimate_allowable_is_a_finding(self):
        result = assess_load_case(
            case(ultimate_allowable=None), "qualification-test", "metallic-ductile"
        )
        self.assertIn("ultimate-allowable-missing", result["findings"])

    def test_negative_margin_is_a_finding(self):
        result = assess_load_case(
            case(ultimate_allowable=1000.0), "analysis-only", "metallic-ductile"
        )
        self.assertIn("negative-ultimate-margin", result["findings"])
        self.assertFalse(result["compliant"])


class TestAssessMargins(unittest.TestCase):
    def test_single_compliant_case_passes(self):
        report = assess_margins(item())
        self.assertTrue(report["compliant"])
        self.assertEqual(report["driving_case_id"], "LC-1")

    def test_worst_case_drives_the_item(self):
        report = assess_margins(
            item(
                load_cases=[
                    case("LC-1"),
                    case("LC-2", design_limit_load=1800.0),
                ]
            )
        )
        self.assertEqual(report["driving_case_id"], "LC-2")

    def test_exactly_zero_margin_is_listed_not_failed(self):
        report = assess_margins(
            item(
                load_cases=[
                    case("LC-1", yield_allowable=1100.0, ultimate_allowable=1250.0)
                ]
            )
        )
        self.assertEqual(report["zero_margin_case_ids"], ["LC-1"])
        self.assertTrue(report["compliant"])
        self.assertAlmostEqual(report["governing_margin"], 0.0, places=9)

    def test_one_failing_case_fails_the_item(self):
        report = assess_margins(
            item(
                load_cases=[case("LC-1"), case("LC-2", ultimate_allowable=100.0)]
            )
        )
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_case_ids"], ["LC-2"])

    def test_duplicate_case_id_raises(self):
        with self.assertRaises(ValueError):
            assess_margins(item(load_cases=[case("LC-1"), case("LC-1")]))

    def test_empty_case_list_raises(self):
        with self.assertRaises(ValueError):
            assess_margins(item(load_cases=[]))

    def test_unknown_approach_raises(self):
        with self.assertRaises(ValueError):
            assess_margins(item(verification_approach="hoping"))


if __name__ == "__main__":
    unittest.main()
