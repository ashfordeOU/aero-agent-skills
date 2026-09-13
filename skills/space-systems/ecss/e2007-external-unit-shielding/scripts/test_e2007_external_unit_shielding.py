"""Contract test for the external-unit shielding leaf (stdlib unittest)."""

import unittest

from e2007_external_unit_shielding_logic import (
    CATEGORY_EXTERNAL_CABLE_RUN,
    CATEGORY_EXTERNAL_UNIT,
    CATEGORY_OUT_OF_SCOPE,
    MARGIN_TOLERANCE_DB,
    assess_external_shielding,
    categorize_item,
    check_shield_individuality,
    coverage_derate_db,
    effective_attenuation_db,
    evaluate_item,
    interpolate_attenuation_db,
    required_attenuation_db,
    termination_derate_db,
    validate_environment,
)

FLAT_CURVE = [(1.0e6, 40.0), (1.0e9, 40.0)]
ENV = {"frequency_hz": 1.0e8, "incident_field_v_per_m": 20.0}


def shield(sid="SH-1", points=None, coverage=95.0, termination="circumferential"):
    return {
        "id": sid,
        "attenuation_points": list(points if points is not None else FLAT_CURVE),
        "braid_coverage_percent": coverage,
        "termination": termination,
    }


def unit(uid="U-1", threshold=2.0, sh=None, location="outside-main-structure"):
    item = {
        "id": uid,
        "kind": "unit",
        "location": location,
        "susceptibility_threshold_v_per_m": threshold,
    }
    if sh is not None:
        item["shield"] = sh
    return item


class TestCategorizeItem(unittest.TestCase):
    def test_external_unit_is_in_scope(self):
        self.assertEqual(categorize_item(unit()), CATEGORY_EXTERNAL_UNIT)

    def test_external_cable_run_is_in_scope(self):
        item = unit("C-1")
        item["kind"] = "cable-run"
        self.assertEqual(categorize_item(item), CATEGORY_EXTERNAL_CABLE_RUN)

    def test_internal_item_is_out_of_scope(self):
        item = unit("U-2", location="inside-main-structure")
        self.assertEqual(categorize_item(item), CATEGORY_OUT_OF_SCOPE)

    def test_internal_cable_run_is_out_of_scope(self):
        item = unit("C-2", location="inside-main-structure")
        item["kind"] = "cable-run"
        self.assertEqual(categorize_item(item), CATEGORY_OUT_OF_SCOPE)

    def test_unknown_location_raises(self):
        item = unit("U-3", location="on-the-launcher")
        with self.assertRaises(ValueError):
            categorize_item(item)

    def test_unknown_kind_raises(self):
        item = unit("U-4")
        item["kind"] = "antenna-boom"
        with self.assertRaises(ValueError):
            categorize_item(item)

    def test_non_mapping_item_raises(self):
        with self.assertRaises(ValueError):
            categorize_item(["U-5"])

    def test_missing_id_raises(self):
        item = unit("U-6")
        item["id"] = ""
        with self.assertRaises(ValueError):
            categorize_item(item)


class TestInterpolateAttenuation(unittest.TestCase):
    def test_single_point_curve_is_held(self):
        self.assertAlmostEqual(interpolate_attenuation_db([(1.0e6, 33.0)], 5.0e8), 33.0)

    def test_below_first_point_clamps_low(self):
        points = [(1.0e6, 20.0), (1.0e9, 50.0)]
        self.assertAlmostEqual(interpolate_attenuation_db(points, 1.0e3), 20.0)

    def test_above_last_point_clamps_high(self):
        points = [(1.0e6, 20.0), (1.0e9, 50.0)]
        self.assertAlmostEqual(interpolate_attenuation_db(points, 1.0e12), 50.0)

    def test_exact_point_returns_its_value(self):
        points = [(1.0e3, 20.0), (1.0e5, 40.0)]
        self.assertAlmostEqual(interpolate_attenuation_db(points, 1.0e3), 20.0)

    def test_log_midpoint_interpolates(self):
        points = [(1.0e3, 20.0), (1.0e5, 40.0)]
        self.assertAlmostEqual(interpolate_attenuation_db(points, 1.0e4), 30.0)

    def test_unsorted_points_are_ordered_first(self):
        points = [(1.0e5, 40.0), (1.0e3, 20.0)]
        self.assertAlmostEqual(interpolate_attenuation_db(points, 1.0e4), 30.0)

    def test_empty_curve_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db([], 1.0e6)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db(FLAT_CURVE, 0.0)

    def test_negative_frequency_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db(FLAT_CURVE, -1.0e6)

    def test_duplicate_point_frequency_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db([(1.0e6, 20.0), (1.0e6, 30.0)], 1.0e6)

    def test_negative_attenuation_point_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db([(1.0e6, -5.0)], 1.0e6)

    def test_non_positive_point_frequency_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db([(0.0, 20.0)], 1.0e6)

    def test_malformed_point_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db([(1.0e6,)], 1.0e6)

    def test_non_numeric_frequency_raises(self):
        with self.assertRaises(ValueError):
            interpolate_attenuation_db(FLAT_CURVE, "1e6")


class TestCoverageDerate(unittest.TestCase):
    def test_solid_shield_has_no_derate(self):
        self.assertAlmostEqual(coverage_derate_db(100.0), 0.0)

    def test_reference_coverage_has_no_derate(self):
        self.assertAlmostEqual(coverage_derate_db(95.0), 0.0)

    def test_below_reference_derates_linearly(self):
        self.assertAlmostEqual(coverage_derate_db(85.0), 5.0)

    def test_low_coverage_derates_further(self):
        self.assertAlmostEqual(coverage_derate_db(70.0), 12.5)

    def test_zero_coverage_raises(self):
        with self.assertRaises(ValueError):
            coverage_derate_db(0.0)

    def test_coverage_above_hundred_raises(self):
        with self.assertRaises(ValueError):
            coverage_derate_db(101.0)

    def test_non_numeric_coverage_raises(self):
        with self.assertRaises(ValueError):
            coverage_derate_db("95")


class TestTerminationDerate(unittest.TestCase):
    def test_circumferential_keeps_performance(self):
        self.assertAlmostEqual(termination_derate_db("circumferential"), 0.0)

    def test_partial_backshell_costs_ten_db(self):
        self.assertAlmostEqual(termination_derate_db("partial-backshell"), 10.0)

    def test_pigtail_costs_twenty_db(self):
        self.assertAlmostEqual(termination_derate_db("pigtail"), 20.0)

    def test_unterminated_credits_nothing(self):
        self.assertIsNone(termination_derate_db("unterminated"))

    def test_unknown_termination_raises(self):
        with self.assertRaises(ValueError):
            termination_derate_db("soldered-blob")


class TestEffectiveAttenuation(unittest.TestCase):
    def test_good_shield_keeps_measured_value(self):
        self.assertAlmostEqual(effective_attenuation_db(shield(), 1.0e8), 40.0)

    def test_pigtail_and_coverage_derates_add(self):
        sh = shield(coverage=85.0, termination="pigtail")
        self.assertAlmostEqual(effective_attenuation_db(sh, 1.0e8), 15.0)

    def test_unterminated_shield_credits_zero(self):
        sh = shield(termination="unterminated")
        self.assertAlmostEqual(effective_attenuation_db(sh, 1.0e8), 0.0)

    def test_result_never_goes_negative(self):
        sh = shield(points=[(1.0e6, 5.0)], coverage=50.0, termination="pigtail")
        self.assertAlmostEqual(effective_attenuation_db(sh, 1.0e8), 0.0)

    def test_shield_without_id_raises(self):
        sh = shield()
        del sh["id"]
        with self.assertRaises(ValueError):
            effective_attenuation_db(sh, 1.0e8)

    def test_non_mapping_shield_raises(self):
        with self.assertRaises(ValueError):
            effective_attenuation_db("SH-1", 1.0e8)


class TestRequiredAttenuation(unittest.TestCase):
    def test_factor_of_ten_needs_twenty_db(self):
        self.assertAlmostEqual(required_attenuation_db(20.0, 2.0), 20.0)

    def test_factor_of_hundred_needs_forty_db(self):
        self.assertAlmostEqual(required_attenuation_db(200.0, 2.0), 40.0)

    def test_benign_environment_needs_nothing(self):
        self.assertAlmostEqual(required_attenuation_db(1.0, 10.0), 0.0)

    def test_zero_threshold_raises(self):
        with self.assertRaises(ValueError):
            required_attenuation_db(20.0, 0.0)

    def test_negative_incident_field_raises(self):
        with self.assertRaises(ValueError):
            required_attenuation_db(-20.0, 2.0)

    def test_non_numeric_threshold_raises(self):
        with self.assertRaises(ValueError):
            required_attenuation_db(20.0, "2")


class TestValidateEnvironment(unittest.TestCase):
    def test_valid_environment_is_normalized(self):
        env = validate_environment(ENV)
        self.assertAlmostEqual(env["frequency_hz"], 1.0e8)
        self.assertAlmostEqual(env["incident_field_v_per_m"], 20.0)

    def test_zero_frequency_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"frequency_hz": 0.0, "incident_field_v_per_m": 20.0})

    def test_zero_field_raises(self):
        with self.assertRaises(ValueError):
            validate_environment({"frequency_hz": 1.0e8, "incident_field_v_per_m": 0.0})

    def test_non_mapping_environment_raises(self):
        with self.assertRaises(ValueError):
            validate_environment(None)


class TestEvaluateItem(unittest.TestCase):
    def test_shielded_external_unit_is_compliant(self):
        res = evaluate_item(unit(sh=shield()), ENV)
        self.assertTrue(res["compliant"])
        self.assertEqual(res["findings"], [])
        self.assertAlmostEqual(res["margin_db"], 20.0)

    def test_shortfall_is_flagged(self):
        sh = shield(coverage=60.0, termination="pigtail")
        res = evaluate_item(unit(sh=sh), ENV)
        self.assertFalse(res["compliant"])
        self.assertIn("attenuation-shortfall", res["findings"])

    def test_missing_shield_is_flagged(self):
        res = evaluate_item(unit(), ENV)
        self.assertFalse(res["compliant"])
        self.assertIn("no-individual-shield-declared", res["findings"])

    def test_internal_item_is_skipped(self):
        res = evaluate_item(unit(location="inside-main-structure"), ENV)
        self.assertFalse(res["in_scope"])
        self.assertEqual(res["findings"], [])
        self.assertIsNone(res["required_attenuation_db"])

    def test_exact_boundary_margin_is_compliant(self):
        sh = shield(points=[(1.0e6, 40.1), (1.0e9, 40.1)], coverage=94.8,
                    termination="pigtail")
        res = evaluate_item(unit(sh=sh), ENV)
        self.assertLess(abs(res["margin_db"]), MARGIN_TOLERANCE_DB)
        self.assertTrue(res["compliant"])

    def test_missing_threshold_raises(self):
        item = unit(sh=shield())
        del item["susceptibility_threshold_v_per_m"]
        with self.assertRaises(ValueError):
            evaluate_item(item, ENV)


class TestShieldIndividuality(unittest.TestCase):
    def test_shared_shield_is_detected(self):
        results = [
            evaluate_item(unit("U-1", sh=shield("SH-A")), ENV),
            evaluate_item(unit("U-2", sh=shield("SH-A")), ENV),
        ]
        shared = check_shield_individuality(results)
        self.assertEqual(sorted(shared["SH-A"]), ["U-1", "U-2"])
        self.assertFalse(results[0]["compliant"])
        self.assertFalse(results[1]["compliant"])

    def test_distinct_shields_are_clean(self):
        results = [
            evaluate_item(unit("U-1", sh=shield("SH-A")), ENV),
            evaluate_item(unit("U-2", sh=shield("SH-B")), ENV),
        ]
        self.assertEqual(check_shield_individuality(results), {})
        self.assertTrue(all(r["compliant"] for r in results))


class TestAssessExternalShielding(unittest.TestCase):
    def test_clean_inventory_is_compliant(self):
        inventory = [
            unit("U-1", sh=shield("SH-A")),
            unit("U-2", sh=shield("SH-B")),
        ]
        report = assess_external_shielding(inventory, ENV)
        self.assertTrue(report["compliant"])
        self.assertEqual(report["in_scope_count"], 2)
        self.assertEqual(report["non_compliant_ids"], [])

    def test_internal_items_are_counted_out_of_scope(self):
        inventory = [
            unit("U-1", sh=shield("SH-A")),
            unit("U-2", location="inside-main-structure"),
        ]
        report = assess_external_shielding(inventory, ENV)
        self.assertEqual(report["out_of_scope_count"], 1)
        self.assertTrue(report["compliant"])

    def test_unshielded_external_item_fails_the_inventory(self):
        inventory = [unit("U-1", sh=shield("SH-A")), unit("U-2")]
        report = assess_external_shielding(inventory, ENV)
        self.assertFalse(report["compliant"])
        self.assertEqual(report["non_compliant_ids"], ["U-2"])

    def test_shared_shield_fails_both_items(self):
        inventory = [unit("U-1", sh=shield("SH-A")), unit("U-2", sh=shield("SH-A"))]
        report = assess_external_shielding(inventory, ENV)
        self.assertFalse(report["compliant"])
        self.assertEqual(sorted(report["non_compliant_ids"]), ["U-1", "U-2"])
        self.assertIn("SH-A", report["shared_shields"])

    def test_duplicate_item_id_raises(self):
        inventory = [unit("U-1", sh=shield("SH-A")), unit("U-1", sh=shield("SH-B"))]
        with self.assertRaises(ValueError):
            assess_external_shielding(inventory, ENV)

    def test_empty_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_external_shielding([], ENV)

    def test_non_list_inventory_raises(self):
        with self.assertRaises(ValueError):
            assess_external_shielding({"id": "U-1"}, ENV)

    def test_bad_environment_raises(self):
        inventory = [unit("U-1", sh=shield("SH-A"))]
        with self.assertRaises(ValueError):
            assess_external_shielding(inventory, {"frequency_hz": 1.0e8})


if __name__ == "__main__":
    unittest.main()
